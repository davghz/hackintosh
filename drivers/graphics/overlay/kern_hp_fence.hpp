// HP 8BDF / A7A1 only. Keep the boot surface tiled; exclude its linear
// cursor/DSB reservation. This policy does not write registers or resize memory.
#pragma once
#include <stdint.h>

namespace HPFence {
constexpr uint64_t MiB = 1024ULL * 1024;
constexpr uint64_t Reserved = 60 * MiB;
constexpr uint64_t OldSize = 64 * MiB;
constexpr uint64_t Pitch = 1920 * 4;
struct Range { uint64_t start, size; };
struct Layout {
    uint32_t reserved;
    uint64_t cursorStart;
    uint32_t cursorBytes;
    uint64_t dsbStart;
};
inline bool layoutValid(const Layout &l) {
    return l.reserved == Reserved && l.cursorStart == Reserved &&
        l.cursorBytes >= 0x80000 && l.cursorBytes <= 0x180000 &&
        !(l.cursorBytes % 0x80000) && l.dsbStart == Reserved + l.cursorBytes;
}
inline bool matches(uint64_t index, const Range &r, uint64_t pitch, uint32_t tile) {
    return index == 0 && r.start == 0 && r.size == OldSize && pitch == Pitch && tile == 2;
}
inline Range adjusted(bool qualified, const Layout &l, uint64_t index,
                      const Range &r, uint64_t pitch, uint32_t tile) {
    return qualified && layoutValid(l) && matches(index, r, pitch, tile)
        ? Range{r.start, Reserved} : r;
}
}
