#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <dispatch/dispatch.h>
#include <mach/mach.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <dlfcn.h>

// Manual, bounded offscreen check: three slots, max 15 frames/sec, max 5 minutes.
// Compare every pixel. Never change display settings, load drivers or sleep the OS.
@interface HPFrame : NSObject
@property(nonatomic,strong) id<MTLTexture> texture;
@property(nonatomic,strong) id<MTLBuffer> output;
@property(nonatomic,strong) id<MTLCommandBuffer> command;
@property(nonatomic,strong) dispatch_semaphore_t completion;
@property(nonatomic) unsigned width, height, phase, submissions;
@property(nonatomic) BOOL bgra, blit;
@end
@implementation HPFrame
@end

static double seconds(void) {
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}
static uint64_t footprint(void) {
    task_vm_info_data_t info = {0}; mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&info, &count) != KERN_SUCCESS) return 0;
    return info.phys_footprint;
}
static uint32_t expected(unsigned x, unsigned y, unsigned phase, BOOL bgra) {
    uint32_t red=(x+phase*13U)&255U, green=(y*3U+phase*7U)&255U;
    uint32_t blue=((x^y)+phase*11U)&255U;
    return (bgra ? blue|(green<<8)|(red<<16) : red|(green<<8)|(blue<<16)) | 0xFF000000U;
}
static int finish(HPFrame *frame, uint64_t *checkedPixels, uint64_t *checkedFrames) {
    if (!frame.command) return 0;
    if (dispatch_semaphore_wait(frame.completion, dispatch_time(DISPATCH_TIME_NOW, 5*NSEC_PER_SEC))) {
        fprintf(stderr,"FAIL: frame %u exceeded 5-second completion wait.\n",frame.phase); return 4;
    }
    if (frame.command.status != MTLCommandBufferStatusCompleted) {
        fprintf(stderr,"FAIL: frame %u command status %lu: %s\n",frame.phase,
                (unsigned long)frame.command.status,frame.command.error.description.UTF8String ?: "unknown"); return 5;
    }
    const uint32_t *data=frame.output.contents;
    for (unsigned y=0;y<frame.height;++y) for (unsigned x=0;x<frame.width;++x) {
        uint32_t want=expected(x,y,frame.phase,frame.bgra && frame.blit);
        uint32_t got=data[(size_t)y*frame.width+x];
        if (want!=got) {
            fprintf(stderr,"FAIL: frame %u %ux%u %s %s pixel (%u,%u)=%08x expected %08x\n",
                    frame.phase,frame.width,frame.height,frame.bgra?"BGRA":"RGBA",frame.blit?"blit":"compute",x,y,got,want);
            return 6;
        }
    }
    *checkedPixels+=(uint64_t)frame.width*frame.height; ++*checkedFrames;
    frame.command=nil;
    return 0;
}
static BOOL allocate(id<MTLDevice> device, HPFrame *frame) {
    MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:
        frame.bgra?MTLPixelFormatBGRA8Unorm:MTLPixelFormatRGBA8Unorm width:frame.width height:frame.height mipmapped:NO];
    td.storageMode=MTLStorageModePrivate;
    td.usage=MTLTextureUsageRenderTarget|MTLTextureUsageShaderRead;
    td.hazardTrackingMode=MTLHazardTrackingModeTracked;
    frame.texture=[device newTextureWithDescriptor:td];
    frame.output=[device newBufferWithLength:(NSUInteger)frame.width*frame.height*4 options:MTLResourceStorageModeShared];
    return frame.texture && frame.output && frame.output.contents;
}
int main(int argc,const char **argv) {
    unsigned duration=300;
    if (argc==2) {
        char *end=NULL; unsigned long n=strtoul(argv[1],&end,10);
        if (!end || *end || n<1 || n>300) return 2;
        duration=(unsigned)n;
    } else if (argc!=1) return 2;
    @autoreleasepool {
        id<MTLDevice> device=MTLCreateSystemDefaultDevice();
        if (!device) return 2;
        void (*fixStats)(void)=NULL;
        const char *fixPath=getenv("HP_METAL_POSH_TEST_LIBRARY");
        if(fixPath) {
            void *library=dlopen(fixPath,RTLD_NOW|RTLD_LOCAL);
            int (*install)(void)=library?dlsym(library,"hp_install_posh_fix"):NULL;
            if(!install||!install()){fprintf(stderr,"Process-local fix could not qualify: %s\n",dlerror()?:"guard rejected");return 7;}
            fixStats=dlsym(library,"hp_posh_fix_stats");
        }
        NSString *source=@"#include <metal_stdlib>\nusing namespace metal;\n"
            "vertex float4 tri(uint v [[vertex_id]]) {float2 p[3]={float2(-1,-1),float2(3,-1),float2(-1,3)};return float4(p[v],0,1);}\n"
            "fragment float4 pattern(float4 p [[position]],constant uint &phase [[buffer(0)]]) {"
            "uint x=uint(p.x),y=uint(p.y);return float4(float((x+phase*13u)&255u),float((y*3u+phase*7u)&255u),float(((x^y)+phase*11u)&255u),255.0)/255.0;}\n"
            "kernel void readback(texture2d<float,access::read> tex [[texture(0)]],device uint *out [[buffer(0)]],uint2 p [[thread_position_in_grid]]) {"
            "if(p.x>=tex.get_width()||p.y>=tex.get_height())return;uint4 c=uint4(round(tex.read(p)*255.0));"
            "out[p.y*tex.get_width()+p.x]=c.r|(c.g<<8)|(c.b<<16)|(c.a<<24);}\n";
        NSError *error=nil;
        id<MTLLibrary> lib=[device newLibraryWithSource:source options:nil error:&error];
        if (!lib) {fprintf(stderr,"Shader build failed: %s\n",error.description.UTF8String);return 3;}
        id<MTLComputePipelineState> compute=[device newComputePipelineStateWithFunction:[lib newFunctionWithName:@"readback"] error:&error];
        NSMutableArray<id<MTLRenderPipelineState>> *pipelines=[NSMutableArray array];
        for (unsigned i=0;i<2;++i) {
            MTLRenderPipelineDescriptor *pd=[MTLRenderPipelineDescriptor new];
            pd.vertexFunction=[lib newFunctionWithName:@"tri"];
            pd.fragmentFunction=[lib newFunctionWithName:@"pattern"];
            pd.colorAttachments[0].pixelFormat=i?MTLPixelFormatBGRA8Unorm:MTLPixelFormatRGBA8Unorm;
            id<MTLRenderPipelineState> pipeline=[device newRenderPipelineStateWithDescriptor:pd error:&error];
            if (!pipeline) {fprintf(stderr,"Render pipeline failed: %s\n",error.description.UTF8String);return 3;}
            [pipelines addObject:pipeline];
        }
        id<MTLCommandQueue> queue=[device newCommandQueue];
        if (!compute || !queue) return 3;
        unsigned widths[3]={640,1279,1920}, heights[3]={360,719,1080};
        NSMutableArray<HPFrame *> *slots=[NSMutableArray array];
        for (unsigned i=0;i<3;++i) {
            HPFrame *frame=[HPFrame new];frame.width=widths[i];frame.height=heights[i];frame.bgra=i==1;
            frame.completion=dispatch_semaphore_create(0);
            if (!allocate(device,frame)) return 3;
            [slots addObject:frame];
        }
        printf("BEGIN: %u seconds, max 15 fps, 3 slots; RGBA/BGRA; 640x360,1279x719,1920x1080; alternate render-compute/render-blit; recycle resources every 60 uses. Device=%s\n",duration,device.name.UTF8String);
        fflush(stdout);
        double start=seconds(), reportAt=start+15;
        uint64_t checkedPixels=0,checkedFrames=0,initialBytes=footprint(),peakBytes=initialBytes;
        unsigned submitted=0,reallocations=0;
        while (seconds()-start<duration) { @autoreleasepool {
            HPFrame *frame=slots[submitted%3];
            int status=finish(frame,&checkedPixels,&checkedFrames);if(status)return status;
            if (frame.submissions && frame.submissions%60==0) {
                frame.texture=nil;frame.output=nil;
                if (!allocate(device,frame)) return 3;
                ++reallocations;
            }
            frame.phase=submitted;frame.blit=(submitted/3)%2==1;
            memset(frame.output.contents,0x55,frame.output.length);
            MTLRenderPassDescriptor *pass=[MTLRenderPassDescriptor renderPassDescriptor];
            pass.colorAttachments[0].texture=frame.texture;pass.colorAttachments[0].loadAction=MTLLoadActionClear;
            pass.colorAttachments[0].storeAction=MTLStoreActionStore;
            pass.colorAttachments[0].clearColor=MTLClearColorMake(1,0,1,0);
            id<MTLCommandBuffer> cmd=[queue commandBuffer];
            id<MTLRenderCommandEncoder> render=[cmd renderCommandEncoderWithDescriptor:pass];
            if (!cmd||!render) return 3;
            [render setRenderPipelineState:pipelines[frame.bgra?1:0]];
            unsigned phase=frame.phase;[render setFragmentBytes:&phase length:sizeof(phase) atIndex:0];
            [render drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];[render endEncoding];
            if (frame.blit) {
                id<MTLBlitCommandEncoder> blit=[cmd blitCommandEncoder];if(!blit)return 3;
                [blit copyFromTexture:frame.texture sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0)
                    sourceSize:MTLSizeMake(frame.width,frame.height,1) toBuffer:frame.output destinationOffset:0
                    destinationBytesPerRow:frame.width*4 destinationBytesPerImage:frame.width*frame.height*4];
                [blit endEncoding];
            } else {
                id<MTLComputeCommandEncoder> encoder=[cmd computeCommandEncoder];if(!encoder)return 3;
                [encoder setComputePipelineState:compute];[encoder setTexture:frame.texture atIndex:0];
                [encoder setBuffer:frame.output offset:0 atIndex:0];
                [encoder dispatchThreadgroups:MTLSizeMake((frame.width+7)/8,(frame.height+7)/8,1) threadsPerThreadgroup:MTLSizeMake(8,8,1)];
                [encoder endEncoding];
            }
            frame.command=cmd;dispatch_semaphore_t done=frame.completion;
            [cmd addCompletedHandler:^(id<MTLCommandBuffer> b){(void)b;dispatch_semaphore_signal(done);}];
            [cmd commit];++submitted;++frame.submissions;
            if (submitted%3==0) {
                double due=start+submitted/15.0;
                while(seconds()<due && seconds()-start<duration) usleep(1000);
            }
            double now=seconds();
            if(now>=reportAt) {
                uint64_t bytes=footprint();if(bytes>peakBytes)peakBytes=bytes;
                printf("PROGRESS: elapsed=%.1f checked_frames=%llu checked_pixels=%llu footprint_MiB=%.1f device_allocated_MiB=%.1f reallocations=%u\n",now-start,checkedFrames,checkedPixels,bytes/1048576.0,device.currentAllocatedSize/1048576.0,reallocations);fflush(stdout);
                if(initialBytes && bytes>initialBytes+512ULL*1024*1024) {fprintf(stderr,"STOP: process footprint grew by more than 512 MiB.\n");return 8;}
                reportAt=now+15;
            }
        }}
        for(HPFrame *frame in slots){int status=finish(frame,&checkedPixels,&checkedFrames);if(status)return status;}
        uint64_t finalBytes=footprint();if(finalBytes>peakBytes)peakBytes=finalBytes;
        printf("PASS: elapsed=%.1f submitted=%u checked_frames=%llu checked_pixels=%llu reallocations=%u footprint_initial_MiB=%.1f footprint_final_MiB=%.1f footprint_peak_MiB=%.1f\n",seconds()-start,submitted,checkedFrames,checkedPixels,reallocations,initialBytes/1048576.0,finalBytes/1048576.0,peakBytes/1048576.0);
        if(fixStats)fixStats();
        return 0;
    }
}
