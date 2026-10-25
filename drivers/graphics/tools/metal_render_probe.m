#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <dispatch/dispatch.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

// Bounded correctness check, not a stress benchmark. Run manually only.
static BOOL complete(id<MTLCommandBuffer> command, const char *label) {
    dispatch_semaphore_t done = dispatch_semaphore_create(0);
    [command addCompletedHandler:^(id<MTLCommandBuffer> b) { (void)b; dispatch_semaphore_signal(done); }];
    printf("Submitting %s (5-second completion limit).\n", label); fflush(stdout);
    [command commit];
    if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 5*NSEC_PER_SEC))) {
        fprintf(stderr, "FAIL: %s timed out.\n", label); fflush(stderr); _exit(4);
    }
    if (command.status != MTLCommandBufferStatusCompleted) {
        fprintf(stderr, "FAIL: %s status %lu: %s\n", label, (unsigned long)command.status,
                command.error.description.UTF8String ?: "unknown");
        return NO;
    }
    return YES;
}
static uint32_t expected(unsigned x, unsigned y, unsigned phase) {
    return (((x ^ phase)&1) ? 255U : 0U) |
        (((y ^ phase)&1) ? 255U << 8 : 0U) |
        ((((x>>3) ^ (y>>3) ^ phase)&1) ? 255U << 16 : 0U) | 0xFF000000U;
}
static BOOL pixels(const uint32_t *values, unsigned phase, const char *label) {
    unsigned count = 0;
    for (unsigned y = 0; y < 64; ++y) for (unsigned x = 0; x < 64; ++x) {
        uint32_t want = expected(x,y,phase), got = values[y*64+x];
        if (got != want) {
            if (count < 4) fprintf(stderr,"%s mismatch (%u,%u): %08x expected %08x\n",label,x,y,got,want);
            ++count;
        }
    }
    if (count) fprintf(stderr,"FAIL: %s %u/4096 mismatches.\n",label,count);
    return count == 0;
}
int main(int argc, const char **argv) {
    const BOOL useBlit = argc == 2 && !strcmp(argv[1], "--blit");
    const BOOL managed = argc == 2 && !strcmp(argv[1], "--managed");
    const BOOL unoptimized = argc == 2 && !strcmp(argv[1], "--unoptimized");
    const BOOL separate = argc == 2 && !strcmp(argv[1], "--separate");
    const BOOL tracked = argc == 2 && !strcmp(argv[1], "--tracked");
    const BOOL fenced = argc == 2 && !strcmp(argv[1], "--fence");
    @autoreleasepool {
        id<MTLDevice> device = MTLCreateSystemDefaultDevice();
        if (!device) return 2;
        printf("Testing %s: 64x64 rasterization, texture reads and copy/readback.\n", device.name.UTF8String);
        NSError *error = nil;
        NSString *source = @"#include <metal_stdlib>\nusing namespace metal;\n"
            "vertex float4 triangle(uint v [[vertex_id]]) {"
            " float2 p[3]={float2(-1,-1),float2(3,-1),float2(-1,3)}; return float4(p[v],0,1); }\n"
            "fragment float4 pattern(float4 p [[position]], constant uint &phase [[buffer(0)]]) {"
            " uint x=uint(p.x),y=uint(p.y); return float4(float((x^phase)&1u),float((y^phase)&1u),"
            " float(((x>>3)^(y>>3)^phase)&1u),1); }\n"
            "kernel void readback(texture2d<float,access::read> image [[texture(0)]],"
            " device uint *out [[buffer(0)]],uint2 p [[thread_position_in_grid]]) {"
            " if(p.x>=64||p.y>=64)return; uint4 c=uint4(round(image.read(p)*255.0f));"
            " out[p.y*64+p.x]=c.r|(c.g<<8)|(c.b<<16)|(c.a<<24); }\n";
        id<MTLLibrary> library = [device newLibraryWithSource:source options:nil error:&error];
        if (!library) {fprintf(stderr,"Shader: %s\n",error.description.UTF8String); return 3;}
        MTLRenderPipelineDescriptor *pd = [MTLRenderPipelineDescriptor new];
        pd.vertexFunction = [library newFunctionWithName:@"triangle"];
        pd.fragmentFunction = [library newFunctionWithName:@"pattern"];
        pd.colorAttachments[0].pixelFormat = MTLPixelFormatRGBA8Unorm;
        id<MTLRenderPipelineState> render = [device newRenderPipelineStateWithDescriptor:pd error:&error];
        id<MTLComputePipelineState> read = [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"readback"] error:&error];
        id<MTLCommandQueue> queue = [device newCommandQueue];
        if (!render || !read || !queue) {fprintf(stderr,"Pipeline: %s\n",error.description.UTF8String ?: "nil"); return 3;}
        MTLTextureDescriptor *td = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:64 height:64 mipmapped:NO];
        td.storageMode = managed ? MTLStorageModeManaged : MTLStorageModePrivate;
        if (unoptimized) td.allowGPUOptimizedContents = NO;
        if (tracked) td.hazardTrackingMode = MTLHazardTrackingModeTracked;
        printf("Target storage: %s; GPU optimized contents requested: %s.\n", managed ? "managed" : "private", unoptimized ? "NO" : "default");
        td.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
        id<MTLTexture> texture = [device newTextureWithDescriptor:td];
        printf("Actual texture hazard tracking mode: %lu (tracked=2).\n", (unsigned long)texture.hazardTrackingMode);
        id<MTLFence> fence = fenced ? [device newFence] : nil;
        if (fenced && !fence) return 3;
        id<MTLBuffer> output = [device newBufferWithLength:64*64*4 options:MTLResourceStorageModeShared];
        id<MTLBuffer> copied = [device newBufferWithLength:64*64*4 options:MTLResourceStorageModeShared];
        if (!texture || !output || !copied || !output.contents || !copied.contents) return 3;
        for (unsigned frame = 0; frame < 12; ++frame) { @autoreleasepool {
            memset(output.contents,0x55,output.length);
            MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
            pass.colorAttachments[0].texture = texture;
            pass.colorAttachments[0].loadAction = MTLLoadActionClear;
            pass.colorAttachments[0].storeAction = MTLStoreActionStore;
            pass.colorAttachments[0].clearColor = MTLClearColorMake(1,0,1,0);
            id<MTLCommandBuffer> cmd = [queue commandBuffer];
            id<MTLRenderCommandEncoder> re = [cmd renderCommandEncoderWithDescriptor:pass];
            if (!cmd || !re) return 3;
            [re setRenderPipelineState:render];
            [re setFragmentBytes:&frame length:sizeof(frame) atIndex:0];
            [re drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
            if (fenced) [re updateFence:fence afterStages:MTLRenderStageFragment];
            [re endEncoding];
            if (separate) {
                if (!complete(cmd,"render only before separate readback")) return 5;
                cmd = [queue commandBuffer];
                if (!cmd) return 3;
            }
            if (useBlit) {
                id<MTLBlitCommandEncoder> be = [cmd blitCommandEncoder];
                if (!be) return 3;
                [be copyFromTexture:texture sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0)
                    sourceSize:MTLSizeMake(64,64,1) toBuffer:output destinationOffset:0 destinationBytesPerRow:256 destinationBytesPerImage:16384];
                [be endEncoding];
            } else {
            id<MTLComputeCommandEncoder> ce = [cmd computeCommandEncoder];
            if (!ce) return 3;
            if (fenced) [ce waitForFence:fence];
            [ce setComputePipelineState:read]; [ce setTexture:texture atIndex:0];
            [ce setBuffer:output offset:0 atIndex:0];
            [ce dispatchThreadgroups:MTLSizeMake(8,8,1) threadsPerThreadgroup:MTLSizeMake(8,8,1)];
            [ce endEncoding];
            }
            if (!complete(cmd,useBlit ? "render + texture copy readback" : "render + shader texture readback")) return 5;
            if (!pixels(output.contents,frame,"render/texture")) return 6;
            printf("PASS: frame %u, all 4096 pixels.\n",frame); fflush(stdout);
        }}
        memset(copied.contents,0x55,copied.length);
        id<MTLCommandBuffer> cmd = [queue commandBuffer];
        id<MTLBlitCommandEncoder> blit = [cmd blitCommandEncoder];
        if (!cmd || !blit) return 3;
        [blit copyFromBuffer:output sourceOffset:0 toBuffer:copied destinationOffset:0 size:output.length];
        [blit endEncoding];
        if (!complete(cmd,"buffer copy")) return 5;
        if (!pixels(copied.contents,11,"buffer copy")) return 6;
        puts("PASS: buffer copy/readback.");
        memset(copied.contents,0x55,copied.length);
        cmd = [queue commandBuffer]; blit = [cmd blitCommandEncoder];
        if (!cmd || !blit) return 3;
        [blit copyFromTexture:texture sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0)
            sourceSize:MTLSizeMake(64,64,1) toBuffer:copied destinationOffset:0 destinationBytesPerRow:256 destinationBytesPerImage:16384];
        [blit endEncoding];
        if (!complete(cmd,"texture-to-buffer copy")) return 5;
        if (!pixels(copied.contents,11,"texture copy")) return 6;
        printf("PASS: 12 rendered frames (%s readback), buffer copy and texture copy matched CPU expectations.\n", useBlit ? "blit" : "shader");
        return 0;
    }
}
