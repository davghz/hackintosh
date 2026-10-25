#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <dispatch/dispatch.h>
#include <stdint.h>
#include <stdio.h>
#include <unistd.h>

// Small, bounded compute/readback check for the next accelerated boot.
// An enumerated device alone does not establish working GPU execution.
int main(void) {
    @autoreleasepool {
        NSArray<id<MTLDevice>> *devices = MTLCopyAllDevices();
        printf("Metal devices: %lu\n", (unsigned long)devices.count);
        if (!devices.count) return 2;
        id<MTLDevice> device = devices.firstObject;
        printf("Testing: %s\n", device.name.UTF8String);
        NSError *error = nil;
        NSString *source = @"#include <metal_stdlib>\n"
            "using namespace metal;\n"
            "kernel void verify(device const uint *input [[buffer(0)]], "
            "device uint *output [[buffer(1)]], uint i [[thread_position_in_grid]]) {"
            " if (i < 1024) output[i] = input[i] * 1664525u + 1013904223u; }\n";
        id<MTLLibrary> library = [device newLibraryWithSource:source options:nil error:&error];
        id<MTLFunction> function = [library newFunctionWithName:@"verify"];
        if (!function) {
            fprintf(stderr, "Shader compilation failed: %s\n", error.description.UTF8String ?: "unknown");
            return 3;
        }
        id<MTLComputePipelineState> pipeline = [device newComputePipelineStateWithFunction:function error:&error];
        if (!pipeline) {
            fprintf(stderr, "Pipeline creation failed: %s\n", error.description.UTF8String ?: "unknown");
            return 3;
        }
        const NSUInteger count = 1024;
        id<MTLBuffer> input = [device newBufferWithLength:count*sizeof(uint32_t) options:MTLResourceStorageModeShared];
        id<MTLBuffer> output = [device newBufferWithLength:count*sizeof(uint32_t) options:MTLResourceStorageModeShared];
        id<MTLCommandQueue> queue = [device newCommandQueue];
        if (!input || !output || !queue || !input.contents || !output.contents) return 3;
        uint32_t *in = input.contents, *out = output.contents;
        for (NSUInteger i = 0; i < count; ++i) { in[i] = (uint32_t)i; out[i] = 0; }
        id<MTLCommandBuffer> command = [queue commandBuffer];
        id<MTLComputeCommandEncoder> encoder = [command computeCommandEncoder];
        if (!command || !encoder) return 3;
        [encoder setComputePipelineState:pipeline];
        [encoder setBuffer:input offset:0 atIndex:0];
        [encoder setBuffer:output offset:0 atIndex:1];
        NSUInteger width = MIN((NSUInteger)64, pipeline.maxTotalThreadsPerThreadgroup);
        if (!width) return 3;
        [encoder dispatchThreadgroups:MTLSizeMake((count+width-1)/width,1,1)
               threadsPerThreadgroup:MTLSizeMake(width,1,1)];
        [encoder endEncoding];
        dispatch_semaphore_t done = dispatch_semaphore_create(0);
        [command addCompletedHandler:^(id<MTLCommandBuffer> buffer) { (void)buffer; dispatch_semaphore_signal(done); }];
        puts("Submitting one 1024-element integer compute command; completion timeout 5 seconds.");
        fflush(stdout);
        [command commit];
        if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 5*NSEC_PER_SEC))) {
            fputs("FAIL: GPU completion timed out.\n", stderr);
            fflush(stderr);
            _exit(4);
        }
        if (command.status != MTLCommandBufferStatusCompleted) {
            fprintf(stderr, "FAIL: command status %lu: %s\n", (unsigned long)command.status,
                    command.error.description.UTF8String ?: "unknown");
            return 5;
        }
        for (NSUInteger i = 0; i < count; ++i) {
            uint32_t expected = (uint32_t)i * 1664525U + 1013904223U;
            if (out[i] != expected) {
                fprintf(stderr, "FAIL: readback at %lu: got %u, expected %u\n", (unsigned long)i, out[i], expected);
                return 6;
            }
        }
        puts("PASS: Metal command completed and all 1024 GPU results matched CPU expectations.");
        return 0;
    }
}
