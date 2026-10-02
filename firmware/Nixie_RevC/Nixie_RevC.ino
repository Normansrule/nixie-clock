// Nixie_RevC.ino - Six-Tube Nixie Clock, Rev C firmware.
//
// Target: Arduino Nano Classic (A000005, ATmega328P, 16 MHz). NOT for ESP32 or Nano Every.
// Libraries: Wire and EEPROM (both ship with the Arduino AVR core). Serial: 115200 baud.
//
// STATUS: UNVALIDATED. This sketch has been compiled for the ATmega328P outside the
// Arduino IDE (see docs/VALIDATION.md) but has never run on a Rev C board.
//
// SAFETY MODEL (see docs/SAFETY.md):
//  * Hardware defaults make the display blank and the HV converter off whenever the Nano
//    is in reset or unprogrammed (base pull-downs, BL pull-down, QP2 gate pull-up).
//  * This firmware keeps HV off until the time is valid (or the user is setting it with the
//    buttons, 60 s timeout), VIN is in range, and a start check sees the rail inside its window.
//    Any out-of-window reading latches HV_FAULT in EEPROM: it survives resets (watchdog,
//    brown-out, the serial monitor's auto-reset) until a deliberate CLEARFAULT command.
//  * Software OFF is NOT proof the rail is discharged. Always measure TP4 before touching.
//  * A 2 s watchdog resets the Nano if the loop hangs; reset = HV off and blank.

#include <Wire.h>
#include <EEPROM.h>
#include <avr/wdt.h>
#include "display_core.h"

// ---------------- Pins (match hardware/NET_MAP.csv) ----------------
const uint8_t PIN_BTN_SET = 2;
const uint8_t PIN_BTN_H = 3;
const uint8_t PIN_BTN_M = 4;
const uint8_t PIN_RUN = 6;       // HIGH = driver outputs enabled (two-stage shifter to BL)
const uint8_t PIN_HV_EN = 7;     // HIGH = converter input switch on (only if HV_ARM is fitted)
const uint8_t PIN_LATCH_N = 9;   // inverted through QL3: Nano HIGH -> LE LOW
const uint8_t PIN_DATA_N = 10;   // inverted through QL2: Nano HIGH -> DIN LOW
const uint8_t PIN_CLOCK_N = 13;  // inverted through QL1: Nano HIGH -> CLK LOW
const uint8_t PIN_HV_SENSE = A0;
const uint8_t PIN_VIN_SENSE = A1;

// ---------------- Limits (decivolts) - review during Stage 3 ----------------
const uint16_t HV_MIN_DV = 1500;       // below 150 V while running = fault
const uint16_t HV_MAX_DV = 1900;       // above 190 V at any time = fault
const uint16_t HV_OFF_OK_DV = 100;     // expected below 10 V a few seconds after HV off (the discharge gate)
const uint16_t VIN_MIN_DV = 108;       // 10.8 V
const uint16_t VIN_MAX_DV = 132;       // 13.2 V (HV5522 VDD maximum)
const unsigned long HV_START_MS = 1500;
const unsigned long HV_DECAY_MS = 3000;
const unsigned long WAKE_MS = 30000UL;
const unsigned long SET_TIMEOUT_MS = 60000UL;
const int FAULT_ADDR = 32;              // EEPROM byte holding the latched-fault marker
const uint8_t FAULT_MARK = 0xA5;        // only this value means "fault latched" (erased EEPROM reads 0xFF)
const uint8_t DS3231_ADDR = 0x68;
const bool SEPARATOR_BLINK = true;

// ---------------- Settings in EEPROM ----------------
struct Settings {
  uint8_t magic;       // 0xC3 = Rev C layout
  uint8_t twelveHour;  // 0 or 1
  uint8_t sleepOn;     // 0 or 1
  uint16_t sleepStart; // minutes of day
  uint16_t sleepEnd;   // minutes of day
};
Settings cfg;

void loadSettings() {
  EEPROM.get(0, cfg);
  if (cfg.magic != 0xC3 || cfg.twelveHour > 1 || cfg.sleepOn > 1 || cfg.sleepStart >= 1440 || cfg.sleepEnd >= 1440) {
    cfg.magic = 0xC3;
    cfg.twelveHour = 0;
    cfg.sleepOn = 0;
    cfg.sleepStart = 23 * 60;
    cfg.sleepEnd = 7 * 60;
    EEPROM.put(0, cfg);
  }
}
void saveSettings() { EEPROM.put(0, cfg); }

// ---------------- State ----------------
enum HvState : uint8_t { HV_OFF, HV_STARTING, HV_ON, HV_FAULT };
enum UiMode : uint8_t { UI_CLOCK, UI_SET_H, UI_SET_M };
HvState hv = HV_OFF;
UiMode ui = UI_CLOCK;
bool timeValid = false;
bool userHold = false;          // serial HVOFF
uint8_t hh = 0, mm = 0, ss = 0;
uint8_t lastSec = 0xFF;
unsigned long hvStateSince = 0;
unsigned long hvOffSince = 0;
bool decayChecked = true;
bool refusedReported = false;
bool unsafeFrame = false;
unsigned long uiSince = 0;
unsigned long wakeUntil = 0;
int8_t exerciseStep = -1;
unsigned long exerciseNext = 0;
const char* faultText = "";

// ---------------- Driver chain ----------------
// Idle levels at the drivers: CLK LOW, LE LOW (latch holds).
void driverIdle() {
  digitalWrite(PIN_CLOCK_N, HIGH);  // CLK LOW
  digitalWrite(PIN_LATCH_N, HIGH);  // LE LOW
  digitalWrite(PIN_DATA_N, HIGH);   // DIN LOW
}

// Shift 64 bits, bit 63 first, then pulse LE. Data is held stable across the whole
// clock pulse, so either clock edge captures it (VERIFY the edge against the datasheet).
void shiftFrame(uint64_t f) {
  if (!nixie::frameIsSafe(f)) {
    f = 0;  // never latch a frame with two cathodes on one tube
    unsafeFrame = true;  // loop() turns this into a latched HV fault
  }
  driverIdle();
  for (int8_t i = 63; i >= 0; i--) {
    bool bit = (f >> i) & 1;
    digitalWrite(PIN_DATA_N, bit ? LOW : HIGH);  // inverted
    delayMicroseconds(4);
    digitalWrite(PIN_CLOCK_N, LOW);   // CLK HIGH
    delayMicroseconds(4);
    digitalWrite(PIN_CLOCK_N, HIGH);  // CLK LOW
    delayMicroseconds(2);
  }
  digitalWrite(PIN_LATCH_N, LOW);   // LE HIGH: copy shift register to outputs
  delayMicroseconds(4);
  digitalWrite(PIN_LATCH_N, HIGH);  // LE LOW: hold
}

void blankDisplay() {
  digitalWrite(PIN_RUN, LOW);  // BL LOW
  shiftFrame(0);
}

// ---------------- Sensing ----------------
uint16_t readAvg(uint8_t pin) {
  uint16_t sum = 0;
  for (uint8_t i = 0; i < 8; i++) sum += analogRead(pin);
  return sum / 8;
}
uint16_t hvDv() { return nixie::hvDeciVolts(readAvg(PIN_HV_SENSE)); }
uint16_t vinDv() { return nixie::vinDeciVolts(readAvg(PIN_VIN_SENSE)); }

void printDv(uint16_t dv) {
  Serial.print(dv / 10);
  Serial.print('.');
  Serial.print(dv % 10);
  Serial.print(F(" V"));
}

// ---------------- HV control ----------------
void hvOff(const char* why) {
  digitalWrite(PIN_HV_EN, LOW);
  blankDisplay();
  if (hv == HV_ON || hv == HV_STARTING) {
    hvOffSince = millis();
    decayChecked = false;
  }
  if (hv != HV_FAULT) hv = HV_OFF;
  if (why && *why) {
    Serial.print(F("HV off: "));
    Serial.println(why);
  }
}

void hvFault(const char* why) {
  if (hv == HV_FAULT) return;  // already latched: no repeated messages or EEPROM writes
  hvOff(why);
  hv = HV_FAULT;
  faultText = why;
  if (EEPROM.read(FAULT_ADDR) != FAULT_MARK) EEPROM.write(FAULT_ADDR, FAULT_MARK);
  Serial.println(F("HV FAULT latched in EEPROM: survives resets. Find the cause, measure TP4, then send CLEARFAULT."));
}

void hvRequestOn() {
  if (hv != HV_OFF) return;
  uint16_t vin = vinDv();
  if (vin < VIN_MIN_DV || vin > VIN_MAX_DV) {
    if (!refusedReported) {  // report once per episode, not every loop
      refusedReported = true;
      Serial.print(F("HV refused: VIN "));
      printDv(vin);
      Serial.println(F(" outside 10.8-13.2 V (USB power alone cannot run the tubes)"));
    }
    return;
  }
  refusedReported = false;
  blankDisplay();
  digitalWrite(PIN_HV_EN, HIGH);
  hv = HV_STARTING;
  hvStateSince = millis();
}

void hvService() {
  unsigned long now = millis();
  uint16_t v = hvDv();
  if (v > HV_MAX_DV) {
    hvFault("HV above 190 V");
    return;
  }
  if (hv == HV_STARTING) {
    if (v >= HV_MIN_DV) {
      hv = HV_ON;
      hvStateSince = now;
      Serial.print(F("HV up: "));
      printDv(v);
      Serial.println();
    } else if (now - hvStateSince > HV_START_MS) {
      hvFault("HV did not reach 150 V (HV_ARM removed? converter fault?)");
    }
  } else if (hv == HV_ON) {
    if (v < HV_MIN_DV) hvFault("HV sagged below 150 V (overload or converter fault)");
  } else if (!decayChecked && now - hvOffSince > HV_DECAY_MS) {
    decayChecked = true;
    if (v > HV_OFF_OK_DV) {
      Serial.print(F("WARNING: HV still "));
      printDv(v);
      Serial.println(F(" 3 s after off. Bleeder or switch fault suspected. Do not open the case."));
    } else {
      Serial.print(F("HV decayed to "));
      printDv(v);
      Serial.println(F(" (sense reading only - still measure TP4 before any contact)"));
    }
  }
}

// ---------------- DS3231 ----------------
bool rtcRead(uint8_t reg, uint8_t* buf, uint8_t n) {
  Wire.beginTransmission(DS3231_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom((int)DS3231_ADDR, (int)n) != n) return false;
  for (uint8_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}
bool rtcWrite(uint8_t reg, const uint8_t* buf, uint8_t n) {
  Wire.beginTransmission(DS3231_ADDR);
  Wire.write(reg);
  for (uint8_t i = 0; i < n; i++) Wire.write(buf[i]);
  return Wire.endTransmission() == 0;
}

// Returns true when a valid time was read. Oscillator-stop flag = invalid.
bool rtcGetTime() {
  uint8_t st;
  if (!rtcRead(0x0F, &st, 1)) return false;
  if (st & 0x80) return false;  // OSF: clock stopped since last set (battery lost?)
  uint8_t b[3];
  if (!rtcRead(0x00, b, 3)) return false;
  uint8_t s = nixie::bcdToBin(b[0] & 0x7F);
  uint8_t m = nixie::bcdToBin(b[1] & 0x7F);
  uint8_t h;
  if (b[2] & 0x40) {  // 12-hour register format (set elsewhere): convert
    h = nixie::bcdToBin(b[2] & 0x1F) % 12;
    if (b[2] & 0x20) h += 12;
  } else {
    h = nixie::bcdToBin(b[2] & 0x3F);
  }
  if (!nixie::validTime(h, m, s)) return false;
  hh = h;
  mm = m;
  ss = s;
  return true;
}

bool rtcSetTime(uint8_t h, uint8_t m, uint8_t s) {
  if (!nixie::validTime(h, m, s)) return false;
  uint8_t b[3] = {nixie::binToBcd(s), nixie::binToBcd(m), nixie::binToBcd(h)};  // 24-hour format
  if (!rtcWrite(0x00, b, 3)) return false;
  uint8_t ctl;
  if (rtcRead(0x0E, &ctl, 1)) {
    ctl &= ~0x80;  // EOSC = 0: keep running on the backup cell
    rtcWrite(0x0E, &ctl, 1);
  }
  uint8_t st;
  if (rtcRead(0x0F, &st, 1)) {
    st &= ~0x80;  // clear OSF
    rtcWrite(0x0F, &st, 1);
  }
  hh = h;
  mm = m;
  ss = s;
  timeValid = true;
  return true;
}

// ---------------- Buttons ----------------
struct Button {
  uint8_t pin;
  bool stable;       // true = pressed
  bool last;
  unsigned long changed;
  unsigned long pressedAt;
  bool longFired;
};
Button bSet = {PIN_BTN_SET, false, false, 0, 0, false};
Button bH = {PIN_BTN_H, false, false, 0, 0, false};
Button bM = {PIN_BTN_M, false, false, 0, 0, false};

// Returns 1 on short press (on release), 2 on long press (2 s, fires once), 0 otherwise.
uint8_t poll(Button& b) {
  bool raw = digitalRead(b.pin) == LOW;
  unsigned long now = millis();
  if (raw != b.last) {
    b.last = raw;
    b.changed = now;
  }
  if (now - b.changed < 30 || raw == b.stable) {
    if (b.stable && !b.longFired && now - b.pressedAt > 2000) {
      b.longFired = true;
      return 2;
    }
    return 0;
  }
  b.stable = raw;
  if (raw) {
    b.pressedAt = now;
    b.longFired = false;
    return 0;
  }
  return b.longFired ? 0 : 1;
}

void wake() { wakeUntil = millis() + WAKE_MS; }

void handleButtons() {
  uint8_t s = poll(bSet), h = poll(bH), m = poll(bM);
  if (s || h || m) wake();
  if (ui != UI_CLOCK && millis() - uiSince > SET_TIMEOUT_MS) {
    ui = UI_CLOCK;  // abandon setting without saving
    Serial.println(F("Set mode timed out (nothing saved)"));
    return;
  }
  if (ui == UI_CLOCK) {
    if (s == 2 || (s == 1 && !timeValid)) {
      ui = UI_SET_H;
      uiSince = millis();
      if (!timeValid) { hh = 0; mm = 0; ss = 0; }
      Serial.println(F("Set hours (H/M to change, SET to continue)"));
    }
    if (h == 2) {
      cfg.twelveHour ^= 1;
      saveSettings();
      Serial.println(cfg.twelveHour ? F("12-hour mode") : F("24-hour mode"));
    }
    if (m == 2) {
      cfg.sleepOn ^= 1;
      saveSettings();
      Serial.println(cfg.sleepOn ? F("Display sleep ON") : F("Display sleep OFF"));
    }
    return;
  }
  if (s || h || m) uiSince = millis();  // any press in set mode restarts the timeout
  if (h == 1) {
    if (ui == UI_SET_H) hh = (hh + 1) % 24;
    else mm = (mm + 1) % 60;
  }
  if (m == 1) {
    if (ui == UI_SET_H) hh = (hh + 23) % 24;
    else mm = (mm + 59) % 60;
  }
  if (s == 1) {
    if (ui == UI_SET_H) {
      ui = UI_SET_M;
    } else {
      ui = UI_CLOCK;
      if (rtcSetTime(hh, mm, 0)) Serial.println(F("Time saved to RTC"));
      else Serial.println(F("RTC write failed"));
    }
  }
}

// ---------------- Serial commands ----------------
char line[32];
uint8_t lineLen = 0;

void printStatus() {
  Serial.print(F("time "));
  if (timeValid) {
    if (hh < 10) Serial.print('0');
    Serial.print(hh);
    Serial.print(':');
    if (mm < 10) Serial.print('0');
    Serial.print(mm);
    Serial.print(':');
    if (ss < 10) Serial.print('0');
    Serial.println(ss);
  } else {
    Serial.println(F("INVALID (set with T hh:mm:ss or long-press SET)"));
  }
  Serial.print(F("VIN "));
  printDv(vinDv());
  Serial.print(F("  HV sense "));
  printDv(hvDv());
  Serial.print(F("  state "));
  const char* names[] = {"OFF", "STARTING", "ON", "FAULT"};
  Serial.println(names[hv]);
  if (hv == HV_FAULT) {
    Serial.print(F("fault: "));
    Serial.println(faultText);
  }
  Serial.print(F("buttons SET/H/M "));
  Serial.print(digitalRead(PIN_BTN_SET) == LOW);
  Serial.print(digitalRead(PIN_BTN_H) == LOW);
  Serial.println(digitalRead(PIN_BTN_M) == LOW);
  Serial.print(cfg.twelveHour ? F("12h") : F("24h"));
  Serial.print(F("  sleep "));
  Serial.println(cfg.sleepOn ? F("on") : F("off"));
}

bool parse2(const char* p, uint8_t& v) {
  if (p[0] < '0' || p[0] > '9' || p[1] < '0' || p[1] > '9') return false;
  v = (uint8_t)((p[0] - '0') * 10 + (p[1] - '0'));
  return true;
}

void runCommand() {
  line[lineLen] = 0;
  uint8_t a, b, c, d;
  if (line[0] == 'T' && line[1] == ' ' && lineLen >= 10 && parse2(line + 2, a) && parse2(line + 5, b) && parse2(line + 8, c)) {
    Serial.println(rtcSetTime(a, b, c) ? F("OK time set") : F("ERR bad time or RTC"));
  } else if (!strcmp(line, "12") || !strcmp(line, "24")) {
    cfg.twelveHour = line[0] == '1';
    saveSettings();
    Serial.println(F("OK"));
  } else if (!strcmp(line, "SLEEP OFF")) {
    cfg.sleepOn = 0;
    saveSettings();
    Serial.println(F("OK"));
  } else if (!strncmp(line, "SLEEP ", 6) && lineLen >= 17 && parse2(line + 6, a) && parse2(line + 9, b) && parse2(line + 12, c) && parse2(line + 15, d) && a < 24 && b < 60 && c < 24 && d < 60) {
    cfg.sleepOn = 1;
    cfg.sleepStart = a * 60 + b;
    cfg.sleepEnd = c * 60 + d;
    saveSettings();
    Serial.println(F("OK"));
  } else if (!strcmp(line, "HVOFF")) {
    userHold = true;
    hvOff("serial HVOFF");
  } else if (!strcmp(line, "RUN")) {
    userHold = false;
    Serial.println(F("OK"));
  } else if (!strcmp(line, "CLEARFAULT")) {
    EEPROM.write(FAULT_ADDR, 0);
    if (hv == HV_FAULT) hv = HV_OFF;
    faultText = "";
    Serial.println(F("Fault cleared. HV may restart now if the display is wanted: be sure TP4 was measured and the cause fixed."));
  } else if (!strcmp(line, "EXERCISE")) {
    exerciseStep = 0;
  } else if (!strcmp(line, "STATUS") || lineLen == 0) {
    printStatus();
  } else {
    Serial.println(F("Commands: STATUS | T hh:mm:ss | 12 | 24 | SLEEP hh:mm hh:mm | SLEEP OFF | HVOFF | RUN | EXERCISE | CLEARFAULT"));
  }
  lineLen = 0;
}

void handleSerial() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') {
      runCommand();
    } else if (lineLen < sizeof(line) - 1) {
      line[lineLen++] = (ch >= 'a' && ch <= 'z') ? ch - 32 : ch;
    }
  }
}

// ---------------- Display policy ----------------
bool wantDisplay() {
  if (userHold || hv == HV_FAULT) return false;
  if (ui != UI_CLOCK) return true;  // user is setting the time
  if (!timeValid) return false;     // default off on invalid time
  if (cfg.sleepOn && nixie::inWindow(hh * 60 + mm, cfg.sleepStart, cfg.sleepEnd) && (long)(millis() - wakeUntil) > 0) return false;
  return true;
}

void render() {
  uint8_t d[nixie::kTubes];
  bool sep = true;
  if (exerciseStep >= 0) {
    nixie::exerciseDigits((uint8_t)exerciseStep, d);
  } else {
    nixie::timeToDigits(hh, mm, ui == UI_CLOCK ? ss : 0, cfg.twelveHour && ui == UI_CLOCK, d);
    bool blinkOff = (millis() / 400) % 2;
    if (ui == UI_SET_H && blinkOff) d[0] = d[1] = nixie::kBlank;
    if (ui == UI_SET_M && blinkOff) d[2] = d[3] = nixie::kBlank;
    if (ui == UI_CLOCK && SEPARATOR_BLINK) sep = (ss % 2) == 0;
  }
  shiftFrame(nixie::buildFrame(d, sep, sep));
  digitalWrite(PIN_RUN, HIGH);  // BL HIGH: outputs enabled
}

// ---------------- Arduino entry points ----------------
void setup() {
  // First: force every HV-related line to its safe state before anything else runs.
  digitalWrite(PIN_HV_EN, LOW);
  pinMode(PIN_HV_EN, OUTPUT);
  digitalWrite(PIN_RUN, LOW);
  pinMode(PIN_RUN, OUTPUT);
  pinMode(PIN_CLOCK_N, OUTPUT);
  pinMode(PIN_DATA_N, OUTPUT);
  pinMode(PIN_LATCH_N, OUTPUT);
  blankDisplay();

  uint8_t resetCause = MCUSR;
  MCUSR = 0;
  wdt_enable(WDTO_2S);

  pinMode(PIN_BTN_SET, INPUT_PULLUP);
  pinMode(PIN_BTN_H, INPUT_PULLUP);
  pinMode(PIN_BTN_M, INPUT_PULLUP);

  Serial.begin(115200);
  Serial.println(F("Nixie Rev C (UNVALIDATED PROTOTYPE FIRMWARE)"));
  // Note: some bootloaders clear MCUSR before the sketch runs, so these may not print.
  if (resetCause & _BV(WDRF)) Serial.println(F("reset: watchdog"));
  if (resetCause & _BV(BORF)) Serial.println(F("reset: brown-out"));

  Wire.begin();
  Wire.setClock(100000);
  loadSettings();
  if (EEPROM.read(FAULT_ADDR) == FAULT_MARK) {
    hv = HV_FAULT;
    faultText = "fault latched before this reset";
    Serial.println(F("HV FAULT is latched from before the reset: HV stays OFF. Measure TP4, fix the cause, then send CLEARFAULT."));
  }
  timeValid = rtcGetTime();
  if (!timeValid) Serial.println(F("RTC time invalid or RTC missing: display stays OFF. Set time to start."));
  wake();
  printStatus();
}

void loop() {
  wdt_reset();
  handleSerial();
  handleButtons();

  static unsigned long lastRtc = 0;
  if (millis() - lastRtc >= 100 && ui == UI_CLOCK) {
    lastRtc = millis();
    bool ok = rtcGetTime();
    if (!ok && timeValid) {
      timeValid = false;
      Serial.println(F("RTC read failed or oscillator stopped: display OFF"));
    } else if (ok) {
      timeValid = true;
    }
    // Hourly anti-poisoning exercise at hh:00:00.
    if (timeValid && ss != lastSec && mm == 0 && ss == 0 && exerciseStep < 0) exerciseStep = 0;
  }

  bool want = wantDisplay();
  if (want && hv == HV_OFF) hvRequestOn();
  if (!want && (hv == HV_ON || hv == HV_STARTING)) hvOff(userHold ? "" : "display not wanted (sleep or invalid time)");
  hvService();
  if (unsafeFrame) {
    unsafeFrame = false;
    Serial.println(F("unsafe frame rejected (more than one cathode on a tube)"));
    hvFault("unsafe frame rejected");
  }

  if (hv == HV_ON) {
    if (exerciseStep >= 0 && (long)(millis() - exerciseNext) >= 0) {  // wrap-safe
      exerciseNext = millis() + 200;
      render();
      if (++exerciseStep >= 10) exerciseStep = -1;
    } else if (exerciseStep < 0 && (ss != lastSec || ui != UI_CLOCK)) {
      render();
    }
  } else if (exerciseStep >= 0) {
    exerciseStep = -1;  // no HV, no exercise
  }
  lastSec = ss;
}
