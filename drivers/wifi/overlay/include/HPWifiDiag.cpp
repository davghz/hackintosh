#include "HPWifiDiag.h"
#include <IOKit/IORegistryEntry.h>
#include <IOKit/IOLib.h>

static volatile uint32_t hpDiagCount;
static volatile uint32_t hpDiagAttempt;
static volatile uint32_t hpDiagFailure;
static volatile uint32_t hpDiagWrapperBegun;
static volatile uint32_t hpDiagStartupActive = 1;
static volatile uint32_t hpDiagIRQCounts[HPWifiDiagIRQCount];
static volatile uint32_t hpDiagIRQCaptured;
static volatile uint32_t hpDiagDeviceCaptured;
static volatile uint32_t hpDiagBootStatusCaptured;

static void hpDiagNumber(IORegistryEntry *root, const char *name, uint32_t value)
{
    root->setProperty(name, static_cast<unsigned long long>(value), 32);
}

void HPWifiDiagBegin()
{
    bool first = __sync_bool_compare_and_swap(&hpDiagWrapperBegun, 0, 1);
    IORegistryEntry *root = IORegistryEntry::getRegistryRoot();
    if (root) {
        root->setProperty("hp-wifi-diag-build", "0.1.4");
        // This single-adapter start runs before its controller is published.
        // Reset exactly once; retain the first error across later attempts.
        if (first) {
            hpDiagNumber(root, "hp-wifi-diag-first-failure-result", 0);
            hpDiagNumber(root, "hp-wifi-diag-first-failure-stage", 0);
            __sync_lock_test_and_set(&hpDiagFailure, 0);
        }
    }
    HPWifiDiag(10);
}

void HPWifiDiag(uint32_t stage, int32_t result, bool failure)
{
    // Firmware preinit is also used after startup. Do not let a later wake or
    // association overwrite startup evidence. A controller retry reopens it.
    if (stage == 100) {
        __sync_lock_test_and_set(&hpDiagStartupActive, 1);
        __sync_add_and_fetch(&hpDiagAttempt, 1);
    }
    if (!hpDiagStartupActive && stage > 13)
        return;
    if (failure || stage == 499 || stage == 900)
        HPWifiDiagCaptureTrace();
    uint32_t count = __sync_add_and_fetch(&hpDiagCount, 1);
    IORegistryEntry *root = IORegistryEntry::getRegistryRoot();
    if (root) {
        root->setProperty("hp-wifi-diag-build", "0.1.4");
        hpDiagNumber(root, "hp-wifi-diag-attempt", hpDiagAttempt);
        hpDiagNumber(root, "hp-wifi-diag-count", count);
        if (failure && __sync_bool_compare_and_swap(&hpDiagFailure, 0, 1)) {
            hpDiagNumber(root, "hp-wifi-diag-first-failure-result", static_cast<uint32_t>(result));
            hpDiagNumber(root, "hp-wifi-diag-first-failure-stage", stage);
        }
        // Stage is the final field written for this progress sample.
        hpDiagNumber(root, "hp-wifi-diag-result", static_cast<uint32_t>(result));
        hpDiagNumber(root, "hp-wifi-diag-stage", stage);
    }
    // Eight progress lines only: avoid console latency around command ACKs.
    // All stages and the first failure still update persistent root properties.
    if (count <= 8)
        IOLog("HPWiFiDiag stage=%u result=%d\n", stage, result);
    if (stage == 499 || stage == 900)
        __sync_lock_test_and_set(&hpDiagStartupActive, 0);
}

bool HPWifiDiagBool(uint32_t stage, bool result)
{
    HPWifiDiag(stage, result ? 0 : -1, !result);
    return result;
}

int32_t HPWifiDiagResult(uint32_t stage, int32_t result)
{
    HPWifiDiag(stage, result, result != 0);
    return result;
}

void HPWifiDiagIRQEvent(HPWifiDiagIRQKind kind)
{
    // Called in the hard interrupt filter as well as the threaded handler.
    // Do not acquire a lock, call IOLog, allocate, or access the registry here.
    if (static_cast<uint32_t>(kind) >= HPWifiDiagIRQCount ||
        !__atomic_load_n(&hpDiagStartupActive, __ATOMIC_RELAXED) ||
        __atomic_load_n(&hpDiagIRQCaptured, __ATOMIC_RELAXED))
        return;
    __sync_add_and_fetch(&hpDiagIRQCounts[kind], 1);
}

void HPWifiDiagCaptureIRQ()
{
    if (!__atomic_load_n(&hpDiagStartupActive, __ATOMIC_RELAXED))
        return;
    IORegistryEntry *root = IORegistryEntry::getRegistryRoot();
    if (!root || !__sync_bool_compare_and_swap(&hpDiagIRQCaptured, 0, 1))
        return;
    static const char *const names[HPWifiDiagIRQCount] = {
        "hp-wifi-diag-irq-filter", "hp-wifi-diag-irq-action",
        "hp-wifi-diag-irq-rx-batch", "hp-wifi-diag-irq-alive",
        "hp-wifi-diag-irq-pnvm", "hp-wifi-diag-irq-init"
    };
    for (uint32_t i = 0; i < HPWifiDiagIRQCount; ++i)
        hpDiagNumber(root, names[i], __atomic_load_n(&hpDiagIRQCounts[i], __ATOMIC_RELAXED));
    // A last filter already in flight can race its counter's read. The marker
    // means all fields were published, not that they form a hardware snapshot.
    hpDiagNumber(root, "hp-wifi-diag-irq-captured", 1);
}

static bool hpDiagFirmwareEqual(const char *value, const char *known)
{
    if (!value)
        return false;
    for (uint32_t i = 0; i < 64; ++i) {
        if (value[i] != known[i])
            return false;
        if (!known[i])
            return true;
    }
    return false;
}

void HPWifiDiagDevice(const char *firmware, uint32_t hardware, uint32_t radio)
{
    if (!__atomic_load_n(&hpDiagStartupActive, __ATOMIC_RELAXED))
        return;
    IORegistryEntry *root = IORegistryEntry::getRegistryRoot();
    if (!root || !__sync_bool_compare_and_swap(&hpDiagDeviceCaptured, 0, 1))
        return;
    // Publish a known literal only, never an arbitrary caller-provided string.
    // This set is the exact twelve-file pinned build/manifest.json selection.
    static const char *const firmwareNames[] = {
        "iwlwifi-Qu-b0-hr-b0-68.ucode", "iwlwifi-Qu-b0-jf-b0-68.ucode",
        "iwlwifi-Qu-c0-hr-b0-68.ucode", "iwlwifi-Qu-c0-jf-b0-68.ucode",
        "iwlwifi-QuZ-a0-hr-b0-68.ucode", "iwlwifi-QuZ-a0-jf-b0-68.ucode",
        "iwlwifi-cc-a0-68.ucode", "iwlwifi-so-a0-gf-a0-68.ucode",
        "iwlwifi-so-a0-gf4-a0-68.ucode", "iwlwifi-so-a0-hr-b0-68.ucode",
        "iwlwifi-so-a0-jf-b0-68.ucode", "iwlwifi-ty-a0-gf-a0-68.ucode"
    };
    for (uint32_t i = 0; i < sizeof(firmwareNames) / sizeof(firmwareNames[0]); ++i) {
        if (hpDiagFirmwareEqual(firmware, firmwareNames[i])) {
            root->setProperty("hp-wifi-diag-firmware", firmwareNames[i]);
            break;
        }
    }
    hpDiagNumber(root, "hp-wifi-diag-hw-rev", hardware);
    hpDiagNumber(root, "hp-wifi-diag-rf-id", radio);
    hpDiagNumber(root, "hp-wifi-diag-device-captured", 1);
}

void HPWifiDiagBootStatus(uint32_t cpu1, uint32_t cpu2, uint32_t umac, uint32_t lmac)
{
    if (!__atomic_load_n(&hpDiagStartupActive, __ATOMIC_RELAXED))
        return;
    IORegistryEntry *root = IORegistryEntry::getRegistryRoot();
    if (!root || !__sync_bool_compare_and_swap(&hpDiagBootStatusCaptured, 0, 1))
        return;
    hpDiagNumber(root, "hp-wifi-diag-secboot-cpu1", cpu1);
    hpDiagNumber(root, "hp-wifi-diag-secboot-cpu2", cpu2);
    hpDiagNumber(root, "hp-wifi-diag-umac-pc", umac);
    hpDiagNumber(root, "hp-wifi-diag-lmac-pc", lmac);
    hpDiagNumber(root, "hp-wifi-diag-secboot-captured", 1);
}

// Storage is fixed for the module lifetime; slots are never reused. A producer
// owns one slot, writes all six words, then publishes ready with release order.
// No allocation, locks, IOLog, registry access, or MMIO occurs in append.
static const uint32_t hpDiagTraceCapacity = 64;
struct HPWifiTraceSlot {
    uint32_t words[6];
    volatile uint32_t ready;
};
static HPWifiTraceSlot hpDiagTraceSlots[hpDiagTraceCapacity];
static uint32_t hpDiagTraceSnapshot[hpDiagTraceCapacity][6];
static volatile uint32_t hpDiagTraceReserved;
static volatile uint32_t hpDiagTraceDropped;
static volatile uint32_t hpDiagTraceFrozen;
static volatile uint32_t hpDiagTraceCommands;

bool HPWifiDiagCommandBegin()
{
    if (!__atomic_load_n(&hpDiagStartupActive, __ATOMIC_RELAXED) ||
        __atomic_load_n(&hpDiagTraceFrozen, __ATOMIC_RELAXED))
        return false;
    uint32_t count = __atomic_load_n(&hpDiagTraceCommands, __ATOMIC_RELAXED);
    while (count < 2) {
        if (__atomic_compare_exchange_n(&hpDiagTraceCommands, &count, count + 1,
                                        false, __ATOMIC_RELAXED, __ATOMIC_RELAXED))
            return true;
    }
    return false;
}

void HPWifiDiagTrace(HPWifiDiagTraceKind kind, uint32_t a, uint32_t b, uint32_t c, uint32_t d)
{
    if (static_cast<uint32_t>(kind) == 0 ||
        static_cast<uint32_t>(kind) >= HPWifiTraceKindLimit ||
        !__atomic_load_n(&hpDiagStartupActive, __ATOMIC_RELAXED) ||
        __atomic_load_n(&hpDiagTraceFrozen, __ATOMIC_RELAXED))
        return;
    uint32_t slot = __atomic_load_n(&hpDiagTraceReserved, __ATOMIC_RELAXED);
    for (;;) {
        if (slot >= hpDiagTraceCapacity) {
            uint32_t dropped = __atomic_load_n(&hpDiagTraceDropped, __ATOMIC_RELAXED);
            while (dropped != UINT32_MAX &&
                   !__atomic_compare_exchange_n(&hpDiagTraceDropped, &dropped, dropped + 1,
                                                false, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {}
            return;
        }
        if (__atomic_compare_exchange_n(&hpDiagTraceReserved, &slot, slot + 1,
                                        false, __ATOMIC_RELAXED, __ATOMIC_RELAXED))
            break;
    }
    HPWifiTraceSlot *record = &hpDiagTraceSlots[slot];
    record->words[0] = slot;
    record->words[1] = static_cast<uint32_t>(kind);
    record->words[2] = a;
    record->words[3] = b;
    record->words[4] = c;
    record->words[5] = d;
    __atomic_store_n(&record->ready, 1, __ATOMIC_RELEASE);
}

void HPWifiDiagCaptureTrace()
{
    if (!__atomic_load_n(&hpDiagStartupActive, __ATOMIC_RELAXED))
        return;
    IORegistryEntry *root = IORegistryEntry::getRegistryRoot();
    if (!root || !__sync_bool_compare_and_swap(&hpDiagTraceFrozen, 0, 1))
        return;
    uint32_t count = 0;
    uint32_t reserved = __atomic_load_n(&hpDiagTraceReserved, __ATOMIC_RELAXED);
    // Reserved is bounded by the CAS loop. An in-flight producer may complete
    // after its slot is inspected; omit it rather than copying a partial tuple.
    for (uint32_t i = 0; i < reserved; ++i) {
        if (!__atomic_load_n(&hpDiagTraceSlots[i].ready, __ATOMIC_ACQUIRE))
            continue;
        for (uint32_t j = 0; j < 6; ++j)
            hpDiagTraceSnapshot[count][j] = hpDiagTraceSlots[i].words[j];
        ++count;
    }
    // Target is pinned x86_64: native uint32 words serialize little-endian.
    // IORegistry copies the fixed CPU buffer; this runs outside IRQ context.
    bool ok = root->setProperty("hp-wifi-diag-trace-data", hpDiagTraceSnapshot,
                                count * sizeof(hpDiagTraceSnapshot[0]));
    ok = root->setProperty("hp-wifi-diag-trace-version", 1ULL, 32) && ok;
    ok = root->setProperty("hp-wifi-diag-trace-count", static_cast<unsigned long long>(count), 32) && ok;
    ok = root->setProperty("hp-wifi-diag-trace-dropped", static_cast<unsigned long long>(
        __atomic_load_n(&hpDiagTraceDropped, __ATOMIC_RELAXED)), 32) && ok;
    ok = root->setProperty("hp-wifi-diag-trace-incomplete", static_cast<unsigned long long>(reserved - count), 32) && ok;
    if (ok)
        hpDiagNumber(root, "hp-wifi-diag-trace-captured", 1);
}
