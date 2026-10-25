#ifndef HP_WIFI_DIAG_H
#define HP_WIFI_DIAG_H
#include <stdint.h>
// Fixed numeric startup diagnostics; never pass identifying/network data.
void HPWifiDiagBegin();
void HPWifiDiag(uint32_t stage, int32_t result = 0, bool failure = false);
bool HPWifiDiagBool(uint32_t stage, bool result);
int32_t HPWifiDiagResult(uint32_t stage, int32_t result);

// IRQ-context entry: fixed counter only, no logging, allocation or registry use.
enum HPWifiDiagIRQKind : uint32_t {
    HPWifiDiagIRQFilter = 0,
    HPWifiDiagIRQAction,
    HPWifiDiagIRQRxBatch,
    HPWifiDiagIRQAliveNotification,
    HPWifiDiagIRQPnvmNotification,
    HPWifiDiagIRQInitNotification,
    HPWifiDiagIRQCount
};
void HPWifiDiagIRQEvent(HPWifiDiagIRQKind kind);
// Only call these from safe startup/command-gated context, never an IRQ filter.
// The first IRQ snapshot is retained; a concurrently finishing filter may fall
// on either side of its individual atomic read. No transactional count claim.
void HPWifiDiagCaptureIRQ();
void HPWifiDiagDevice(const char *firmware, uint32_t hardware, uint32_t radio);
void HPWifiDiagBootStatus(uint32_t cpu1, uint32_t cpu2, uint32_t umac, uint32_t lmac);

// Fixed, non-identifying startup command/IRQ trace. Numeric CPU state only.
enum HPWifiDiagTraceKind : uint32_t {
    HPWifiTraceCommandStart = 1,
    HPWifiTraceCommandSubmit = 2,
    HPWifiTraceCommandDescriptor = 3,
    HPWifiTraceCommandDoorbell = 4,
    HPWifiTraceWaitEnter = 5,
    HPWifiTraceWaitReturn = 6,
    HPWifiTraceCommandReturn = 7,
    HPWifiTraceCommandAbort = 8,
    HPWifiTraceCompletionSeen = 9,
    HPWifiTraceCompletionPending = 10,
    HPWifiTraceCompletionDone = 11,
    HPWifiTraceIRQ_ICT = 12,
    HPWifiTraceIRQ_CSR = 13,
    HPWifiTraceIRQ_ICT_EMPTY = 14,
    HPWifiTraceIRQ_CSR_UNAVAILABLE = 15,
    HPWifiTraceIRQ_MSIX_RAW = 16,
    HPWifiTraceRxBatch = 17,
    HPWifiTraceRxHeader = 18,
    HPWifiTraceRxBadHeader = 19,
    HPWifiTraceRxEnd = 20,
    HPWifiTraceLmacError = 21,
    HPWifiTraceUmacError = 22,
    HPWifiTraceIRQExit = 23,
    HPWifiTraceRxDmaReadFailure = 24,
    HPWifiTraceKindLimit = 25
};
bool HPWifiDiagCommandBegin();
void HPWifiDiagTrace(HPWifiDiagTraceKind kind, uint32_t a, uint32_t b, uint32_t c, uint32_t d);
// Safe startup context only. Freeze once, omit uncommitted slots, marker last.
void HPWifiDiagCaptureTrace();
#endif
