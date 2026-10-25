#include "../overlay/kern_hp_nvram.hpp"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <initializer_list>
int main() {
    using namespace HPNvram;
    uint8_t function[ContextOffset+sizeof(Context)]={};
    memcpy(function,Entry,sizeof(Entry));
    memcpy(function+ContextOffset,Context,sizeof(Context));
    assert(prepare(function,sizeof(function),true));
    assert(!prepare(function,sizeof(function),false));
    assert(!prepare(nullptr,sizeof(function),true));
    for(size_t size=0;size<sizeof(function);++size) assert(!prepare(function,size,true));
    for(size_t i=0;i<sizeof(function);++i) {
        if(i>=sizeof(Entry) && i<ContextOffset) continue;
        for(unsigned bit=0;bit<8;++bit) {
            function[i]^=1U<<bit;
            assert(!prepare(function,sizeof(function),true));
            function[i]^=1U<<bit;
        }
    }
    assert(function[PatchOffset-2]==0xff && function[PatchOffset-1]==0x90);
    uint32_t slot=0;memcpy(&slot,function+PatchOffset,4);assert(slot==0x9f8);
    function[PatchOffset]=0xe8;
    memcpy(&slot,function+PatchOffset,4);assert(slot==0x9e8);
    assert(!prepare(function,sizeof(function),true)); // cannot apply twice
    for(size_t i=0;i<sizeof(Context);++i)
        assert(function[ContextOffset+i] == (ContextOffset+i==PatchOffset ? 0xe8 : Context[i]));
    puts("PASS: one-byte operand correction selects writeNVRAMProperty; neighboring instructions unchanged; wrong kernel slots, truncations, fingerprint mutations and repeat application rejected.");
}
