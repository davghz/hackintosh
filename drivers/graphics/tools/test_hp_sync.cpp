#include "../overlay/kern_hp_sync.hpp"
#include "../overlay/kern_hp_sync_signatures.hpp"
#include <cassert>
#include <cstring>
#include <cstdio>

static void clear(uint64_t (&event)[8]) { for (auto &x : event) x = HPSync::EmptyChannel; }
static uint64_t entry(uint32_t ch, uint32_t stamp) { return (uint64_t(stamp) << 32) | ch; }
int main() {
    uint64_t e[8]; clear(e);
    HPSync::Dependencies d;
    e[0]=entry(2,10); e[1]=entry(3,20); e[2]=entry(2,9); e[3]=entry(7,100);
    assert(d.add(e,128,7)); assert(d.channels==2 && d.stamps[2]==10 && !d.present[7]);
    e[0]=entry(2,11);assert(d.add(e,128,7));assert(d.stamps[2]==11);
    e[7]=entry(128,1);auto saved=d;assert(!d.add(e,128,7));assert(!memcmp(&saved,&d,sizeof(d)));
    clear(e);e[0]=entry(1,0xFFFFFFFEU);assert(d.add(e,128,7));
    e[0]=entry(1,2);assert(d.add(e,128,7));assert(d.stamps[1]==2);
    e[0]=entry(1,0xFFFFFFFDU);assert(d.add(e,128,7));assert(d.stamps[1]==2);
    assert(!d.add(e,0,0));assert(!d.add(e,129,0));assert(!d.add(e,64,64));
    HPSync::Dependencies all;
    for(uint32_t i=0;i<128;i++){clear(e);e[0]=entry(i,i+3);assert(all.add(e,128,64));}
    assert(all.channels==127);
    uint32_t next=0,total=0;bool visited[128]={};
    while(all.packet(next,e))for(auto v:e){uint32_t ch=uint32_t(v);if(ch==HPSync::EmptyChannel)continue;
        assert(ch<128&&ch!=64&&!visited[ch]&&uint32_t(v>>32)==ch+3);visited[ch]=true;total++;}
    assert(total==127);assert(!all.packet(next,e));
    assert(!HPSync::range(0,64));assert(!HPSync::range(0x100000,64));
    assert(!HPSync::range(UINT64_MAX-2,64));assert(!HPSync::range(0xFFFFFF8000001000ULL,65537));
    assert(HPSync::range(0xFFFFFF8000001000ULL,64));
    uint8_t window[64]={};memcpy(window+16,HPSyncSignatures::ComputeCall,32);
    const uint64_t base=reinterpret_cast<uint64_t>(window),at=base+16;
    assert(HPSyncSignatures::match(at,base,64,HPSyncSignatures::ComputeCall));
    for(unsigned i=0;i<32;i++){window[16+i]^=1;assert(!HPSyncSignatures::match(at,base,64,HPSyncSignatures::ComputeCall));window[16+i]^=1;}
    assert(!HPSyncSignatures::match(0,base,64,HPSyncSignatures::ComputeCall));
    assert(!HPSyncSignatures::match(at,base,47,HPSyncSignatures::ComputeCall));
    assert(!HPSyncSignatures::match(base-1,base,64,HPSyncSignatures::ComputeCall));
    // Compare many randomized merges against an independent per-channel model.
    HPSync::Dependencies fuzz;uint32_t rng=0xA7A18BDF,expect[128]={};bool seen[128]={};
    for(unsigned iter=0;iter<100000;iter++){
        clear(e);for(unsigned j=0;j<8;j++){rng=rng*1664525U+1013904223U;uint32_t ch=rng%128,stamp=iter*8+j;
            e[j]=entry(ch,stamp);if(ch!=9){seen[ch]=true;expect[ch]=stamp;}}
        assert(fuzz.add(e,128,9));
        for(unsigned ch=0;ch<128;ch++)assert(fuzz.present[ch]==seen[ch]&&(!seen[ch]||fuzz.stamps[ch]==expect[ch]));
    }
    puts("PASS: dependency accumulation, self-exclusion, all 128 channels, stamp wrap, invalid inputs, exact signatures, 100000 randomized cases.");
}
