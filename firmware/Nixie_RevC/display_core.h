// display_core.h - Rev C display logic with no hardware access.
//
// Everything here is pure computation so it can be unit-tested on a PC
// (tests/test_display_core.cpp) as well as compiled for the ATmega328P.
// A passing host test shows the arithmetic is self-consistent. It does NOT show
// that the bit order, polarity or clock edge match the real HV5522PJ-G.
//
// Frame layout (64 bits, shifted bit 63 first, so U1 ends up in the lower 32 bits):
//   bits  0..31 : U1  -> T1, T2, T3 digits (OUT1..OUT30) and separator L1 (OUT31)
//   bits 32..63 : U2  -> T4, T5, T6 digits (OUT1..OUT30) and separator L2 (OUT31)
//   OUT32 of each bank is unused and must never be set.
// Within a bank, OUTn maps to bit (n-1) unless kOutReversed is true, in which case
// OUTn maps to bit (32-n). Pick the value that matches the datasheet shift direction
// during Stage 4 of the build guide (one digit at a time).
#ifndef NIXIE_DISPLAY_CORE_H
#define NIXIE_DISPLAY_CORE_H

#include <stdint.h>

namespace nixie {

// ---- Build-time constants (VERIFY on the real board) ----
static const bool kOutReversed = false;   // HV5522 shift direction within a bank
static const uint8_t kTubes = 6;
static const uint8_t kBlank = 0xFF;      // "no digit" marker

// HV sense: A0 sees HV * 22k / (1M + 1M + 22k). ADC reference = 5 V AVCC.
// Full scale 5 V -> 459.5 V, i.e. 4595 decivolts per 1023 counts.
static const uint32_t kHvFullScaleDeciV = 4595;
// VIN sense: A1 sees VIN * 10k / (47k + 10k). Full scale 5 V -> 28.5 V.
static const uint32_t kVinFullScaleDeciV = 285;

// ---- Driver bit mapping ----
inline uint8_t outToBit(uint8_t bank, uint8_t out /*1..32*/) {
  uint8_t b = kOutReversed ? (uint8_t)(32 - out) : (uint8_t)(out - 1);
  return (uint8_t)(bank * 32 + b);
}

// OUT number (1..30) for a digit on a tube (tube 0..5, digit 0..9).
inline uint8_t digitOut(uint8_t tube, uint8_t digit) {
  return (uint8_t)(1 + (tube % 3) * 10 + digit);
}

inline uint64_t digitMask(uint8_t tube, uint8_t digit) {
  if (tube >= kTubes || digit > 9) return 0;
  return (uint64_t)1 << outToBit(tube / 3, digitOut(tube, digit));
}

inline uint64_t separatorMask(uint8_t sep /*0 = L1 on U1, 1 = L2 on U2*/) {
  if (sep > 1) return 0;
  return (uint64_t)1 << outToBit(sep, 31);
}

inline uint64_t unusedMask() {
  return ((uint64_t)1 << outToBit(0, 32)) | ((uint64_t)1 << outToBit(1, 32));
}

// All ten cathode bits that belong to one tube.
inline uint64_t tubeMask(uint8_t tube) {
  uint64_t m = 0;
  for (uint8_t d = 0; d < 10; d++) m |= digitMask(tube, d);
  return m;
}

// One-active-digit rule: every tube has at most one cathode on, and no unused
// output is set. The firmware refuses to latch any frame that fails this.
inline bool frameIsSafe(uint64_t f) {
  if (f & unusedMask()) return false;
  uint64_t known = separatorMask(0) | separatorMask(1);
  for (uint8_t t = 0; t < kTubes; t++) {
    uint64_t m = f & tubeMask(t);
    if (m & (m - 1)) return false;  // more than one bit set
    known |= tubeMask(t);
  }
  return (f & ~known) == 0;
}

inline uint64_t buildFrame(const uint8_t digits[kTubes], bool sep1, bool sep2) {
  uint64_t f = 0;
  for (uint8_t t = 0; t < kTubes; t++) {
    if (digits[t] <= 9) f |= digitMask(t, digits[t]);
  }
  if (sep1) f |= separatorMask(0);
  if (sep2) f |= separatorMask(1);
  return f;
}

// ---- Time helpers ----
inline bool validTime(uint8_t h, uint8_t m, uint8_t s) { return h < 24 && m < 60 && s < 60; }

inline uint8_t bcdToBin(uint8_t v) { return (uint8_t)((v >> 4) * 10 + (v & 0x0F)); }
inline uint8_t binToBcd(uint8_t v) { return (uint8_t)(((v / 10) << 4) | (v % 10)); }

inline uint8_t hourForDisplay(uint8_t h24, bool twelveHour) {
  if (!twelveHour) return h24;
  uint8_t h = h24 % 12;
  return h == 0 ? 12 : h;
}

// Fills six digits HH MM SS. In 12-hour mode a leading hour zero is blanked.
inline void timeToDigits(uint8_t h24, uint8_t m, uint8_t s, bool twelveHour, uint8_t out[kTubes]) {
  uint8_t h = hourForDisplay(h24, twelveHour);
  out[0] = (uint8_t)(h / 10);
  out[1] = (uint8_t)(h % 10);
  out[2] = (uint8_t)(m / 10);
  out[3] = (uint8_t)(m % 10);
  out[4] = (uint8_t)(s / 10);
  out[5] = (uint8_t)(s % 10);
  if (twelveHour && out[0] == 0) out[0] = kBlank;
}

// Minutes-of-day window check; handles windows that wrap past midnight.
inline bool inWindow(uint16_t nowMin, uint16_t startMin, uint16_t endMin) {
  if (startMin == endMin) return false;
  if (startMin < endMin) return nowMin >= startMin && nowMin < endMin;
  return nowMin >= startMin || nowMin < endMin;
}

// Anti-poisoning exercise: over steps 0..9 every tube lights every one of its ten
// cathodes once. Tubes are offset so the six tubes never show the same digit.
inline void exerciseDigits(uint8_t step, uint8_t out[kTubes]) {
  for (uint8_t t = 0; t < kTubes; t++) out[t] = (uint8_t)((step + t) % 10);
}

// ---- Sense conversions (integer, decivolts) ----
inline uint16_t hvDeciVolts(uint16_t adc) { return (uint16_t)((uint32_t)adc * kHvFullScaleDeciV / 1023); }
inline uint16_t vinDeciVolts(uint16_t adc) { return (uint16_t)((uint32_t)adc * kVinFullScaleDeciV / 1023); }

}  // namespace nixie

#endif  // NIXIE_DISPLAY_CORE_H
