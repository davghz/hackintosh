#pragma once
// Publication policy only. No kernel APIs, I/O, allocation, or retained pointers.
#include <stdint.h>

namespace hpbat {
// Pinned XNU IOPMPrivate.h (f6217f891ac0bb64f3d375211650a4c1ff8ca1ea).
// These bits report observed adapter state; no sleep or clamshell command.
constexpr uint32_t policySetValue = 1u << 16;
constexpr uint32_t policySetACConnected = 1u << 18;
enum class PolicyResult { Inactive, Invalid, Unchanged, Deferred, Submitted };

struct ACPowerPolicy {
    bool submitted = false;
    bool external = false;

    void invalidate() { submitted = false; }

    template <typename Submit>
    PolicyResult publish(uint32_t psr, bool active, Submit submit) {
        if (!active) return PolicyResult::Inactive;
        if (psr > 1) return PolicyResult::Invalid;
        const bool next = psr == 1;
        if (submitted && external == next) return PolicyResult::Unchanged;
        const uint32_t message = policySetACConnected | (next ? policySetValue : 0u);
        if (!submit(message)) return PolicyResult::Deferred;
        // The API acknowledges submission, not completed root-domain handling.
        external = next;
        submitted = true;
        return PolicyResult::Submitted;
    }
};
}
