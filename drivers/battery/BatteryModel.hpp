#pragma once
// HP BAT1 ACPI values only. No I/O, allocation, globals or synthetic readings.
#include <stdint.h>
#include <stddef.h>

namespace hpbat {
constexpr uint64_t unknown32 = 0xffffffffULL;
inline bool known(uint64_t n) { return n < unknown32; }
enum class Error { None, Package, Revision, Units, Capacity, Voltage, State, Adapter, Overflow };
struct Info {
    uint32_t units, design, full, designVoltage, warning, low;
    bool designKnown, voltageKnown, warningKnown, lowKnown;
};
struct Snapshot {
    uint32_t remaining, full, design, voltage;
    int32_t amperage, minutes;
    bool external, charging, critical, warning, warningKnown;
    bool designKnown, voltageKnown, rateKnown;
};
inline Error parseInfo(const uint64_t *v, size_t count, bool bix, Info &out) {
    // Numeric prefix before the strings: _BIX revision0=16; _BIF=9.
    if (!v || count != (bix ? 16U : 9U)) return Error::Package;
    if (bix && v[0] != 0) return Error::Revision;
    const size_t i = bix ? 1 : 0;
    if (v[i] > 1) return Error::Units;
    if (!known(v[i+2]) || !v[i+2]) return Error::Capacity;
    if (v[i] == 0 && (!known(v[i+4]) || !v[i+4])) return Error::Voltage;
    out = {};
    out.units = static_cast<uint32_t>(v[i]);
    out.full = static_cast<uint32_t>(v[i+2]);
    out.designKnown = known(v[i+1]) && v[i+1] != 0;
    out.design = out.designKnown ? static_cast<uint32_t>(v[i+1]) : 0;
    out.voltageKnown = known(v[i+4]) && v[i+4] != 0;
    out.designVoltage = out.voltageKnown ? static_cast<uint32_t>(v[i+4]) : 0;
    out.warningKnown = known(v[i+5]);
    out.warning = out.warningKnown ? static_cast<uint32_t>(v[i+5]) : 0;
    out.lowKnown = known(v[i+6]);
    out.low = out.lowKnown ? static_cast<uint32_t>(v[i+6]) : 0;
    return Error::None;
}
inline bool capacity(uint32_t raw, const Info &info, uint32_t &mah) {
    if (info.units > 1 || (info.units == 0 && !info.designVoltage)) return false;
    const uint64_t n = info.units == 0 ? uint64_t(raw) * 1000 / info.designVoltage : raw;
    if (n > 0x7fffffffULL) return false;
    mah = static_cast<uint32_t>(n);
    return true;
}
inline Error parseState(const uint64_t *v, size_t count, uint64_t adapter,
                        const Info &info, Snapshot &out) {
    if (!v || count != 4) return Error::Package;
    if (info.units > 1) return Error::Units;
    if (!info.full) return Error::Capacity;
    if (info.units == 0 && !info.designVoltage) return Error::Voltage;
    if (v[0] > 7 || (v[0] & 3) == 3) return Error::State;
    if (adapter > 1) return Error::Adapter;
    if (!known(v[2])) return Error::Capacity;
    if ((v[0] & 2) && adapter == 0) return Error::State;
    out = {};
    out.minutes = -1;
    out.external = adapter == 1;
    out.charging = (v[0] & 2) != 0;
    out.critical = (v[0] & 4) != 0;
    out.warningKnown = info.warningKnown;
    out.warning = info.warningKnown && v[2] <= info.warning;
    out.designKnown = info.designKnown;
    out.voltageKnown = known(v[3]) && v[3] != 0;
    out.voltage = out.voltageKnown ? static_cast<uint32_t>(v[3]) : 0;
    if (!capacity(static_cast<uint32_t>(v[2]), info, out.remaining) ||
        !capacity(info.full, info, out.full) || out.full == 0 ||
        (out.designKnown && !capacity(info.design, info, out.design))) return Error::Overflow;
    // _BST returns magnitude, not a signed 16-bit BAC0 register. The firmware
    // already took abs(BAC0) and converted mA to mW when power-unit=0.
    out.rateKnown = known(v[1]) && (info.units == 1 || out.voltageKnown);
    if ((v[0] & 3) == 0 && v[1] != 0) out.rateKnown = false;
    if (out.rateKnown) {
        const uint64_t magnitude = info.units == 0 ? v[1] * 1000 / out.voltage : v[1];
        if (magnitude > 0x7fffffffULL) return Error::Overflow;
        out.amperage = static_cast<int32_t>(magnitude);
        if (v[0] & 1) out.amperage = -out.amperage;
        if (v[1] != 0 && (v[0] & 3)) {
            const uint64_t available = out.charging ? (v[2] >= info.full ? 0 : info.full-v[2]) : v[2];
            const uint64_t minutes = available * 60 / v[1];
            if (minutes <= 0x7fffffffULL) out.minutes = static_cast<int32_t>(minutes);
        }
    }
    return Error::None;
}
}
