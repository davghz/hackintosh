#include "kern_hp_dvmt.hpp"
#include "kern_hp8bdf.hpp"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>

int main(int argc, char **argv) {
    assert(argc == 2);
    uint8_t original[HPDvmt::Window];
    FILE *f = fopen(argv[1], "rb");
    assert(f && fread(original, 1, sizeof(original), f) == sizeof(original));
    fclose(f);
    size_t offset = 999;
    uint8_t replacement[HPDvmt::PatchSize] = {};
    const uint32_t reserved = HP8BDF::stolenBytes(0xfe);
    assert(reserved == 60U*1024U*1024U);
    assert(((0xfec1U << 17) & 0xfe000000U) == 4032U*1024U*1024U);
    assert(HPDvmt::prepare(original, sizeof(original), reserved, offset, replacement));
    assert(offset == 0xad);
    const uint8_t expected[] = {0xb8,0x00,0x00,0xc0,0x03,0x90,0x90,0x90};
    assert(!memcmp(replacement, expected, sizeof(expected)));
    uint8_t data[HPDvmt::Window];
    memcpy(data, original, sizeof(data));
    memcpy(data+offset, replacement, sizeof(replacement));
    assert(!memcmp(data, original, offset));
    assert(!memcmp(data+offset+8, original+offset+8, sizeof(data)-offset-8));
    assert(!HPDvmt::prepare(data, sizeof(data), reserved, offset, replacement));
    assert(!HPDvmt::prepare(nullptr, sizeof(data), reserved, offset, replacement));
    for (size_t length = 0; length < sizeof(data); ++length)
        assert(!HPDvmt::prepare(original, length, reserved, offset, replacement));
    for (size_t byte = 0; byte < sizeof(HPDvmt::Expected); ++byte) {
        memcpy(data, original, sizeof(data));
        data[0xad+byte] ^= 1;
        assert(!HPDvmt::prepare(data, sizeof(data), reserved, offset, replacement));
    }
    memcpy(data, original, sizeof(data));
    memcpy(data+0x20, HPDvmt::Expected, sizeof(HPDvmt::Expected));
    assert(!HPDvmt::prepare(data, sizeof(data), reserved, offset, replacement));
    memset(data, 0, sizeof(data));
    memcpy(data+0xae, HPDvmt::Expected, sizeof(HPDvmt::Expected));
    assert(!HPDvmt::prepare(data, sizeof(data), reserved, offset, replacement));
    for (unsigned int gms = 0; gms < 256; ++gms)
        if (gms != 0xfe)
            assert(!HPDvmt::prepare(original, sizeof(original), HP8BDF::stolenBytes(gms), offset, replacement));
    puts("PASS: exact donor, 4032-to-60 MiB correction, byte-preserving patch, 256 bounds, all 16 signature mutations, duplicate/moved/already-patched signatures, 255 other GMS values");
}
