#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <dispatch/dispatch.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(int argc, const char **argv) { @autoreleasepool {
    if (argc != 2 || (strcmp(argv[1],"buffer") && strcmp(argv[1],"upload") && strcmp(argv[1],"texture-copy") && strcmp(argv[1],"clear"))) return 1;
    const char *mode=argv[1];
    id<MTLDevice> d=MTLCreateSystemDefaultDevice(); if(!d)return 2;
    id<MTLCommandQueue> q=[d newCommandQueue];
    id<MTLBuffer> in=[d newBufferWithLength:16384 options:MTLResourceStorageModeShared];
    id<MTLBuffer> out=[d newBufferWithLength:16384 options:MTLResourceStorageModeShared];
    if(!q||!in||!out||!in.contents||!out.contents)return 3;
    uint32_t *input=in.contents,*output=out.contents;
    for(unsigned i=0;i<4096;i++) { input[i]=0xFF000000U|((i&1)?255U:0U)|((i&2)?0xFF00U:0U)|((i&4)?0xFF0000U:0U); output[i]=0x55555555; }
    id<MTLCommandBuffer> cmd=[q commandBuffer]; if(!cmd)return 3;
    id<MTLTexture> texture=nil;
    if(!strcmp(mode,"buffer")) {
        id<MTLBlitCommandEncoder> b=[cmd blitCommandEncoder];if(!b)return 3;
        [b copyFromBuffer:in sourceOffset:0 toBuffer:out destinationOffset:0 size:16384];[b endEncoding];
    } else {
        MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:64 height:64 mipmapped:NO];
        BOOL clear=!strcmp(mode,"clear");
        td.storageMode=clear?MTLStorageModePrivate:MTLStorageModeManaged;
        td.usage=clear?MTLTextureUsageRenderTarget:MTLTextureUsageShaderRead;
        texture=[d newTextureWithDescriptor:td]; if(!texture)return 3;
        if(clear) {
            MTLRenderPassDescriptor *p=[MTLRenderPassDescriptor renderPassDescriptor];
            p.colorAttachments[0].texture=texture;p.colorAttachments[0].loadAction=MTLLoadActionClear;
            p.colorAttachments[0].storeAction=MTLStoreActionStore;p.colorAttachments[0].clearColor=MTLClearColorMake(1,0,0,1);
            id<MTLRenderCommandEncoder> r=[cmd renderCommandEncoderWithDescriptor:p];if(!r)return 3;[r endEncoding];
        } else [texture replaceRegion:MTLRegionMake2D(0,0,64,64) mipmapLevel:0 withBytes:input bytesPerRow:256];
        if(!strcmp(mode,"upload")) {
            NSError *error=nil;
            NSString *source=@"#include <metal_stdlib>\nusing namespace metal;\n"
                "kernel void check(texture2d<float,access::read> t [[texture(0)]],device uint *o [[buffer(0)]],uint2 p [[thread_position_in_grid]]){"
                "uint4 c=uint4(round(t.read(p)*255.0f));o[p.y*64+p.x]=c.r|(c.g<<8)|(c.b<<16)|(c.a<<24);}";
            id<MTLLibrary> lib=[d newLibraryWithSource:source options:nil error:&error];
            if(!lib){fprintf(stderr,"Shader: %s\n",error.description.UTF8String);return 3;}
            id<MTLComputePipelineState> pipe=[d newComputePipelineStateWithFunction:[lib newFunctionWithName:@"check"] error:&error];
            if(!pipe){fprintf(stderr,"Pipeline: %s\n",error.description.UTF8String);return 3;}
            id<MTLComputeCommandEncoder> c=[cmd computeCommandEncoder];if(!c)return 3;
            [c setComputePipelineState:pipe];[c setTexture:texture atIndex:0];[c setBuffer:out offset:0 atIndex:0];
            [c dispatchThreadgroups:MTLSizeMake(8,8,1) threadsPerThreadgroup:MTLSizeMake(8,8,1)];[c endEncoding];
        } else {
            id<MTLBlitCommandEncoder> b=[cmd blitCommandEncoder];if(!b)return 3;
            [b copyFromTexture:texture sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0) sourceSize:MTLSizeMake(64,64,1)
                toBuffer:out destinationOffset:0 destinationBytesPerRow:256 destinationBytesPerImage:16384];[b endEncoding];
        }
    }
    dispatch_semaphore_t done=dispatch_semaphore_create(0);
    [cmd addCompletedHandler:^(id<MTLCommandBuffer> c){(void)c;dispatch_semaphore_signal(done);}];
    printf("Submitting isolated %s test (5-second completion limit).\n",mode);fflush(stdout);[cmd commit];
    if(dispatch_semaphore_wait(done,dispatch_time(DISPATCH_TIME_NOW,5*NSEC_PER_SEC))){fprintf(stderr,"FAIL: timeout\n");fflush(stderr);_exit(4);}
    if(cmd.status!=MTLCommandBufferStatusCompleted){fprintf(stderr,"FAIL: command %lu %s\n",(unsigned long)cmd.status,cmd.error.description.UTF8String ?: "unknown");return 5;}
    unsigned bad=0;
    for(unsigned i=0;i<4096;i++) { uint32_t want=!strcmp(mode,"clear")?0xFF0000FFU:input[i];
        if(output[i]!=want){if(bad<4)fprintf(stderr,"Mismatch %u: %08x expected %08x\n",i,output[i],want);bad++;}}
    if(bad){fprintf(stderr,"FAIL: %s %u/4096 values wrong.\n",mode,bad);return 6;}
    printf("PASS: %s all 4096 values correct.\n",mode);return 0;
}}
