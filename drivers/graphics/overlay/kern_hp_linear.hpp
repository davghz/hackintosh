// Read-only address qualification for direct writes to the existing cursor RAM.
#pragma once
#include <stddef.h>
#include <stdint.h>
namespace HPLinear {
constexpr uint64_t Start=0x03c00000, Bytes=0x180000, PerPipe=0x80000, PerImage=0x40000;
constexpr uint64_t PhysMask=0x7ffffff000ULL;
inline bool cpu(uint32_t ebx,uint32_t edx) {
    return (edx & (1U<<19)) && (((ebx>>8)&255)*8)==64;
}
inline bool layout(uint32_t reserved,uint64_t start,uint32_t bytes,uint64_t dsb) {
    return reserved==Start && start==Start && bytes==Bytes && dsb==Start+Bytes;
}
inline bool ram(uint64_t base) {
    return (base>>47)==0x1ffff && !(base&4095) && base<=UINT64_MAX-Bytes;
}
inline bool pte(uint64_t entry,uint32_t physicalPage) {
    const uint64_t physical=uint64_t(physicalPage)<<12;
    return physicalPage && !(physical&~PhysMask) && (entry&7)==7 && (entry&PhysMask)==physical;
}
inline bool imageRange(uint32_t pipe,uint32_t first,uint32_t second,
                       uint32_t index,uint32_t width,uint64_t &offset,size_t &length) {
    if(pipe>2 || index>1 || (width!=64 && width!=128 && width!=256)) return false;
    const uint64_t expected=Start+pipe*PerPipe;
    if(first!=expected || second!=expected+PerImage) return false;
    offset=pipe*PerPipe+index*PerImage;
    length=size_t(width)*width*4;
    return offset<=Bytes-length;
}
}
