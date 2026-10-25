// Experimental0.1.3, exact HP 8BDF / macOS 25G241 ACPI battery bridge.
// Only canonical firmware query methods. No EC/MMIO access or charge controls.
#include <IOKit/IOService.h>
#include <IOKit/IOWorkLoop.h>
#include <IOKit/IOTimerEventSource.h>
#include <IOKit/IOCommandGate.h>
#include <IOKit/acpi/IOACPIPlatformDevice.h>
#include <IOKit/pwr_mgt/IOPMPowerSource.h>
#include <IOKit/pwr_mgt/IOPM.h>
#include <libkern/OSAtomic.h>
#include <libkern/version.h>
#include <libkern/c++/OSArray.h>
#include <libkern/c++/OSData.h>
#include <libkern/c++/OSNumber.h>
#include <libkern/c++/OSString.h>
#include <IOKit/IOKitKeys.h>
#include "BatteryModel.hpp"
#include "ACPowerPolicy.hpp"

// Typed alias for the qualified x86_64 IOKit export on the exact admitted kernel.
// -fapple-kext can lower even qualified virtual C++ calls through an SDK vtable;
// this alias must instead retain a direct relocation to the named kernel method.
class IOPMrootDomain;
extern "C" IOReturn hpbatNotifyACPolicy(IOPMrootDomain *, UInt32)
    __asm__("__ZN14IOPMrootDomain24receivePowerNotificationEj");

class HPBAT1PowerSource : public IOPMPowerSource {
    OSDeclareDefaultStructors(HPBAT1PowerSource)
    void erase(const char *key) {
        if (properties->getObject(key)) {
            properties->removeObject(key);
            removeProperty(key);
            settingsChangedSinceUpdate = true;
        }
    }
    void number(const char *key, UInt32 value) {
        const OSSymbol *symbol = OSSymbol::withCString(key);
        OSNumber *n = OSNumber::withNumber(value, 32);
        if (symbol && n) setPSProperty(symbol, n);
        if (symbol) symbol->release();
        if (n) n->release();
    }
public:
    void publish(const hpbat::Snapshot &s) {
        setBatteryInstalled(true);
        setExternalConnected(s.external);
        setIsCharging(s.charging);
        setCurrentCapacity(s.remaining);
        setMaxCapacity(s.full);
        // First trial publishes capacity/status only to powerd. Its current
        // cache is not reset when Amperage disappears, so do not publish that
        // standard field until known->unknown behavior is qualified. Preserve
        // real readings in explicitly optional diagnostic properties instead.
        setTimeRemaining(-1);
        setAtCriticalLevel(s.critical);
        if (s.warningKnown) setAtWarnLevel(s.warning); else erase("AtWarnLevel");
        if (s.designKnown) number("DesignCapacity", s.design); else erase("DesignCapacity");
        if (s.voltageKnown) setVoltage(s.voltage); else erase("Voltage");
        if (s.rateKnown) setProperty("HPBAT1CurrentMA", static_cast<UInt32>(s.amperage), 32);
        else removeProperty("HPBAT1CurrentMA");
        if (s.minutes >= 0) setProperty("HPBAT1EstimatedMinutes", static_cast<UInt32>(s.minutes), 32);
        else removeProperty("HPBAT1EstimatedMinutes");
        // Do not infer charge capability, cycle count, temperature, health,
        // manufacture data, or "fully charged" from connection/capacity alone.
        setProperty("HPBAT1RateKnown", s.rateKnown);
        setProperty("HPBAT1SampleValid", true);
        updateStatus();
    }
    void absent(bool external) {
        setBatteryInstalled(false);
        setExternalConnected(external);
        setIsCharging(false);
        setTimeRemaining(-1);
        const char *keys[] = {"CurrentCapacity", "MaxCapacity", "DesignCapacity",
            "Voltage", "Amperage", "AtWarnLevel", "AtCriticalLevel"};
        for (auto key : keys) erase(key);
        setProperty("HPBAT1RateKnown", false);
        removeProperty("HPBAT1CurrentMA");
        removeProperty("HPBAT1EstimatedMinutes");
        setProperty("HPBAT1SampleValid", true);
        updateStatus();
    }
    void stale() {
        // Retain the last successful capacities, explicitly flag stale data.
        // Do not represent a read failure as removal or 0% charge.
        erase("Amperage");
        setTimeRemaining(-1);
        setProperty("HPBAT1RateKnown", false);
        removeProperty("HPBAT1CurrentMA");
        removeProperty("HPBAT1EstimatedMinutes");
        setProperty("HPBAT1SampleValid", false);
        updateStatus();
    }
};
OSDefineMetaClassAndStructors(HPBAT1PowerSource, IOPMPowerSource)

class HPBAT1Bridge : public IOService {
    OSDeclareDefaultStructors(HPBAT1Bridge)
    IOACPIPlatformDevice *battery = nullptr;
    IOACPIPlatformDevice *adapter = nullptr;
    IOWorkLoop *loop = nullptr;
    IOTimerEventSource *timer = nullptr;
    IOCommandGate *gate = nullptr;
    IONotifier *adapterNotify = nullptr;
    HPBAT1PowerSource *source = nullptr;
    hpbat::Info info{};
    volatile UInt32 infoDirty = 1;
    UInt32 infoAge = 0;
    UInt32 polls = 0;
    hpbat::ACPowerPolicy powerPolicy{};
    UInt32 policySubmissions = 0;
    bool infoValid = false;
    bool registered = false;
    bool attached = false;
    bool started = false;
    bool pmStarted = false;
    bool gateAdded = false;
    bool timerAdded = false;
    bool boardQualified = false;
    bool stopping = false;
    bool awake = true;
    const char *qualificationFailure = "not evaluated";
    static constexpr const char *qualifiedKernel =
        "Darwin Kernel Version 25.6.0: Tue Aug 18 17:46:40 PDT 2026; root:xnu-12377.161.15.700.19~2/RELEASE_X86_64";
    static void initialBuildObservation(IOService *provider) {
        auto root = IORegistryEntry::getRegistryRoot();
        auto object = root ? root->copyProperty(kOSBuildVersionKey) : nullptr;
        auto build = OSDynamicCast(OSString, object);
        if (build) provider->setProperty("HPBAT1InitialOSBuild", build);
        else provider->setProperty("HPBAT1InitialOSBuild", object ? "<non-string>" : "<absent>");
        if (object) object->release();
    }
    bool osBuildReady() {
        // Unlike mutable kern.osversion storage, copyProperty retains one
        // immutable OSString snapshot while launchd publishes build identity.
        auto root = IORegistryEntry::getRegistryRoot();
        auto object = root ? root->copyProperty(kOSBuildVersionKey) : nullptr;
        auto build = OSDynamicCast(OSString, object);
        const bool ready = build && build->isEqualTo("25G241");
        const bool pending = !object || (build && build->getLength() == 0);
        const char *state = ready ? "qualified" : (pending ? "pending" : "mismatch");
        setProperty("HPBAT1OSBuildState", state);
        battery->setProperty("HPBAT1OSBuildState", state);
        if (build) {
            setProperty("HPBAT1ObservedOSBuild", build);
            battery->setProperty("HPBAT1ObservedOSBuild", build);
        } else {
            const char *observed = object ? "<non-string>" : "<absent>";
            setProperty("HPBAT1ObservedOSBuild", observed);
            battery->setProperty("HPBAT1ObservedOSBuild", observed);
        }
        if (object) object->release();
        if (!ready) {
            setProperty("HPBAT1DependencyState", pending ? "waiting for OS build" : "OS build refused");
            failed(pending ? "OS build not published yet" : "OS build identity mismatch");
        }
        return ready;
    }
    void startStage(IOService *provider, const char *stage) {
        // Retain the reason on the existing BAT1 provider even if this service
        // fails start and is detached. Static strings only, no identifiers.
        provider->setProperty("HPBAT1StartBuild", "0.1.3");
        provider->setProperty("HPBAT1StartStage", stage);
    }
    bool refuseStart(IOService *provider, const char *reason) {
        provider->setProperty("HPBAT1StartFailure", reason);
        startStage(provider, "refused");
        IOLog("HPBAT1Bridge0.1.3: start refused: %s\n", reason);
        return false;
    }

    static bool named(IORegistryEntry *entry, const char *name) {
        return entry && !strcmp(entry->getName(gIOACPIPlane), name);
    }
    static bool pciWord(IORegistryEntry *entry, const char *key, UInt16 expected) {
        auto data = OSDynamicCast(OSData, entry->getProperty(key));
        if (!data || data->getLength() != 4) return false;
        const auto bytes = static_cast<const UInt8 *>(data->getBytesNoCopy());
        return (UInt16(bytes[0]) | (UInt16(bytes[1]) << 8)) == expected && !bytes[2] && !bytes[3];
    }
    static IOACPIPlatformDevice *child(IORegistryEntry *parent, const char *name) {
        OSIterator *it = parent ? parent->getChildIterator(gIOACPIPlane) : nullptr;
        IOACPIPlatformDevice *found = nullptr;
        if (it) {
            while (auto entry = OSDynamicCast(IORegistryEntry, it->getNextObject())) {
                if (named(entry, name)) {
                    found = OSDynamicCast(IOACPIPlatformDevice, entry);
                    if (found) found->retain();
                    break;
                }
            }
            it->release();
        }
        return found;
    }
    bool qualify(IOService *provider) {
        if (version_major != 25 || version_minor != 6 || version_revision != 0 ||
            strcmp(version, qualifiedKernel)) {
            qualificationFailure = "kernel identity mismatch"; return false;
        }
        battery = OSDynamicCast(IOACPIPlatformDevice, provider);
        if (!battery || !named(battery, "BAT1")) {
            qualificationFailure = "provider is not BAT1 ACPI device"; return false;
        }
        auto lpcb = battery->getParentEntry(gIOACPIPlane);
        auto pc00 = lpcb ? lpcb->getParentEntry(gIOACPIPlane) : nullptr;
        auto sb = pc00 ? pc00->getParentEntry(gIOACPIPlane) : nullptr;
        if (!named(lpcb, "LPCB") || !named(pc00, "PC00") || !named(sb, "_SB")) {
            qualificationFailure = "BAT1 ACPI ancestry mismatch"; return false;
        }
        // ACAD can be published later than BAT1. Acquire it only from poll,
        // on the same workloop gate as the existing exact PCI readiness check.
        qualificationFailure = "none";
        return true;
    }
    bool dependenciesReady() {
        if (!boardQualified) {
            boardQualified = exactBoard();
            setProperty("HPBAT1BoardQualified", boardQualified);
            if (!boardQualified) {
                setProperty("HPBAT1DependencyState", "waiting for exact HP PCI identity");
                failed("exact HP PCI identity unavailable"); return false;
            }
        }
        if (!adapter) adapter = child(battery->getParentEntry(gIOACPIPlane), "ACAD");
        if (!adapter) {
            setProperty("HPBAT1DependencyState", "waiting for ACAD");
            failed("ACAD provider unavailable"); return false;
        }
        if (!adapterNotify) adapterNotify = adapter->registerInterest(gIOGeneralInterest, interest, this);
        if (!adapterNotify) {
            setProperty("HPBAT1DependencyState", "waiting for ACAD interest");
            failed("ACAD interest registration failed"); return false;
        }
        setProperty("HPBAT1DependencyState", "ready");
        return true;
    }
    bool exactBoard() {
        // PCI properties reside on the IOPCIDevice, not its ACPI node.
        // Require the native acpi-device object to be this machine's HDAS;
        // an unrelated PCI device with the same IDs cannot qualify the board.
        auto lpcb = battery->getParentEntry(gIOACPIPlane);
        auto pc00 = lpcb ? lpcb->getParentEntry(gIOACPIPlane) : nullptr;
        auto hdas = child(pc00, "HDAS");
        OSDictionary *match = serviceMatching("IOPCIDevice");
        OSIterator *it = match ? getMatchingServices(match) : nullptr;
        bool exact = false;
        if (it && hdas) {
            while (auto pci = OSDynamicCast(IOService, it->getNextObject())) {
                if (pci->getProperty("acpi-device") == hdas &&
                    pciWord(pci, "vendor-id", 0x8086) && pciWord(pci, "device-id", 0x51ca) &&
                    pciWord(pci, "subsystem-vendor-id", 0x103c) && pciWord(pci, "subsystem-id", 0x8bdf)) {
                    exact = true; break;
                }
            }
        }
        if (it) it->release();
        if (match) match->release();
        if (hdas) hdas->release();
        return exact;
    }
    bool numericPackage(const char *method, UInt32 total, UInt32 numeric, uint64_t *v) {
        OSObject *result = nullptr;
        const IOReturn status = battery->evaluateObject(method, &result);
        auto package = OSDynamicCast(OSArray, result);
        bool valid = status == kIOReturnSuccess && package && package->getCount() == total;
        for (UInt32 i = 0; valid && i < numeric; ++i) {
            auto n = OSDynamicCast(OSNumber, package->getObject(i));
            if (!n) valid = false; else v[i] = n->unsigned64BitValue();
        }
        if (result) result->release();
        return valid;
    }
    bool readInformation() {
        uint64_t numbers[16]{};
        hpbat::Info next{};
        bool valid = numericPackage("_BIX", 20, 16, numbers) &&
            hpbat::parseInfo(numbers, 16, true, next) == hpbat::Error::None;
        if (!valid) valid = numericPackage("_BIF", 13, 9, numbers) &&
            hpbat::parseInfo(numbers, 9, false, next) == hpbat::Error::None;
        if (valid) { info = next; infoAge = 0; }
        infoValid = valid;
        return valid;
    }
    void failed(const char *reason) {
        setProperty("HPBAT1LastError", reason);
        setProperty("HPBAT1SampleValid", false);
        if (registered) source->stale();
    }
    void publishPowerPolicy(UInt32 psr) {
        // poll/changeState/quiesce share this workloop gate. The root domain is
        // the boot-lifetime singleton; borrow it only for this synchronous call.
        const auto result = powerPolicy.publish(psr, !stopping && awake,
            [this](uint32_t message) {
                auto root = IOService::getPMRootDomain();
                if (!root) {
                    setProperty("HPBAT1PowerPolicyState", "waiting for root domain");
                    return false;
                }
                // Direct typed alias avoids the old SDK RootDomain vtable.
                // The kernel queues only the integer message, never this object.
                const IOReturn status = hpbatNotifyACPolicy(root, message);
                setProperty("HPBAT1PowerPolicySubmitResult", static_cast<UInt32>(status), 32);
                if (status != kIOReturnSuccess) {
                    setProperty("HPBAT1PowerPolicyState", "submission failed; will retry");
                    return false;
                }
                return true;
            });
        if (result == hpbat::PolicyResult::Submitted) {
            if (policySubmissions != 0xffffffffu) ++policySubmissions;
            setProperty("HPBAT1PowerPolicySubmissions", policySubmissions, 32);
            setProperty("HPBAT1PowerPolicyExternalSubmitted", psr == 1);
            setProperty("HPBAT1PowerPolicyState", "submitted; kernel handling unconfirmed");
        }
    }
    void publishReady() {
        setProperty("HPBAT1LastError", "none");
        setProperty("HPBAT1SampleValid", true);
        setProperty("HPBAT1SuccessfulSamples", ++polls, 32);
        if (!registered) { source->registerService(); registered = true; }
    }
    void poll() {
        if (stopping || !awake) return;
        // Dependency acquisition is non-blocking and serialized. No firmware
        // methods before exact board identity, ACAD and its notifier are ready.
        if (!osBuildReady() || !dependenciesReady()) return;
        UInt32 sta = 0, psr = 0;
        if (battery->evaluateInteger("_STA", &sta) != kIOReturnSuccess ||
            (sta & 0xf) != 0xf || (sta & ~UInt32(0x1f))) {
            failed("invalid _STA"); return;
        }
        if (adapter->evaluateInteger("_PSR", &psr) != kIOReturnSuccess || psr > 1) {
            failed("invalid _PSR"); return;
        }
        // The validated adapter state is independent of capacity/_BST success.
        // An invalid or failed _PSR returned above and cannot invent a disconnect.
        publishPowerPolicy(psr);
        if (!(sta & 0x10)) {
            infoValid = false;
            source->absent(psr == 1);
            publishReady();
            return;
        }
        // Clear the flag BEFORE evaluating: a synchronous firmware Notify in
        // _BST then survives for the following poll. No ACPI in notify callback.
        const bool refresh = OSCompareAndSwap(1, 0, &infoDirty);
        if ((!infoValid || refresh || ++infoAge >= 12) && !readInformation()) {
            failed("invalid _BIX/_BIF"); return;
        }
        uint64_t bst[4]{};
        hpbat::Snapshot next{};
        if (!numericPackage("_BST", 4, 4, bst) ||
            hpbat::parseState(bst, 4, psr, info, next) != hpbat::Error::None) {
            failed("invalid _BST"); return;
        }
        source->publish(next);
        publishReady();
    }
    static void tick(OSObject *owner, IOTimerEventSource *) {
        auto self = OSDynamicCast(HPBAT1Bridge, owner);
        if (!self || self->stopping || !self->awake) return;
        self->poll();
        if (!self->stopping && self->awake) self->timer->setTimeoutMS(5000);
    }
    static IOReturn interest(void *target, void *, UInt32 type, IOService *, void *, vm_size_t) {
        auto self = static_cast<HPBAT1Bridge *>(target);
        if (type == kIOACPIMessageDeviceNotification) OSBitOrAtomic(1, &self->infoDirty);
        return kIOReturnSuccess;
    }
    static IOReturn changeState(OSObject *owner, void *state, void *, void *, void *) {
        auto self = OSDynamicCast(HPBAT1Bridge, owner);
        if (!self || self->stopping) return kIOReturnSuccess;
        self->awake = state != nullptr;
        self->powerPolicy.invalidate();
        self->setProperty("HPBAT1PowerPolicyState", "awaiting valid sample after power transition");
        self->timer->cancelTimeout();
        self->infoValid = false;
        OSBitOrAtomic(1, &self->infoDirty);
        if (self->awake) self->timer->setTimeoutMS(1000);
        return kIOReturnSuccess;
    }
    static IOReturn quiesce(OSObject *owner, void *, void *, void *, void *) {
        auto self = OSDynamicCast(HPBAT1Bridge, owner);
        if (self) {
            self->stopping = true;
            self->powerPolicy.invalidate();
            if (self->timer) self->timer->cancelTimeout();
        }
        return kIOReturnSuccess;
    }
    void cleanup() {
        if (pmStarted) { PMstop(); pmStarted = false; }
        if (gateAdded) gate->runAction(quiesce);
        if (adapterNotify) { adapterNotify->remove(); adapterNotify = nullptr; }
        if (source) {
            if (registered) {
                source->terminate(kIOServiceRequired | kIOServiceSynchronous);
                registered = false;
                // terminate may already stop and detach the child.
                if (source->getProvider() != this) { started = false; attached = false; }
            }
            if (started) { source->stop(this); started = false; }
            if (attached) { source->detach(this); attached = false; }
            source->release(); source = nullptr;
        }
        if (timer) { timer->cancelTimeout(); if (timerAdded) loop->removeEventSource(timer); timerAdded = false; timer->release(); timer = nullptr; }
        if (gate) { if (gateAdded) loop->removeEventSource(gate); gateAdded = false; gate->release(); gate = nullptr; }
        if (loop) { loop->release(); loop = nullptr; }
        if (adapter) { adapter->release(); adapter = nullptr; }
    }
public:
    bool start(IOService *provider) override {
        startStage(provider, "qualification");
        provider->setProperty("HPBAT1ObservedKernelVersion", version);
        provider->setProperty("HPBAT1ObservedDarwinMajor", static_cast<UInt32>(version_major), 32);
        provider->setProperty("HPBAT1ObservedDarwinMinor", static_cast<UInt32>(version_minor), 32);
        provider->setProperty("HPBAT1ObservedDarwinRevision", static_cast<UInt32>(version_revision), 32);
        initialBuildObservation(provider);
        if (!qualify(provider)) return refuseStart(provider, qualificationFailure);
        startStage(provider, "parent-start");
        if (!IOService::start(provider)) { cleanup(); return refuseStart(provider, "parent start failed"); }
        const char *failure = "allocation failed";
        startStage(provider, "allocation");
        loop = IOWorkLoop::workLoop();
        gate = IOCommandGate::commandGate(this);
        timer = IOTimerEventSource::timerEventSource(this, tick);
        source = new HPBAT1PowerSource;
        if (!loop || !gate || !timer || !source) goto fail;
        failure = "power source init failed";
        startStage(provider, "source-init");
        if (!source->init()) goto fail;
        failure = "command gate attach failed";
        startStage(provider, "gate-attach");
        gateAdded = loop->addEventSource(gate) == kIOReturnSuccess;
        if (!gateAdded) goto fail;
        failure = "timer attach failed";
        startStage(provider, "timer-attach");
        timerAdded = loop->addEventSource(timer) == kIOReturnSuccess;
        if (!timerAdded) goto fail;
        failure = "power source attach failed";
        startStage(provider, "source-attach");
        attached = source->attach(this);
        if (!attached) goto fail;
        failure = "power source start failed";
        startStage(provider, "source-start");
        started = source->start(this);
        if (!started) goto fail;
        setProperty("HPBAT1BuildGuard", "25G241");
        setProperty("HPBAT1DriverVersion", "0.1.3");
        setProperty("HPBAT1BoardGuard", "HDAS 8086:51ca subsystem 103c:8bdf");
        setProperty("HPBAT1SampleValid", false);
        setProperty("HPBAT1PowerPolicyState", "awaiting first valid adapter sample");
        setProperty("HPBAT1DependencyState", "pending first poll");
        {
            // Observe sleep/wake; no charge/power hardware programming.
            static IOPMPowerState states[2] = {
                {1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0},
                {1, kIOPMPowerOn, kIOPMPowerOn, kIOPMPowerOn, 0, 0, 0, 0, 0, 0, 0, 0}
            };
            failure = "power driver registration failed";
            startStage(provider, "power-registration");
            PMinit(); pmStarted = true;
            provider->joinPMtree(this);
            if (registerPowerDriver(this, states, 2) != kIOReturnSuccess) goto fail;
        }
        provider->setProperty("HPBAT1StartFailure", "none");
        startStage(provider, "started-awaiting-dependencies");
        IOLog("HPBAT1Bridge0.1.3: started, dependency qualification deferred to timer\n");
        timer->setTimeoutMS(1000);
        return true;
    fail:
        cleanup(); IOService::stop(provider); return refuseStart(provider, failure);
    }
    IOReturn message(UInt32 type, IOService *provider, void *argument = nullptr) override {
        if (type == kIOACPIMessageDeviceNotification) {
            OSBitOrAtomic(1, &infoDirty);
            return kIOReturnSuccess;
        }
        return IOService::message(type, provider, argument);
    }
    IOReturn setPowerState(unsigned long state, IOService *) override {
        if (gate) gate->runAction(changeState, state ? reinterpret_cast<void *>(1) : nullptr);
        return kIOPMAckImplied;
    }
    void stop(IOService *provider) override { cleanup(); IOService::stop(provider); }
    void free() override { cleanup(); IOService::free(); }
};
OSDefineMetaClassAndStructors(HPBAT1Bridge, IOService)

extern "C" kern_return_t HPBAT1Bridge_kern_start(kmod_info_t *, void *) { return KERN_SUCCESS; }
// Experimental boot-only candidate: don't unload a live power source.
extern "C" kern_return_t HPBAT1Bridge_kern_stop(kmod_info_t *, void *) { return KERN_FAILURE; }
