# QGroundControl Multi CAM for Windows

Customizations of upstream QGroundControl pinned to `527296e2d2d4ee95f52e0001db4ecb7d317fe814`.
Apply `tools/patch_qgc_dual_hikvision.py`, then `tools/patch_qgc_udp_low_latency.py`, then `tools/patch_qgc_multicam.py` in the upstream checkout.

- Multi CAM supports 2–5 cameras with separate MAIN/SUB RTSP URLs. The `+` button adds cameras; only cameras 3–5 can be removed. URLs persist across restarts. Removing a camera shifts subsequent camera pairs together.
- One large video with smaller previews on the left. Clicking a preview swaps it with the main camera. The MAIN/SUB switch sits at center right and switches every active camera together. Stream changes briefly restart the affected receivers.
- The optional Vehicle Model starts empty. A one-time migration clears the old automatic “Змій” name while preserving other custom names and existing camera URLs.
- Battery left click toggles percentage/voltage and persists the display selection. Right click or long press opens battery details. Percentage requires valid onboard battery telemetry; voltage is the fallback when percentage is unavailable.
- Ping is MAVLink PING round-trip time to the active vehicle's autopilot through its primary link. An unanswered/stale ping displays `—`, never a fabricated latency.
- RX MB includes incoming MAVLink link bytes and video network-source buffers (RTP/RTCP for RTSP) received by QGC while a vehicle session is open. Decimal MB: 1 MB = 1,000,000 bytes. This is **not total Starlink usage**: other apps/devices, outbound traffic, IP/UDP/TCP/VPN overhead and RTSP control messages are excluded. Assumes configured video streams belong to the active vehicle.
- Explicit disconnect resets the session. An unplanned interruption of up to 60 seconds preserves it; a longer interruption or different vehicle/link identity starts a new session. Video bytes during the brief interruption are included.
- RTSP remains UDP only, with a bounded 40–80 ms jitter buffer, late-packet dropping and retransmission disabled.

## Validation

The Windows workflow applies all patches to the pinned upstream tree, generates settings pages, runs the standalone C++ session test, builds QGC and packages `QGroundControl-MultiCAM-UDP.exe` with its SHA256 hash. Installer artifacts are kept for 30 days.

Local session test:

```sh
g++ -std=c++17 -Wall -Wextra -Werror tests/session_state_test.cc -o /tmp/session-state-test
/tmp/session-state-test
```

Hardware checks still require live cameras/autopilot: test all 2–5 camera layouts, camera selection, MAIN/SUB URLs, ping support, battery telemetry and Starlink reconnects before operating.
