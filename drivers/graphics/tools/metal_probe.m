#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
int main(void) {
    @autoreleasepool {
        NSArray<id<MTLDevice>> *devices = MTLCopyAllDevices();
        printf("Metal devices: %lu\n", (unsigned long)devices.count);
        for (id<MTLDevice> device in devices) {
            printf("Device: %s; registry ID: 0x%llx; low power: %s\n",
                   device.name.UTF8String, (unsigned long long)device.registryID,
                   device.lowPower ? "yes" : "no");
        }
        return devices.count ? 0 : 2;
    }
}
