#include "../overlay/kern_hp_linear.hpp"
#include "../overlay/kern_hp_linear_signatures.hpp"
#include "../overlay/kern_hp_sync_signatures.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <initializer_list>
template<size_t N> static void fingerprint(const uint8_t (&expected)[N]) {
    uint8_t copy[N];memcpy(copy,expected,N);auto at=reinterpret_cast<uint64_t>(copy);
    assert(HPSyncSignatures::match(at,at,N,expected));
    for(size_t i=0;i<N;++i) {
        assert(!HPSyncSignatures::match(at,at,i,expected));
        for(unsigned bit=0;bit<8;++bit) {
            copy[i]^=1U<<bit;assert(!HPSyncSignatures::match(at,at,N,expected));copy[i]^=1U<<bit;
        }
    }
}
int main() {
    using namespace HPLinear;
    assert(cpu(8U<<8,1U<<19));assert(!cpu(8U<<8,0));
    for(unsigned line=0;line<256;++line) if(line!=8) assert(!cpu(line<<8,1U<<19));
    assert(layout(Start,Start,Bytes,Start+Bytes));
    assert(!layout(Start,Start,Bytes-4096,Start+Bytes));
    assert(!layout(Start+4096,Start,Bytes,Start+Bytes));
    assert(ram(0xffffff8001000000ULL));
    for(auto invalid:{0ULL,0x100000ULL,0x800000000000ULL,0xffffff8001000001ULL,0xfffffffffffff000ULL}) assert(!ram(invalid));
    for(uint32_t pipe=0;pipe<3;++pipe) for(uint32_t index=0;index<2;++index)
        for(uint32_t width:{64U,128U,256U}) {
            uint64_t offset=0;size_t length=0;uint32_t a=Start+pipe*PerPipe,b=a+PerImage;
            assert(imageRange(pipe,a,b,index,width,offset,length));
            assert(offset==pipe*PerPipe+index*PerImage && length==width*width*4);
            assert(offset+length<=Bytes && !(offset%4096) && !(length%4096));
            // Every pixel remains at the identical linear offset in the same
            // page; choosing direct RAM has no X-tile address transformation.
            for(size_t pixel=0;pixel<length;pixel+=4) assert(offset+pixel<Bytes);
            for(uint32_t bit=1;bit;bit<<=1) {
                assert(!imageRange(pipe,a^bit,b,index,width,offset,length));
                assert(!imageRange(pipe,a,b^bit,index,width,offset,length));
            }
        }
    uint64_t offset=0;size_t length=0;
    assert(!imageRange(3,Start,Start+PerImage,0,64,offset,length));
    assert(!imageRange(0,Start,Start+PerImage,2,64,offset,length));
    for(uint32_t width:{0U,1U,63U,65U,127U,129U,255U,257U,0xffffffffU})
        assert(!imageRange(0,Start,Start+PerImage,0,width,offset,length));
    uint32_t random=0xa7a18bdf;
    for(unsigned i=0;i<200000;++i) {
        random=random*1664525U+1013904223U;
        uint32_t page=(random&0x7ffffffU)|1U;
        uint64_t entry=(uint64_t(page)<<12)|7;
        assert(pte(entry,page));assert(!pte(entry,page^1));
        assert(!pte(entry&~1ULL,page));assert(!pte(entry,0));
        assert(!pte(entry,page|0x8000000U));
    }
    fingerprint(HPLinearSignatures::Image);fingerprint(HPLinearSignatures::State);fingerprint(HPLinearSignatures::Getter);
    puts("PASS: all 18 pipe/buffer/size combinations bounded; wrong layouts/CPU capabilities rejected; 200000 physical-page mismatch cases; all native fingerprint mutations and truncations rejected.");
}
