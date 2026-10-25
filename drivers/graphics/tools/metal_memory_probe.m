#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <objc/runtime.h>
#import <dispatch/dispatch.h>
#include <mach/mach.h>
#include <malloc/malloc.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>
#include <dlfcn.h>

// Reproducer only: no method replacement, driver writes or installation.
static uint64_t footprint(void) {
    task_vm_info_data_t info={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;
    return task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&info,&count)==KERN_SUCCESS ? info.phys_footprint : 0;
}
static void stats(unsigned completed) {
    vm_address_t *zones=NULL;unsigned count=0;
    uint64_t bytes=0,blocks=0;
    if(malloc_get_all_zones(mach_task_self(),NULL,&zones,&count)==KERN_SUCCESS)
        for(unsigned i=0;i<count;++i){malloc_statistics_t s={0};malloc_zone_statistics((malloc_zone_t *)zones[i],&s);bytes+=s.size_in_use;blocks+=s.blocks_in_use;}
    printf("MEMORY completed=%u footprint_bytes=%llu malloc_bytes=%llu malloc_blocks=%llu\n",completed,footprint(),bytes,blocks);fflush(stdout);
}
int main(int argc, const char **argv) {
    @autoreleasepool {
        id<MTLDevice> device=MTLCreateSystemDefaultDevice();
        id<MTLCommandQueue> queue=[device newCommandQueue];if(!device||!queue)return 2;
        void (*fixStats)(void)=dlsym(RTLD_DEFAULT,"hp_posh_fix_stats");
        if(argc==2) {
            void *library=dlopen(argv[1],RTLD_NOW|RTLD_LOCAL);
            int (*install)(void)=library?dlsym(library,"hp_install_posh_fix"):NULL;
            if(!install||!install()){fprintf(stderr,"Process-local fix could not qualify: %s\n",dlerror()?:"guard rejected");return 7;}
            fixStats=dlsym(library,"hp_posh_fix_stats");
        } else if(argc!=1)return 2;
        Class bufferClass=objc_getClass("MTLIGAccelCommandBuffer");
        Class queueClass=objc_getClass("MTLIGAccelCommandQueue");
        Ivar posh=class_getInstanceVariable(bufferClass,"_pPoshUsedAsTarget");
        Ivar only=class_getInstanceVariable(bufferClass,"m_isOnlyActiveCommandBuffer");
        Ivar owner=class_getInstanceVariable(bufferClass,"_pIGCommandQueue");
        Ivar shared=class_getInstanceVariable(queueClass,"m_pPoshUsedAsTarget");
        if(!posh||!only||!owner||!shared){fprintf(stderr,"Expected driver ivars unavailable.\n");return 3;}
        printf("LAYOUT buffer_size=%zu queue_size=%zu posh=%td only=%td owner=%td shared=%td\n",class_getInstanceSize(bufferClass),class_getInstanceSize(queueClass),ivar_getOffset(posh),ivar_getOffset(only),ivar_getOffset(owner),ivar_getOffset(shared));
        unsigned onlyPrivate=0,other=0;
        const BOOL overlap=getenv("HP_MEMORY_OVERLAP")!=NULL;
        const BOOL uncommitted=getenv("HP_MEMORY_UNCOMMITTED")!=NULL;
        printf("MODE overlap=%d uncommitted=%d\n",overlap,uncommitted);
        stats(0);
        for(unsigned i=0;i<600;++i){ @autoreleasepool {
            id<MTLCommandBuffer> blocker=overlap?[queue commandBuffer]:nil;
            id<MTLCommandBuffer> cmd=[queue commandBuffer];if(!cmd)return 3;
            if(object_getClass(cmd)!=bufferClass){fprintf(stderr,"Unexpected command class %s; run without Metal debug layer.\n",object_getClassName(cmd));return 3;}
            const uint8_t *base=(__bridge const void *)cmd;
            void *allocation=*(void *const *)(base+ivar_getOffset(posh));
            const uint8_t *q=*(const uint8_t *const *)(base+ivar_getOffset(owner));
            void *sharedAllocation=q?*(void *const *)(q+ivar_getOffset(shared)):NULL;
            BOOL isOnly=*(const uint8_t *)(base+ivar_getOffset(only))!=0;
            if(isOnly && allocation && allocation!=sharedAllocation)++onlyPrivate;else ++other;
            if(i==0)printf("FIRST only=%d private_posh=%d shared_null=%d malloc_size=%zu\n",isOnly,allocation&&allocation!=sharedAllocation,sharedAllocation==NULL,allocation?malloc_size(allocation):0);
            if(blocker && !uncommitted) {
                dispatch_semaphore_t prior=dispatch_semaphore_create(0);
                [blocker addCompletedHandler:^(id<MTLCommandBuffer> c){(void)c;dispatch_semaphore_signal(prior);}];
                [blocker commit];
                if(dispatch_semaphore_wait(prior,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC)))_exit(4);
                if(blocker.status!=MTLCommandBufferStatusCompleted)return 5;
            }
            if(!uncommitted) {
            dispatch_semaphore_t done=dispatch_semaphore_create(0);
            [cmd addCompletedHandler:^(id<MTLCommandBuffer> c){(void)c;dispatch_semaphore_signal(done);}];
            [cmd commit];
            if(dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC))){fprintf(stderr,"Command timeout.\n");_exit(4);}
            if(cmd.status!=MTLCommandBufferStatusCompleted){fprintf(stderr,"Command failed.\n");return 5;}
            }
        }
            if((i+1)%100==0)stats(i+1);
        }
        printf("RESULT private_only_active=%u other=%u\n",onlyPrivate,other);
        // Idle briefly to distinguish delayed cleanup from retained allocations.
        usleep(500000);stats(600);
        if(fixStats)fixStats();
        return 0;
    }
}
