// HP-only ABI correction, qualified against kernel 25G241 and its vtable.
#pragma once
#include <stddef.h>
#include <stdint.h>
namespace HPNvram {
constexpr char SaveSymbol[] = "__ZN24AppleIntelBaseController11hwSaveNVRAMEv";
constexpr char WriteSymbol[] = "__ZN18IODTPlatformExpert18writeNVRAMPropertyEP15IORegistryEntryPK8OSSymbolP6OSData";
constexpr char ReservedSymbol[] = "__ZN18IODTPlatformExpert28_RESERVEDIODTPlatformExpert1Ev";
constexpr char VtableSymbol[] = "__ZTV18IODTPlatformExpert";
constexpr size_t ContextOffset = 0x151, PatchOffset = 0x166;
constexpr uint8_t Context[] = {0x49, 0x8b, 0xb7, 0x60, 0x0c, 0x00, 0x00, 0x49, 0x8b, 0x06, 0x4c, 0x89, 0xf7, 0x4c, 0x89, 0xe2, 0x48, 0x89, 0xd9, 0xff, 0x90, 0xf8, 0x09, 0x00, 0x00, 0x41, 0x89, 0xc6, 0x48, 0x85, 0xdb, 0x74, 0x17};
constexpr uint8_t Entry[] = {0x55, 0x48, 0x89, 0xe5, 0x41, 0x57, 0x41, 0x56, 0x41, 0x54, 0x53, 0x48, 0x81, 0xec, 0x00, 0x01, 0x00, 0x00};
constexpr uint8_t WriteEntry[] = {0x55, 0x48, 0x89, 0xe5, 0x48, 0x8b, 0xbf, 0xe0, 0x00, 0x00, 0x00, 0x48, 0x85, 0xff};
inline bool prepare(const uint8_t *function, size_t length, bool kernelSlotsVerified) {
    if (!function || !kernelSlotsVerified || length < ContextOffset + sizeof(Context)) return false;
    for (size_t i=0;i<sizeof(Entry);++i) if (function[i]!=Entry[i]) return false;
    for (size_t i=0;i<sizeof(Context);++i) if (function[ContextOffset+i]!=Context[i]) return false;
    return true;
}
}
