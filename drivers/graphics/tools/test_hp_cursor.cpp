#include "../overlay/kern_hp_cursor.hpp"
#include <cassert>
#include <cstdio>
#include <initializer_list>

int main() {
    using namespace HPCursor;
    // Actual captured HP registers from the successful synchronization boot.
    assert(filter(true, ControlA, 0x27U, 0x2a0fU) == 0x10000027U);
    assert(filter(true, ControlA, 0x27U, 0x0a0fU) == 0x27U);
    assert(filter(true, ControlA, 0x10000027U, 0x2a0fU) == 0x10000027U);
    // Exercise both eligibility and preservation of every unrelated bit.
    uint32_t random = 0x84A70C31U;
    for (unsigned i = 0; i < 200000; ++i) {
        random = random * 1664525U + 1013904223U;
        const uint32_t value = random;
        assert(filter(false, ControlA, value, ProgrammableSlots) == value);
        assert(filter(true, ControlA, value, 0) == value);
        assert(filter(true, ControlA, value, 0xFFFFFFFFU) == value);
        for (auto reg : {0x70028ULL, 0x70084ULL, 0x70088ULL, 0x70180ULL,
                         0x71080ULL, 0x72080ULL, 0x170080ULL, 0xFFFF000000070080ULL})
            assert(filter(true, reg, value, ProgrammableSlots) == value);
        const uint32_t result = filter(true, ControlA, value, ProgrammableSlots);
        assert(((value ^ result) & ~SlotMask) == 0);
        assert(filter(true, ControlA, result, ProgrammableSlots) == result);
        if (!activeArgb(value) || value == 0xFFFFFFFFU) assert(result == value);
    }
    for (uint32_t mode : {0x22U, 0x23U, 0x27U}) {
        assert(filter(true, ControlA, mode, ProgrammableSlots) == (OneSlot | mode));
        assert(filter(true, ControlA, mode | SlotMask, ProgrammableSlots) == (OneSlot | mode));
    }
    for (uint32_t disabled : {0U, OneSlot, SlotMask})
        assert(filter(true, ControlA, disabled, ProgrammableSlots) == disabled);
    assert(filter(true, ControlA, 0xFFFFFFFFU, ProgrammableSlots) == 0xFFFFFFFFU);
    puts("PASS: cursor filter preserves modes and unrelated registers/bits; wrong HP/mode/arbitration rejected; 200000 randomized cases.");
}
