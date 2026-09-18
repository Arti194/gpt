#!/usr/bin/env python3
from pathlib import Path

p = Path("src/VideoManager/VideoReceiver/GStreamer/GstSourceFactory.cc")
s = p.read_text(encoding="utf-8")

old = '''    constexpr GstRTSPLowerTrans kRtspProtocols = static_cast<GstRTSPLowerTrans>(GST_RTSP_LOWER_TRANS_TCP);
    constexpr guint kRtspMinLatencyMs = 120u;
    constexpr guint kRtspMaxLatencyMs = 250u;
    guint rtspLatencyMs = latencyMs;
    if (rtspLatencyMs < kRtspMinLatencyMs) rtspLatencyMs = kRtspMinLatencyMs;
    else if (rtspLatencyMs > kRtspMaxLatencyMs) rtspLatencyMs = kRtspMaxLatencyMs;
    const gboolean doRetransmission = FALSE;
    const gboolean dropOnLatency = TRUE;
'''

new = '''    // Zmiy FPV profile: hard RTSP/RTP over UDP only. Never fall back to TCP.
    // Prefer dropping damaged/late video over accumulating control-view latency.
    constexpr GstRTSPLowerTrans kRtspProtocols =
        static_cast<GstRTSPLowerTrans>(GST_RTSP_LOWER_TRANS_UDP);

    // Small bounded jitter buffer for live piloting. Late packets are discarded.
    constexpr guint kRtspMinLatencyMs = 40u;
    constexpr guint kRtspMaxLatencyMs = 80u;
    guint rtspLatencyMs = latencyMs;
    if (rtspLatencyMs < kRtspMinLatencyMs) rtspLatencyMs = kRtspMinLatencyMs;
    else if (rtspLatencyMs > kRtspMaxLatencyMs) rtspLatencyMs = kRtspMaxLatencyMs;

    // No retransmission: a missing packet must not stall the live view.
    const gboolean doRetransmission = FALSE;
    const gboolean dropOnLatency = TRUE;
'''

if old not in s:
    raise SystemExit("TCP-only Hikvision block not found; dual-camera patch may have changed")

s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")
print("Applied hard UDP low-latency RTSP profile (40-80 ms, no TCP fallback, no retransmission)")
