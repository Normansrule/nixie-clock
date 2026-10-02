# High-voltage safety

> **About 170 volts of direct current (V DC) lives on this board whenever the high-voltage converter has run. Treat it as hazardous and potentially lethal.** Rev C is an unvalidated engineering prototype. Nobody has yet powered one and recorded the results.

This page is the rulebook. The [build guide](BUILD_GUIDE.md) points back here at every high-voltage (HV) step, and none of its gates may be skipped.

## The five rules

1. **No mains inside the clock.** Power comes only from an external, *isolated*, regulated 12 V adapter with a centre-positive 5.5 × 2.1 mm plug. The clock never touches line voltage. Do not substitute a non-isolated supply, a bench supply without current limit during bring-up, or a battery pack of unknown voltage.
2. **Off is not safe until you have measured it.** Firmware "HV off", dark tubes, unplugging the adapter and pulling the HV_ARM shunt all stop the converter. **None of them proves the HV rail (net `HV170`, test pad TP4) is discharged.** Only a meter reading does.
3. **Measure before every touch.** Before your hands, tools or probes go near the board: unplug 12 V, wait at least 60 seconds, then measure TP4 to TP1 (ground). Continue only below **10 V**. If the reading is not falling as the bleeder predicts, **STOP**: a bleeder resistor may be open, and the capacitors can hold charge for a long time.
4. **Enclosed in use; guarded during bring-up.** In normal use the clock never runs with the bottom cover off, the hood or frame removed, or with any gap that exposes HV copper, leads or the converter. The only exception is guarded bench bring-up (Stages 3 and 4 of the build guide), where the board must be measured: then it sits on an insulated surface behind a clear barrier, on a current-limited supply, with meter leads and USB connected **before** power is applied, hands off while energised, never unattended.
5. **Experienced review first.** Before the HV_ARM shunt goes in for the first time, someone experienced with high-voltage DC circuits reviews the populated board, the enclosure and your measuring setup.

## What protects you in the design, and what does not

| Protection | What it does | What it does **not** do |
|---|---|---|
| Isolated external 12 V adapter | Keeps mains out of the enclosure | Does nothing about the 170 V made inside |
| F1 resettable fuse (Positive Temperature Coefficient, PTC) | Limits a 12 V side fault | Does not limit HV current |
| QP1 reverse-polarity P-channel MOSFET (Metal-Oxide-Semiconductor Field-Effect Transistor) | Blocks a reversed plug | The converter itself has **no** reverse-polarity protection (its data sheet says so) |
| JP1 HV_ARM shunt | Physically opens the converter's 12 V input | Does not discharge anything already charged |
| QP2 high-side switch, gate pulled off | Converter stays off while the Nano is in reset or unprogrammed | A failed transistor can leave it on |
| Base pull-downs + BL pull-down + POL tied high | Tubes blanked while the Nano is in reset | Depends on the HV5522 behaving as its data sheet says: **verify** |
| 22 kΩ 1 W anode resistors, 220 kΩ 1 W lamp resistors | Set and limit current into each tube and lamp | The NCH8200HV module has no documented current limit, so a hard short can overload a 1 W resistor (see [VALIDATION.md](VALIDATION.md#open-items)) |
| RH1 + RH2 bleeder (220 kΩ total) | Discharges the HV rail in well under a second on paper | Fails silently if a resistor opens: that is why rule 3 exists |
| HV sense divider to A0 | Firmware shuts down outside 150–190 V | A reading is not a guarantee: the sensing chain can fail |
| Firmware fault latch (EEPROM) | Any HV fault keeps HV off across resets until `CLEARFAULT` | A deliberate clear by the user re-enables it |
| Firmware watchdog | A hung Nano resets, which blanks the tubes and turns HV off | Not a safety device on its own |
| Sleeving ≥300 V (600 V preferred) on neon leads | Insulates exposed lamp leads | Only if every lead is covered |

These parts are **safety items and must never be "value-engineered" away**: the 1 W anode and lamp resistors, the ≥250 V HV capacitor (CHV), the bleeders, the sleeving, the isolated adapter and the fused, reverse-protected 12 V path.

## Measuring the HV rail safely

- Use a meter rated at least Category II 600 V with intact leads. Clip the black lead to TP1 **before** power is ever applied, and use a single-hand technique: one hand behind your back or in your pocket.
- Probe TP4 only with the probe tip; never bridge TP4 to anything with a tool.
- Expected with the converter running: about 170 V (the NCH8200HV output is fixed, not adjustable, per its v2.1 data sheet).
- Expected after unplugging, with good bleeders: below 10 V within about 1 second on paper (see [EQUATIONS.md](EQUATIONS.md#3-bleeder-discharge)). Rule 3 still asks you to wait 60 seconds and measure, because the converter's internal capacitance is unknown.
- If you ever need to force a discharge, use a purpose-made discharge tool: a resistor of at least 10 kΩ, rated 5 W or more, on insulated leads. Never short the rail with a screwdriver.

## USB, the shunt and the serial monitor

The Nano's USB port sits under the bottom cover. Two situations:

- **Guarded bring-up (Stages 3–4):** USB may stay connected with the shunt fitted, but connect it before applying 12 V and never plug or unplug it while 12 V is on. Opening the serial monitor resets the Nano; the firmware keeps any HV fault latched in EEPROM across that reset, so HV cannot quietly restart after a fault. A USB isolator between the computer and the clock is a sensible extra.
- **Flashing firmware:** follow the steps below every time.

### Flashing

1. Unplug the 12 V adapter. Remove the HV_ARM shunt only after the discharge check below.
2. Wait 60 seconds, remove the bottom cover, **measure TP4 below 10 V**, then remove the HV_ARM shunt.
3. Connect USB only after that. With the shunt out, USB power cannot reach the converter. This matters because the NCH8200HV starts from as little as 2.5 V input, and USB can back-feed a few volts into the 12 V rail through the Nano's regulator.
4. Refit the shunt only when you are about to close the case for a powered test.

## Stop conditions (any of these ends the session until fixed)

- TP4 does not fall below 10 V within 60 seconds of unplugging.
- The firmware reports `HV FAULT`, `HV still ... after off`, or `unsafe frame rejected`. A fault stays latched in EEPROM until you send `CLEARFAULT`; only do that after you have measured TP4 and found the cause.
- Any smell, discoloration, crackling, visible arcing or a resistor warmer than you can comfortably hold.
- A tube shows more than one digit, or a lamp stays lit when the display should be blank.
- The 12 V adapter current rises above about 0.35 A with all digits lit (the model predicts roughly 0.25 A; see [EQUATIONS.md](EQUATIONS.md#5-12-v-input-current)).

## Who should not build this

If you are not comfortable working near high-voltage direct current, have never used a multimeter on a live circuit, or have no experienced person to review your board, do not build Rev C yet. Wait for a validated revision.
