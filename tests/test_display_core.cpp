// Host unit tests for firmware/Nixie_RevC/display_core.h.
// Build and run:  g++ -std=c++11 -Wall -Wextra -I firmware/Nixie_RevC tests/test_display_core.cpp -o /tmp/tdc && /tmp/tdc
// These are firmware-core checks on a PC. They are not evidence the real driver chain works.
#include <cstdio>
#include <cstdlib>
#include "display_core.h"

using namespace nixie;
static int fails = 0, total = 0;
#define CHECK(c) do { total++; if (!(c)) { fails++; std::printf("FAIL line %d: %s\n", __LINE__, #c); } } while (0)

static int popcount64(uint64_t v) { int n = 0; while (v) { v &= v - 1; n++; } return n; }

int main() {
  // Every digit of every tube maps to a unique bit in the right bank, never OUT31/OUT32.
  uint64_t seen = 0;
  for (uint8_t t = 0; t < 6; t++)
    for (uint8_t d = 0; d < 10; d++) {
      uint64_t m = digitMask(t, d);
      CHECK(popcount64(m) == 1);
      CHECK((seen & m) == 0);
      seen |= m;
      CHECK((t < 3) ? (m & 0xFFFFFFFFull) != 0 : (m >> 32) != 0);
      CHECK((m & (separatorMask(0) | separatorMask(1) | unusedMask())) == 0);
    }
  CHECK(popcount64(seen) == 60);
  CHECK(popcount64(separatorMask(0) | separatorMask(1) | unusedMask()) == 4);
  CHECK((seen | separatorMask(0) | separatorMask(1) | unusedMask()) == ~0ull);

  // Specific mapping (kOutReversed = false): T1 digit 0 = U1 OUT1 = bit 0; T4 digit 0 = U2 OUT1 = bit 32.
  CHECK(digitMask(0, 0) == 1ull);
  CHECK(digitMask(2, 9) == (1ull << 29));
  CHECK(separatorMask(0) == (1ull << 30));
  CHECK(digitMask(3, 0) == (1ull << 32));
  CHECK(separatorMask(1) == (1ull << 62));
  CHECK(unusedMask() == ((1ull << 31) | (1ull << 63)));

  // One-active-digit rule.
  uint8_t d[6] = {1, 2, 3, 4, 5, 6};
  uint64_t f = buildFrame(d, true, true);
  CHECK(frameIsSafe(f));
  CHECK(popcount64(f) == 8);
  CHECK(!frameIsSafe(f | digitMask(0, 7)));       // two cathodes on T1
  CHECK(!frameIsSafe(f | unusedMask()));          // OUT32 set
  CHECK(frameIsSafe(0));
  uint8_t blank[6] = {kBlank, kBlank, kBlank, kBlank, kBlank, kBlank};
  CHECK(buildFrame(blank, false, false) == 0);
  uint8_t bad[6] = {10, 11, 200, 9, 9, 9};        // out-of-range digits are ignored, not wrapped
  CHECK(popcount64(buildFrame(bad, false, false)) == 3);

  // Time formatting.
  uint8_t o[6];
  timeToDigits(13, 5, 9, false, o);
  CHECK(o[0] == 1 && o[1] == 3 && o[2] == 0 && o[3] == 5 && o[4] == 0 && o[5] == 9);
  timeToDigits(13, 5, 9, true, o);
  CHECK(o[0] == kBlank && o[1] == 1);
  timeToDigits(0, 0, 0, true, o);
  CHECK(o[0] == 1 && o[1] == 2);
  timeToDigits(12, 0, 0, true, o);
  CHECK(o[0] == 1 && o[1] == 2);
  timeToDigits(23, 59, 59, false, o);
  CHECK(o[0] == 2 && o[1] == 3 && o[2] == 5 && o[3] == 9 && o[4] == 5 && o[5] == 9);
  CHECK(validTime(23, 59, 59) && !validTime(24, 0, 0) && !validTime(0, 60, 0) && !validTime(0, 0, 60));

  // Every valid time produces a safe frame.
  for (int h = 0; h < 24; h++)
    for (int m = 0; m < 60; m++)
      for (int s = 0; s < 60; s += 7)
        for (int mode = 0; mode < 2; mode++) {
          timeToDigits(h, m, s, mode, o);
          if (!frameIsSafe(buildFrame(o, true, true))) { fails++; std::printf("unsafe frame at %02d:%02d:%02d\n", h, m, s); }
        }

  // BCD.
  for (int v = 0; v < 100; v++) CHECK(bcdToBin(binToBcd(v)) == v);
  CHECK(binToBcd(59) == 0x59);

  // Sleep window, including wrap past midnight.
  CHECK(inWindow(23 * 60 + 30, 23 * 60, 7 * 60));
  CHECK(inWindow(3 * 60, 23 * 60, 7 * 60));
  CHECK(!inWindow(12 * 60, 23 * 60, 7 * 60));
  CHECK(!inWindow(7 * 60, 23 * 60, 7 * 60));
  CHECK(inWindow(9 * 60, 8 * 60, 17 * 60));
  CHECK(!inWindow(9 * 60, 8 * 60, 8 * 60));

  // Exercise lights every cathode of every tube once over 10 steps.
  uint64_t lit = 0;
  for (uint8_t st = 0; st < 10; st++) {
    exerciseDigits(st, o);
    uint64_t ff = buildFrame(o, false, false);
    CHECK(frameIsSafe(ff));
    lit |= ff;
  }
  CHECK(lit == seen);

  // Sense conversions match tests/check_equations.py.
  CHECK(hvDeciVolts(378) >= 1695 && hvDeciVolts(378) <= 1700);  // ~170 V
  CHECK(hvDeciVolts(1023) == 4595);
  CHECK(vinDeciVolts(431) >= 119 && vinDeciVolts(431) <= 121);  // ~12 V

  std::printf("%d/%d display-core host checks passed\n", total - fails, total);
  return fails ? 1 : 0;
}
