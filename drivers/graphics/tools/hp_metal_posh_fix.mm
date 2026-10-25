// Experimental cleanup correction with exact HP/build/image/code/layout guards.
// Default build requires explicit installation in a test process.
// HP_POSH_AUTOINSTALL enables a constructor for the isolated deployment candidate.
#import <Foundation/Foundation.h>
#import <IOKit/IOKitLib.h>
#import <objc/runtime.h>
#include <mach-o/loader.h>
#include <dlfcn.h>
#include <malloc/malloc.h>
#include <new>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/sysctl.h>
#include <syslog.h>
#include <unistd.h>
#include "hp_metal_posh_signatures.hpp"

static IMP originalDealloc;
static Class bufferClass, queueClass;
static ptrdiff_t poshOffset, onlyOffset, queueOffset, sharedOffset;
static uint64_t freedBlocks, sharedSkipped, ordinarySkipped, refused;
static pthread_mutex_t installLock=PTHREAD_MUTEX_INITIALIZER;

static void fixedDealloc(id object, SEL selector) {
    void *privateAllocation=nullptr;
    const uint8_t *base=(const uint8_t *)object;
    // Native destructor frees non-only-active allocations itself. Leave those alone.
    if (*(const uint8_t *)(base+onlyOffset)) {
        void *allocation=*(void *const *)(base+poshOffset);
        id queue=*(id const *)(base+queueOffset);
        if (allocation && queue && object_getClass(queue)==queueClass) {
            void *shared=*(void *const *)((const uint8_t *)queue+sharedOffset);
            if (allocation==shared) __atomic_add_fetch(&sharedSkipped,1,__ATOMIC_RELAXED);
            else {
                // Qualified initializer uses operator new(0x12010). Rounded zone
                // size differs by process; observed sizes include 76 and 96 KiB.
                const size_t bytes=malloc_size(allocation);
                if (bytes>=0x12010 && bytes<=0x18000) privateAllocation=allocation;
                else __atomic_add_fetch(&refused,1,__ATOMIC_RELAXED);
            }
        } else if (allocation) __atomic_add_fetch(&refused,1,__ATOMIC_RELAXED);
    } else __atomic_add_fetch(&ordinarySkipped,1,__ATOMIC_RELAXED);
    // Let native teardown finish first: its encoder/context cleanup may still
    // refer to POSH. Do not touch the released object or queue afterward.
    ((void(*)(id,SEL))originalDealloc)(object,selector);
    if (privateAllocation) {
        ::operator delete(privateAllocation);
        uint64_t count=__atomic_add_fetch(&freedBlocks,1,__ATOMIC_RELAXED);
#ifdef HP_POSH_AUTOINSTALL
        if((count & 4095U)==0)syslog(LOG_NOTICE,"HP-POSH 0.1 freed=%llu private command allocations",count);
#else
        (void)count;
#endif
    }
}

static bool numberMatches(io_registry_entry_t root, CFStringRef key, int64_t expected) {
    CFTypeRef value=IORegistryEntryCreateCFProperty(root,key,kCFAllocatorDefault,0);
    int64_t number=0;
    bool valid=value && CFGetTypeID(value)==CFNumberGetTypeID() &&
        CFNumberGetValue((CFNumberRef)value,kCFNumberSInt64Type,&number) && number==expected;
    if(value)CFRelease(value);return valid;
}
static bool targetMatches(void) {
    char build[32]={0};size_t length=sizeof(build);
    if(sysctlbyname("kern.osversion",build,&length,nullptr,0) || strcmp(build,"25G241"))return false;
    io_registry_entry_t root=IORegistryGetRootEntry(kIOMainPortDefault);
    if(!root)return false;
    CFTypeRef stage=IORegistryEntryCreateCFProperty(root,CFSTR("hp-graphics-probe-stage"),kCFAllocatorDefault,0);
    bool valid=stage && CFGetTypeID(stage)==CFStringGetTypeID() && CFEqual(stage,CFSTR("graphics-patches-enabled")) &&
        numberMatches(root,CFSTR("hp-graphics-pci-vendor"),0x8086) &&
        numberMatches(root,CFSTR("hp-graphics-pci-device"),0xa7a1) &&
        numberMatches(root,CFSTR("hp-graphics-pci-revision"),4) &&
        numberMatches(root,CFSTR("hp-graphics-pci-subvendor"),0x103c) &&
        numberMatches(root,CFSTR("hp-graphics-pci-subdevice"),0x8bdf) &&
        numberMatches(root,CFSTR("hp-graphics-reserved-bytes"),60*1024*1024);
    if(stage)CFRelease(stage);IOObjectRelease(root);return valid;
}
static bool uuidMatches(const void *base) {
    static const uint8_t expected[16]={0x2b,0x84,0x9e,0x57,0xac,0x6a,0x32,0x16,0xa6,0x7b,0x38,0xe0,0x80,0x60,0x35,0x85};
    const mach_header_64 *header=(const mach_header_64 *)base;
    if(header->magic!=MH_MAGIC_64 || header->ncmds>128 || header->sizeofcmds>65536)return false;
    const uint8_t *cursor=(const uint8_t *)(header+1),*end=cursor+header->sizeofcmds;
    for(unsigned i=0;i<header->ncmds;++i){
        if(cursor+sizeof(load_command)>end)return false;
        const load_command *cmd=(const load_command *)cursor;
        if(cmd->cmdsize<sizeof(*cmd)||cursor+cmd->cmdsize>end)return false;
        if(cmd->cmd==LC_UUID)return cmd->cmdsize==sizeof(uuid_command) &&
            !memcmp(((const uuid_command *)cmd)->uuid,expected,sizeof(expected));
        cursor+=cmd->cmdsize;
    }
    return false;
}
extern "C" int hp_install_posh_fix(void) {
    pthread_mutex_lock(&installLock);
    if(originalDealloc){pthread_mutex_unlock(&installLock);return 1;}
    int result=0,stage=1;
    do {
        if(!targetMatches())break;
        stage=2;
        bufferClass=objc_getClass("MTLIGAccelCommandBuffer");queueClass=objc_getClass("MTLIGAccelCommandQueue");
        if(!bufferClass||!queueClass||class_getInstanceSize(bufferClass)!=920||class_getInstanceSize(queueClass)!=864)break;
        stage=3;
        Ivar posh=class_getInstanceVariable(bufferClass,"_pPoshUsedAsTarget");
        Ivar only=class_getInstanceVariable(bufferClass,"m_isOnlyActiveCommandBuffer");
        Ivar queue=class_getInstanceVariable(bufferClass,"_pIGCommandQueue");
        Ivar shared=class_getInstanceVariable(queueClass,"m_pPoshUsedAsTarget");
        if(!posh||!only||!queue||!shared)break;
        stage=4;
        poshOffset=ivar_getOffset(posh);onlyOffset=ivar_getOffset(only);queueOffset=ivar_getOffset(queue);sharedOffset=ivar_getOffset(shared);
        if(poshOffset!=816||onlyOffset!=880||queueOffset!=768||sharedOffset!=848)break;
        stage=5;
        Method dealloc=class_getInstanceMethod(bufferClass,sel_registerName("dealloc"));
        Method init=class_getInstanceMethod(bufferClass,sel_registerName("initWithQueue:retainedReferences:synchronousDebugMode:"));
        if(!dealloc||!init||method_getNumberOfArguments(dealloc)!=2)break;
        stage=6;
        IMP impl=method_getImplementation(dealloc);Dl_info image={};
        if(!dladdr((const void *)impl,&image)||!image.dli_fbase||!uuidMatches(image.dli_fbase))break;
        stage=7;
        const uint8_t *base=(const uint8_t *)image.dli_fbase;
        if((const uint8_t *)impl!=base+0x7ecba || (const uint8_t *)method_getImplementation(init)!=base+0x7e862)break;
        stage=8;
        using namespace HPPoshSignatures;
        if(memcmp(base+0x7ecba,DeallocStart,sizeof(DeallocStart)) || memcmp(base+0x7ed6b,DeallocOwnership,sizeof(DeallocOwnership)) ||
           memcmp(base+0x7e862,InitStart,sizeof(InitStart)) || memcmp(base+0x7e9b0,InitOwnership,sizeof(InitOwnership)))break;
        originalDealloc=impl;
        method_setImplementation(dealloc,(IMP)fixedDealloc);
        result=1;
    } while(false);
    pthread_mutex_unlock(&installLock);
    fprintf(stderr,"HP-POSH: %s stage=%d (explicit process-local experiment)\n",result?"qualified and installed":"qualification rejected; no changes",stage);
#ifdef HP_POSH_AUTOINSTALL
    syslog(LOG_NOTICE,"HP-POSH 0.1 %s stage=%d",result?"qualified cleanup installed":"qualification rejected; no changes",stage);
#endif
    return result;
}
extern "C" void hp_posh_fix_stats(void) {
    fprintf(stderr,"HP-POSH counters freed=%llu shared_skipped=%llu ordinary_native_cleanup=%llu refused=%llu\n",
        __atomic_load_n(&freedBlocks,__ATOMIC_RELAXED),__atomic_load_n(&sharedSkipped,__ATOMIC_RELAXED),
        __atomic_load_n(&ordinarySkipped,__ATOMIC_RELAXED),__atomic_load_n(&refused,__ATOMIC_RELAXED));
}

#ifdef HP_POSH_AUTOINSTALL
static void *lateInstall(void *) {
    for(unsigned i=0;i<2000;++i) {
        if(objc_getClass("MTLIGAccelCommandBuffer") && objc_getClass("MTLIGAccelCommandQueue")) {
            hp_install_posh_fix();return nullptr;
        }
        usleep(1000);
    }
    syslog(LOG_NOTICE,"HP-POSH 0.1 driver classes unavailable; no changes");
    return nullptr;
}
__attribute__((constructor)) static void automaticInstall(void) {
    if(objc_getClass("MTLIGAccelCommandBuffer") && objc_getClass("MTLIGAccelCommandQueue"))hp_install_posh_fix();
    else {
        pthread_t thread;
        if(!pthread_create(&thread,nullptr,lateInstall,nullptr))pthread_detach(thread);
    }
}
#endif
