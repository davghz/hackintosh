// HP-only correction for the qualified TGL 16.0.32 framebuffer.
// No IOKit dependency: the production matcher is tested against the donor bytes.
#pragma once
#include <stddef.h>
#include <stdint.h>

namespace HPDvmt {
constexpr size_t Window = 0x100;
constexpr size_t PatchSize = 8;
constexpr uint8_t Expected[] = {
    0xc1, 0xe0, 0x11,                         // shl eax, 17
    0x25, 0x00, 0x00, 0x00, 0xfe,             // and eax, 0xfe000000
    0x41, 0x89, 0x84, 0x24, 0xe4, 0x0d, 0, 0 // mov [r12+0xde4], eax
};

inline bool prepare(const uint8_t *function, size_t length, uint32_t reserved,
                    size_t &offset, uint8_t (&replacement)[PatchSize]) {
    // This candidate is qualified only for this HP's measured 60 MiB allocation.
    if (!function || length < Window || reserved != 60U * 1024U * 1024U)
        return false;
    size_t count = 0, found = 0;
    for (size_t i = 0; i + sizeof(Expected) <= Window; ++i) {
        bool equal = true;
        for (size_t j = 0; j < sizeof(Expected); ++j)
            if (function[i+j] != Expected[j]) { equal = false; break; }
        if (equal) { ++count; found = i; }
    }
    // Exact offset from FBMemMgr_Init in the qualified debug donor; no fuzzy patch.
    if (count != 1 || found != 0xad) return false;
    offset = found;
    replacement[0] = 0xb8; // mov eax, reserved; same result register, no overrun
    for (size_t i = 0; i < 4; ++i) replacement[i+1] = reserved >> (8*i);
    replacement[5] = replacement[6] = replacement[7] = 0x90;
    return true;
}
}
