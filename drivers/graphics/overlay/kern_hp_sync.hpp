#pragma once
#include <stdint.h>
#include <stddef.h>

namespace HPSync {
constexpr uint32_t MaxChannels = 128;
constexpr uint32_t EventSlots = 8;
constexpr uint32_t WaitLimitMs = 250;
constexpr uint32_t MaxResources = 4096;
constexpr uint32_t EmptyChannel = 0xFFFFFFFFU;

// IOAccelEventMachineFast2 on the pinned 25G241 kernel uses eight packed
// {uint32 channel, uint32 stamp} entries. Timestamp comparisons wrap at 32 bits.
struct Dependencies {
    uint32_t stamps[MaxChannels] {};
    bool present[MaxChannels] {};
    uint32_t channels {0};

    bool add(const uint64_t (&event)[EventSlots], uint32_t channelCount, uint32_t exclude) {
        if (!channelCount || channelCount > MaxChannels || exclude >= channelCount) return false;
        for (uint32_t i = 0; i < EventSlots; ++i) {
            const uint32_t ch = static_cast<uint32_t>(event[i]);
            if (ch != EmptyChannel && ch >= channelCount) return false;
        }
        for (uint32_t i = 0; i < EventSlots; ++i) {
            const uint32_t ch = static_cast<uint32_t>(event[i]);
            if (ch == EmptyChannel || ch == exclude) continue;
            const uint32_t stamp = static_cast<uint32_t>(event[i] >> 32);
            if (!present[ch]) { present[ch] = true; stamps[ch] = stamp; ++channels; }
            else if (static_cast<int32_t>(stamp - stamps[ch]) > 0) stamps[ch] = stamp;
        }
        return true;
    }
    bool packet(uint32_t &next, uint64_t (&event)[EventSlots]) const {
        for (auto &entry : event) entry = EmptyChannel;
        uint32_t used = 0;
        while (next < MaxChannels && used < EventSlots) {
            const uint32_t ch = next++;
            if (present[ch]) event[used++] = (static_cast<uint64_t>(stamps[ch]) << 32) | ch;
        }
        return used != 0;
    }
};

inline bool range(uint64_t pointer, size_t length) {
    return length && length <= 65536 && (pointer >> 47) == 0x1FFFF &&
        pointer <= UINT64_MAX - (length - 1);
}
}
