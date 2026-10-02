# Firmware: Nixie_RevC

For the **Arduino Nano Classic (A000005, ATmega328P, 16 MHz)** only. Not for the Nano Every, Nano ESP32 or other boards. Uses only `Wire` and `EEPROM`, which ship with the Arduino AVR core. Serial at 115200 baud.

**Status: UNVALIDATED.** Compiled and linked for the ATmega328P with avr-gcc outside the Arduino IDE; never run on a Rev C board. Read [docs/SAFETY.md](../../docs/SAFETY.md) before connecting USB to a board that has ever had HV on it.

## Files

- `Nixie_RevC.ino`: pins, safe start-up, HV state machine, RTC, buttons, serial commands.
- `display_core.h`: pure logic (bit mapping, one-digit-per-tube check, time formatting, sense conversions). Tested on a PC by `tests/test_display_core.cpp`.

## Features

HH:MM:SS; 12/24-hour; time setting by buttons or serial; real-time clock (RTC) with coin-cell backup; startup blanking; display sleep window; hourly digit exercise against cathode poisoning; VIN and HV diagnostics; default-off on invalid time, reset and faults.

## Safe defaults

- The first lines of `setup()` drive HV_EN and RUN low and shift an all-off frame.
- HV starts only when the time is valid (or while you set it with the buttons, which times out after 60 s), VIN reads 10.8–13.2 V (13.2 V is the HV5522's VDD maximum), and the rail reaches 150 V within 1.5 s. Above 190 V at any time, below 150 V while running, or an unsafe frame latches `HV FAULT` **in EEPROM**: it survives every reset, including the one the serial monitor causes, until you send `CLEARFAULT`.
- Every frame passes `frameIsSafe()` (at most one cathode per tube, never HVOUT32) or an all-off frame is sent instead.
- A 2 s watchdog resets the Nano if the loop hangs; in reset the hardware blanks the tubes and turns HV off.

## Buttons

| Action | Result |
|---|---|
| Hold SET 2 s (or press SET while the time is invalid) | Set hours: H up, M down; SET → set minutes; SET → save (seconds = 00). 60 s without a press abandons setting. HV runs while setting so you can see the digits |
| Hold H 2 s | Toggle 12 / 24-hour (saved) |
| Hold M 2 s | Toggle display sleep (saved) |
| Any press during sleep | Wake for 30 s |

## Serial commands (115200, newline)

`STATUS` · `T hh:mm:ss` · `12` · `24` · `SLEEP hh:mm hh:mm` · `SLEEP OFF` · `HVOFF` (HV off and blank until `RUN`) · `RUN` · `EXERCISE` · `CLEARFAULT` (only after measuring TP4 and fixing the cause)

## Build-time constants to confirm on real hardware

- `nixie::kOutReversed` in `display_core.h` (false = HVOUT*n* is frame bit *n* − 1, matching the data sheet's shift direction). Confirm in Stage 4 by lighting one digit at a time.
- HV window `HV_MIN_DV` / `HV_MAX_DV` and VIN window in `Nixie_RevC.ino`.
- The anode resistor start value (22 kΩ) is not a verified brightness: measure every digit before changing it.

## Build it

Arduino IDE: *Tools → Board → Arduino AVR Boards → Arduino Nano*, *Processor → ATmega328P* (or *Old Bootloader*), then Upload. Record the IDE and core versions in `docs/VALIDATION.md` and pin them in `docs/SECURITY.md` once Stage 2 passes.

Without the IDE (compile check only): `scripts/avr_compile_check.sh /path/to/ArduinoCore-avr`.
