# Validation status (Rev C)

**Rev C is an UNVALIDATED ENGINEERING PROTOTYPE, not a fabrication release.** No Gerbers or drill files are shipped. This page keeps two lists apart on purpose:

- **Recorded checks**: things a script or tool did to the *files* in this repository. They show the files are self-consistent. They are **not** independent proof that the circuit, the board or the enclosure works.
- **Physical checks**: things that can only be done with real parts, a real board and a meter. **None of these has been done.**

## Recorded checks (repeat with `scripts/run_all_checks.sh`)

| Check | Tool | Result on 2026-09-30 | What it does *not* show |
|---|---|---|---|
| Equation arithmetic (38 checks, including the sealed-case temperature) | `tests/check_equations.py` | 38 / 38 pass | That the real tubes, converter or resistors behave like the model |
| Design-table consistency (150 checks): BOM counts, no Nano pin on a driver net, pull-ups/pull-downs present, POL tied high, one cathode per driver output, placement inside the board, fastener lengths | `tests/check_design.py` (**custom Python, not KiCad DRC**) | 150 / 150 pass | Electrical correctness of the design; anything about copper |
| Requirements and BOM (traceability, safety ratings in BOM.csv, bed fit, files exist) | `tests/check_requirements.py` (**custom Python**) | 142 / 142 pass | Whether the requirements are met by real hardware |
| Fabrication release gate | `scripts/make_fab_outputs.sh` | Refuses (no routed board): correct | Anything about a future board |
| Firmware display core on a PC (383 checks), including every displayable time producing a one-digit-per-tube frame | `g++` + `tests/test_display_core.cpp` | 383 / 383 pass | That the bit order, polarity and clock edge match the real HV5522 |
| Firmware compile and link for ATmega328P | `scripts/avr_compile_check.sh`: avr-gcc 7.3.0 against ArduinoCore-avr 1.8.6, **manual build, not the Arduino IDE** | Pass: 13 712 B flash, 844 B static RAM, no sketch warnings with `-Wall -Wextra` | That the IDE build is identical, that it uploads, or that it runs correctly |
| Schematic encodes the net map | `scripts/make_kicad.py`: **native** `kicad-cli 7.0.11 sch export netlist`, compared net by net with `NET_MAP.csv` | 106 / 106 nets match, no extra nets | ERC; readability; whether the net map itself is right. **Native ERC has not been run** |
| Placement board | `scripts/make_kicad.py`: **native** pcbnew 7.0.11 DRC on `Nixie_RevC_placement.kicad_pcb` (outline, 5 M2 holes, placeholder courtyards on both sides, no copper) | 0 violations | Anything about routing, clearances, copper or real footprints |
| Desktop app (Nixie Clock Companion 1.0.0) | electron-builder 26.15.3 / Electron 44.5.1, Linux AppImage and `.deb` packaged; app launched on a virtual display (Xvfb) with Playwright: pages load, calculator matches EQUATIONS.md, Web Serial present, no page errors | Pass on Linux x64 | Windows and macOS builds (made by CI at release, not yet run); any real serial session with a Nano |
| Enclosure computer-aided design (CAD) model | `tests/check_cad.py`: OpenCASCADE booleans between every alarm-clock case part and nominal envelopes of the PCB, glass, spacers, lamps and switches, plus enclosure rules (tubes fully inside, window fully glazed, rod and cable gaps, build volume) | 86 / 86 pass | Physical fit of real, printed parts and real tubes |

Reports: `hardware/reports/SUMMARY.txt`, `hardware/reports/placement_native_drc.rpt`, `hardware/reports/netlist_vs_netmap.txt`, `cad/BUILD_REPORT.txt`.

## Physical checks: all NOT established

| Item | Status | Stage |
|---|---|---|
| Native KiCad electrical rules check (ERC) on a human-reviewed schematic | NOT DONE | Before Stage 1 |
| Routed 4-layer board with native design rules check (DRC) under `Nixie_RevC.kicad_dru` | NOT DONE (board not routed) | Before Stage 1 |
| Experienced HV layout review, then Gerbers | NOT DONE | Before Stage 1 |
| Arduino integrated development environment (IDE) compile and upload to a real Nano | NOT DONE | 2 |
| Printed fit: coupons, case, floor, button rods, window panel, screws | NOT DONE | 0, 6 |
| Low-voltage power-up, reverse polarity, logic levels, blanking default | NOT DONE | 1, 2 |
| HV bring-up, sense accuracy, **measured discharge** | NOT DONE | 3 |
| Digit mapping, per-digit current, converter loading | NOT DONE | 4 |
| Closed-case thermal margin | NOT DONE | 5 |
| Any safety compliance or certification | NOT CLAIMED | — |

## Untested assumptions

Each of these is a number or behaviour the design relies on and that nobody has measured on Rev C hardware.

1. IN-14 bulb is about 19 × 55 mm (Tube-Tester) on 7 mm factory spacers; the case leaves about 23 mm above the glass. Real tubes vary.
2. IN-14 lead pattern (13 leads) is a **placeholder**: 12.0 mm circle, 1.0 mm holes. Measure your tubes.
3. IN-14 maintaining voltage about 145 V; typical current 2.5 mA. With 22 kΩ at 170 V the model gives about 1.1 mA.
4. NE-2 maintaining voltage about 60 V.
4a. IN-14 ignition (strike) voltage is commonly quoted as up to about 170 V; it was not confirmed from a primary source here. On a fixed 170 V rail that leaves little margin: check that every digit strikes reliably, including from cold. The firmware's 150 V floor is a fault limit, not an operating point.
5. NCH8200HV: output fixed at about 170 V, 2.5–15 V input, 30 mA peak, pin order VIN, GND, VOUT, GND, GND, **internal output capacitance unknown** (the discharge model assumes 1 µF). Module outline unknown: the placement board reserves 30 × 21 mm.
6. HV5522PJ-G function table (POL HIGH + BL LOW = all off; with POL HIGH and BL HIGH, a register 1 = output on), shift direction (HVOUT1 → HVOUT32), falling-edge clock, LE HIGH loads latches, VDD 10.8–13.2 V (the firmware's VIN window stops at 13.2 V for this reason), PLCC pin numbers: taken from the Supertex-era HV5522 data sheet. Recheck against Microchip DS20005699.
7. DS3231SN pins 5–12 should be grounded.
8. Omron B3F-1062-G body about 3.5 mm tall and 6 × 6 mm.
9. Nano's 5 V rail is the ADC reference, accurate to a few percent.
10. All printed fit allowances marked VERIFY in `cad/DIMENSIONS.json`.

## Open items

These came out of the recorded checks and are deliberately left visible rather than fixed silently.

- **Anode resistor fault power.** If the full 170 V rail appears across one 22 kΩ resistor (a shorted tube or cathode path), it dissipates 1.31 W, above its 1 W rating. The NCH8200HV data sheet documents no current limit. Options for a future revision: a 2 W part or two 11 kΩ 1 W in series, a current-limited HV supply, or an HV fuse. Rev C keeps the brief's 22 kΩ 1 W values.
- **Tube current well below typical.** The 22 kΩ start value predicts about 45 % of the IN-14's typical 2.5 mA. Measure at Stage 4 before deciding anything.
- **Enclosure changed from the brief: alarm-clock case.** At the builder's request the low base with tubes standing out of it (and its two options, printed hood or acrylic top) was replaced by one fully enclosed case: tubes inside, a captive 3 mm smoked acrylic window, buttons pressed from the top through printed rods, and the PCB carried on floor standoffs. This removes the 0.2 mm ring gaps around the tubes and the need to pass glass through openings. Fasteners are now one set (4 × M2 × 8, 7 × M2 × 6). Test pads TP1–TP4 and the HV_ARM header moved to the top side so they can be reached with the case lifted off.
- **Button rods (new, unverified).** Each rod rests on its switch by its own weight (about 0.03 N against a 1.47 N actuation force) with about 1 mm of free travel above the 0.25 mm switch travel. The height chain (standoffs, PCB, switch, roof) has not been measured; coupon 06 and Stage 6 check it.
- **Window retention.** The panel rests on the floor and is held in its slot by three silicone dots, so it stays in the case when the case is lifted. Without the silicone it would drop out onto the tubes.
- **Sealed case, no vents.** Kept closed on purpose so HV stays enclosed. The model predicts an average internal rise of about 3–5 K at about 2.7 W ([EQUATIONS.md](EQUATIONS.md#7-sealed-case-temperature)); local hot spots (the Nano's regulator, PS1) are checked at Stage 5.
- **Case printing.** The case prints upright and needs tree supports inside under the roof and in the window opening; support removal around the window slot must leave the slot clean (see [PRINTING.md](PRINTING.md)).
- **USB back-feed.** The converter can start from 2.5 V. With the shunt fitted and only USB connected, back-feed through the Nano could, in principle, reach it if QP2 were on. Firmware refuses HV below 10.8 V VIN, and the flashing procedure removes the shunt; Stage 2 checks that `HV_IN_12V` stays near 0 V whenever HV is not requested.
- **Serial monitor resets the Nano.** Opening the serial monitor resets the board. The firmware therefore latches HV faults in EEPROM; it does not rely on the Nano staying powered. Confirmed in code only; Stage 2 checks it on a board.
- **Bottom-side keep-out above the cable clamp.** Parts under the clamp region near the rear opening must stay below about 11 mm.
- **Nano classic bootloader and the watchdog.** Some older Nano bootloaders hang after a watchdog reset. With the pins high-impedance the clock simply stays dark and HV stays off (safe), but it will not restart until power-cycled. Record which bootloader your Nano has.

## Build log (fill in)

| Date | Stage | Builder | Reviewer | Measurement | Value | PASS/FIX/STOP | Notes |
|---|---|---|---|---|---|---|---|
| | 0 | | | glass diameters T1–T6 | | | |
| | 0 | | | real IN-14 lead circle | | | |
| | 1 | | | TP2, TP3, reverse polarity | | | |
| | 2 | | | IDE / core / compiler versions | | | |
| | 2 | | | DRV_BL and HV_GATE in reset | | | |
| | 3 | | | TP4 running; firmware HV reading | | | |
| | 3 | | | TP4 at 1 s / 5 s / 60 s after off | | | |
| | 4 | | | per-digit current (attach table) | | | |
| | 4 | | | supply current, all lit | | | |
| | 5 | | | regulator / PS1 / RA temps after 2 h | | | |
| | 6 | | | enclosure fit, gaps | | | |
