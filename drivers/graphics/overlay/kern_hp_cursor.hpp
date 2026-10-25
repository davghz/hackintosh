#pragma once
#include <stdint.h>

namespace HPCursor {
// Display 13 Wa_22012358565: a 32-bit cursor requires ARB_SLOTS=1.
// References: Linux v6.12 intel_cursor.c, intel_display.c, i915_reg.h.
// This narrow HP trial preserves firmware arbitration policy: it changes ONLY
// active pipe-A cursor writes when programmable slots are already enabled.
// Enabling PIPE_ARB_USE_PROG_SLOTS ourselves would also require reviewing every
// primary/overlay plane; do not silently introduce that broader experiment.
constexpr uint64_t ControlA = 0x70080;
constexpr uint32_t ArbControlA = 0x70028;
constexpr uint32_t ProgrammableSlots = 1U << 13;
constexpr uint32_t SlotMask = 7U << 28;
constexpr uint32_t OneSlot = 1U << 28;
constexpr uint32_t ModeMask = 0x27;

inline bool activeArgb(uint32_t value) {
    const uint32_t mode = value & ModeMask;
    return mode == 0x22 || mode == 0x23 || mode == 0x27;
}

inline uint32_t filter(bool qualified, uint64_t reg, uint32_t value,
                       uint32_t pipeArbitration) {
    if (!qualified || reg != ControlA || !activeArgb(value) ||
        value == 0xFFFFFFFFU || pipeArbitration == 0xFFFFFFFFU ||
        !(pipeArbitration & ProgrammableSlots))
        return value;
    return (value & ~SlotMask) | OneSlot;
}
}
