#pragma once
#include <cstdint>
#include <string>

// Monotonic milliseconds. A manual disconnect always ends a session; an
// unplanned outage preserves it for at most 60 seconds, including its video.
class SessionState {
public:
    static constexpr int64_t graceMs = 60000;
    void connect(const std::string &key, int64_t now) {
        if (!open || identity != key || (gapStart >= 0 && now - gapStart > graceMs)) bytes = 0;
        identity = key;
        open = true;
        gapStart = -1;
    }
    void lost(int64_t now) { if (open && gapStart < 0) gapStart = now; }
    void disconnect() { open = false; gapStart = -1; bytes = 0; identity.clear(); }
    void add(uint64_t amount, int64_t now) {
        if (open && (gapStart < 0 || now - gapStart <= graceMs)) bytes += amount;
    }
    uint64_t bytes = 0;
    bool open = false;
    int64_t gapStart = -1;
    std::string identity;
};
