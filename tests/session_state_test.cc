#include "../tools/multicam/SessionState.h"
#include <cassert>
int main() {
    SessionState s;
    s.add(100, 0); assert(s.bytes == 0);
    s.connect("vehicle-a", 0); s.add(1000000, 1);
    s.lost(2); s.add(500, 30000);
    s.connect("vehicle-a", 60002); assert(s.bytes == 1000500);
    s.lost(70000); s.connect("vehicle-a", 130001); assert(s.bytes == 0);
    s.add(100, 130002); s.connect("vehicle-b", 130003); assert(s.bytes == 0);
    s.add(100, 130004); s.disconnect(); s.connect("vehicle-b", 130005); assert(s.bytes == 0);
    s.lost(130006); s.add(100, 190007); assert(s.bytes == 0);
    s.connect("vehicle-b", 190008); s.add(100, 190009); assert(s.bytes == 100);
}
