#include "../overlay/kern_hp_fence.hpp"
#include "../overlay/kern_hp_fence_signatures.hpp"
#include "../overlay/kern_hp_sync_signatures.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <initializer_list>

// Independent CPU-aperture X-tile address model, using the captured hardware
// fence register encoding. This checks actual row placement, not just policy.
static uint64_t physical(uint64_t address, uint32_t low, uint32_t high) {
    uint64_t start = low & 0xfffff000U;
    uint64_t end = uint64_t(high & 0xfffff000U) + 4096;
    if (!(low & 1) || address < start || address >= end) return address;
    assert(!(low & 2));
    uint64_t pitch = ((high & 0x7ffU) + 1) * 128;
    uint64_t x = (address-start) % pitch, y = (address-start) / pitch;
    return start + (y/8)*(pitch*8) + (x/512)*4096 + (y%8)*512 + x%512;
}
template<size_t N> static void signature(const uint8_t (&bytes)[N]) {
    uint8_t actual[N]; memcpy(actual,bytes,N);
    auto at = reinterpret_cast<uint64_t>(actual);
    assert(HPSyncSignatures::match(at,at,N,bytes));
    assert(!HPSyncSignatures::match(0,at,N,bytes));
    assert(!HPSyncSignatures::match(at,at+1,N,bytes));
    for (size_t length=0;length<N;++length)
        assert(!HPSyncSignatures::match(at,at,length,bytes));
    for (size_t i=0;i<N;++i) for(unsigned bit=0;bit<8;++bit) {
        actual[i] ^= 1U<<bit;
        assert(!HPSyncSignatures::match(at,at,N,bytes));
        actual[i] ^= 1U<<bit;
    }
}
int main() {
    using namespace HPFence;
    Layout layout{uint32_t(Reserved),Reserved,0x180000,Reserved+0x180000};
    Range old{0,OldSize};
    auto updated = adjusted(true,layout,0,old,Pitch,2);
    assert(updated.start==0 && updated.size==Reserved);
    const uint32_t oldHigh=0x03fff03b, newHigh=0x03bff03b;
    assert(newHigh==(((updated.size-1)&0xfffff000)|((Pitch/128)-1)));
    assert(Reserved%(Pitch*8)==0); // end on a complete X-tile row
    for (uint64_t a=0;a<Reserved;a+=4093)
        assert(physical(a,1,oldHigh)==physical(a,1,newHigh));
    // Before: row pairs of the 64x64 linear cursor become four separated strips.
    for (unsigned row=0;row<8;++row)
        assert((physical(Reserved+row*256,1,oldHigh)-Reserved)/256 == (row/2)*16+row%2);
    // After: every pixel of all reserved 256x256 cursor buffers remains linear,
    // as do the DSB/control buffers immediately following the cursor reservation.
    for (uint64_t a=Reserved;a<layout.dsbStart+0x12000;a+=4)
        assert(physical(a,1,newHigh)==a);
    auto same=[&](bool hp,const Layout &l,uint64_t index,const Range &r,uint64_t pitch,uint32_t tile) {
        auto out=adjusted(hp,l,index,r,pitch,tile);
        assert(out.start==r.start && out.size==r.size);
    };
    same(false,layout,0,old,Pitch,2);
    for (auto bytes : {0U,0x7ffffU,0x80001U,0x200000U,0xffffffffU}) {
        auto l=layout;l.cursorBytes=bytes;l.dsbStart=Reserved+bytes;same(true,l,0,old,Pitch,2);
    }
    for (uint32_t bytes : {0x80000U,0x100000U,0x180000U}) {
        auto l=layout;l.cursorBytes=bytes;l.dsbStart=Reserved+bytes;
        assert(adjusted(true,l,0,old,Pitch,2).size==Reserved);
    }
    for (auto field : {0U,1U,2U}) for(unsigned bit=0;bit<64;++bit) {
        auto l=layout;
        if(field==0) l.cursorStart^=1ULL<<bit;
        if(field==1) l.dsbStart^=1ULL<<bit;
        if(field==2 && bit<32) l.reserved^=1U<<bit;
        else if(field==2) continue;
        same(true,l,0,old,Pitch,2);
    }
    uint64_t random=0x8bdfa7a100000001ULL;
    for(unsigned i=0;i<200000;++i) {
        random=random*6364136223846793005ULL+1442695040888963407ULL;
        same(true,layout,1+(random%65535),old,Pitch,2);
        same(true,layout,0,Range{random|1,OldSize},Pitch,2);
        if(random!=OldSize) same(true,layout,0,Range{0,random},Pitch,2);
        if(random!=Pitch) same(true,layout,0,old,random,2);
        if(uint32_t(random)!=2) same(true,layout,0,old,Pitch,uint32_t(random));
    }
    signature(HPFenceSignatures::Init);
    signature(HPFenceSignatures::MemoryEntry);
    signature(HPFenceSignatures::CursorLayout);
    signature(HPFenceSignatures::DsbLayout);
    puts("PASS: original four-strip geometry reproduced; framebuffer addresses preserved; cursor/DSB addresses linear; all signature-bit mutations and 200000 unexpected-request cases rejected.");
}
