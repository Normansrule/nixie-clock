#!/usr/bin/env bash
# avr_compile_check.sh - compile and link firmware/Nixie_RevC for the ATmega328P with avr-gcc,
# against the official Arduino AVR core sources, WITHOUT the Arduino IDE or arduino-cli.
#
# What a pass means: the sketch, Wire and the core compile and link for an ATmega328P at 16 MHz,
# and the image fits in flash/RAM. What it does NOT mean: that the Arduino IDE build is identical,
# that the bootloader/upload works, or that the firmware behaves correctly on a board.
#
# Usage: scripts/avr_compile_check.sh [path-to-ArduinoCore-avr]
#   Needs: avr-gcc, avr-g++, avr-size, avr-objcopy (Ubuntu: sudo apt install gcc-avr avr-libc)
#   Core:  git clone --depth 1 --branch 1.8.6 https://github.com/arduino/ArduinoCore-avr.git
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CORE="${1:-${ARDUINO_CORE:-$ROOT/.build/ArduinoCore-avr}}"
if [ ! -d "$CORE/cores/arduino" ]; then
  echo "Arduino AVR core not found at $CORE"
  echo "Fetch it:  git clone --depth 1 --branch 1.8.6 https://github.com/arduino/ArduinoCore-avr.git \"$CORE\""
  exit 2
fi
B="$ROOT/.build/avr"
rm -rf "$B" && mkdir -p "$B"
MCU="-mmcu=atmega328p -DF_CPU=16000000L -DARDUINO=10819 -DARDUINO_AVR_NANO -DARDUINO_ARCH_AVR"
INC="-I$CORE/cores/arduino -I$CORE/variants/eightanaloginputs -I$CORE/libraries/Wire/src -I$CORE/libraries/EEPROM/src -I$ROOT/firmware/Nixie_RevC"
CFLAGS="-Os -Wall -ffunction-sections -fdata-sections $MCU $INC"
CXXFLAGS="$CFLAGS -std=gnu++11 -fpermissive -fno-exceptions -fno-threadsafe-statics"

{ echo '#include <Arduino.h>'; echo '#line 1 "Nixie_RevC.ino"'; cat "$ROOT/firmware/Nixie_RevC/Nixie_RevC.ino"; } > "$B/sketch.cpp"
avr-g++ $CXXFLAGS -Wextra -c "$B/sketch.cpp" -o "$B/sketch.o"

objs=()
for f in "$CORE"/cores/arduino/*.c "$CORE/libraries/Wire/src/utility/twi.c"; do
  o="$B/$(basename "$f").o"; avr-gcc $CFLAGS -std=gnu11 -c "$f" -o "$o"; objs+=("$o"); done
for f in "$CORE"/cores/arduino/*.cpp "$CORE/libraries/Wire/src/Wire.cpp"; do
  o="$B/$(basename "$f").o"; avr-g++ $CXXFLAGS -c "$f" -o "$o"; objs+=("$o"); done
for f in "$CORE"/cores/arduino/*.S; do
  [ -e "$f" ] || continue; o="$B/$(basename "$f").o"; avr-gcc $MCU -x assembler-with-cpp -c "$f" -o "$o"; objs+=("$o"); done

avr-gcc -Os -Wl,--gc-sections $MCU "$B/sketch.o" "${objs[@]}" -lm -o "$B/Nixie_RevC.elf"
avr-objcopy -O ihex -R .eeprom "$B/Nixie_RevC.elf" "$B/Nixie_RevC.hex"
echo "--- size (ATmega328P: 30720 B flash with bootloader, 2048 B RAM) ---"
avr-size -A "$B/Nixie_RevC.elf" | awk '/^.text|^.data|^.bss/'
TEXT=$(avr-size -A "$B/Nixie_RevC.elf" | awk '/^.text/{t=$2} /^.data/{d=$2} END{print t+d}')
RAM=$(avr-size -A "$B/Nixie_RevC.elf" | awk '/^.data/{d=$2} /^.bss/{b=$2} END{print d+b}')
echo "flash used: $TEXT / 30720 B   static RAM: $RAM / 2048 B"
if [ "$TEXT" -le 30720 ] && [ "$RAM" -le 1536 ]; then
  echo "AVR compile+link: PASS (avr-gcc $(avr-gcc -dumpversion), manual build, not Arduino IDE)"
  # Keep a copy of the image for flashing with avrdude (see docs/MANUFACTURING.md), with its provenance.
  OUT="$ROOT/firmware/Nixie_RevC/build"; mkdir -p "$OUT"
  cp "$B/Nixie_RevC.hex" "$OUT/Nixie_RevC.hex"
  CORE_REF="$(git -C "$CORE" rev-parse HEAD 2>/dev/null || echo unknown)"
  {
    echo "Nixie_RevC.hex - UNVALIDATED prototype firmware image (never run on a Rev C board)"
    echo "Built by scripts/avr_compile_check.sh: avr-gcc $(avr-gcc -dumpversion), ATmega328P @ 16 MHz, -Os"
    echo "Arduino AVR core: $CORE_REF (1.8.6 expected)"
    echo "Flash used: $TEXT bytes, static RAM: $RAM bytes"
    echo "SHA-256: $(sha256sum "$OUT/Nixie_RevC.hex" | cut -d' ' -f1)"
  } > "$OUT/BUILD_INFO.txt"
else
  echo "AVR compile+link: FAIL (size)"; exit 1
fi
