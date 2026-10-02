# Wiring, pin by pin

This page is the human-readable view of [`hardware/NET_MAP.csv`](../hardware/NET_MAP.csv) (340 connections, 106 shared nets). The net map is the source of truth; the generated KiCad schematic ([PDF](Nixie_RevC_schematic.pdf)) is checked against it by a native KiCad netlist export. **Verify every pin against the real part and board before soldering.**

![Wiring overview and shift chain](img/wiring_shift_chain.svg)

Status column in the net map: `OK` = stable, well-known pinout (Nano silk labels, DS3231SN); `DATASHEET` = taken from the HV5522 data sheet, recheck against the current Microchip revision; `VERIFY` = design intent to confirm during schematic review.

## 1. Power path

| From | Through | To | Net |
|---|---|---|---|
| 12 V adapter | J1 pad 1 (pad 2 = GND) | F1 pin 1 | `+12V_IN` |
| F1 pin 2 | QP1 drain → source (gate to GND) | V12 rail | `12V_FUSED` → `V12` |
| V12 | C5 47 µF to GND; TP2 | Nano VIN, U1/U2 VDD (pin 25), C1–C4 | `V12` |
| Nano 5V | TP3 | U3 VCC (pin 2), C8, RI1, RI2 | `V5` |
| V12 | JP1 (HV_ARM) | QP2 source, RGP | `HV_ARMED_12V` |
| QP2 drain | C6 10 µF to GND | PS1 pin 1 VIN | `HV_IN_12V` |
| PS1 pin 3 VOUT | CHV to GND; TP4 | RA1–RA6, RL1, RL2, RH1, RS1 | `HV170` |

Test pads: TP1 GND, TP2 V12, TP3 V5, TP4 HV170. PCB pads: J1 12 V in, J2 backup battery (pad 1 VBAT, pad 2 GND).

## 2. Arduino Nano (A1)

| Nano pin | Net | Goes to | Notes |
|---|---|---|---|
| D2 | `BTN_SET` | SW1 pins 1, 2 | `INPUT_PULLUP`, press = LOW |
| D3 | `BTN_H` | SW2 pins 1, 2 | |
| D4 | `BTN_M` | SW3 pins 1, 2 | Switch pins 3, 4 to GND |
| D6 | `RUN` | RB4 → QL4 → RB6 → QL5 → `DRV_BL` | HIGH = outputs enabled |
| D7 | `HV_EN` | RB5 → QE1 → `HV_GATE` (QP2 gate) | HIGH = converter input on |
| D9 | `LATCH_N` | RB3 → QL3 → `DRV_LE` | Inverted: Nano HIGH → LE LOW |
| D10 | `DATA_N` | RB2 → QL2 → `DRV_DIN` | Inverted |
| D13 | `CLOCK_N` | RB1 → QL1 → `DRV_CLK` | Inverted. D13 also drives the Nano's light-emitting diode (LED): harmless |
| A0 | `HV_SENSE` | RS2/RS3 junction, C7 | 170 V → 1.85 V |
| A1 | `VIN_SENSE` | RV1/RV2 junction | 12 V → 2.1 V; firmware window 10.8–13.2 V |
| A4 | `I2C_SDA` | U3 pin 15, RI1 | I²C (Inter-Integrated Circuit) data |
| A5 | `I2C_SCL` | U3 pin 16, RI2 | I²C clock |
| VIN / 5V / GND | `V12` / `V5` / `GND` | | |

**Rule: no Nano pin connects directly to an HV5522 pin.** The HV5522 needs logic HIGH above VDD − 2 V (about 10 V at 12 V), which a 5 V Nano cannot give, and a direct link would put the Nano on a board that carries 170 V. `tests/check_design.py` enforces this rule on the net map.

## 3. Level shifters (5 V → 12 V logic)

Each Nano output drives an NPN (bipolar, negative-positive-negative) transistor through a 10 kΩ base resistor, with a 100 kΩ pull-down so the transistor stays off while the Nano is in reset.

| Signal | Transistor | Base R / pull-down | Collector pull-up | Driver net | Default with Nano in reset |
|---|---|---|---|---|---|
| Clock | QL1 MMBT3904 | RB1 / RPD1 | RC1 10 k to V12 | `DRV_CLK` | HIGH (reset state; running idle is LOW) |
| Data | QL2 MMBT3904 | RB2 / RPD2 | RC2 | `DRV_DIN` | HIGH |
| Latch | QL3 MMBT3904 | RB3 / RPD3 | RC3 | `DRV_LE` | HIGH (latches follow the shift register, but BL is blanking) |
| Blank | QL4 MMBT3904 → QL5 MMBT3906 | RB4 / RPD4, RB6 / RPU5 | RD1 10 k **pull-down** | `DRV_BL` | **LOW = all outputs off** |
| HV enable | QE1 MMBT3904 | RB5 / RPD5 | RGP 100 k gate pull-up | `HV_GATE` | QP2 **off** |

Blanking uses two stages so that its default is LOW (blanked) rather than the HIGH that a single pulled-up inverter would give.

## 4. HV5522PJ-G drivers (U1, U2)

PLCC-44 pins, from the HV5522 data sheet: 30–44 = HVOUT1–15, 1–17 = HVOUT16–32, 18 DATA OUT, 22 POL, 23 CLK, 24 VSS, 25 VDD, 26 LE, 27 DATA IN, 28 BL, 19–21 and 29 not connected.

| Pin | U1 net | U2 net |
|---|---|---|
| 25 VDD (logic supply) / 24 VSS (ground) | `V12` / `GND` | `V12` / `GND` |
| 23 CLK | `DRV_CLK` | `DRV_CLK` |
| 26 LE | `DRV_LE` | `DRV_LE` |
| 28 BL | `DRV_BL` | `DRV_BL` |
| 22 POL | **`V12` (tied HIGH)** | **`V12`** |
| 27 DATA IN | `DRV_DIN` | `DRV_CHAIN` |
| 18 DATA OUT | `DRV_CHAIN` | not connected |

**Why POL is tied high.** In the data sheet's function table, BL LOW with POL HIGH turns every output **off**; BL LOW with POL LOW turns every output **on**. Tying POL to V12 is what makes the default-low BL line a blanking signal. If POL were ever left floating or low, a reset would light all ten digits of every tube at once.

### Driver output map

| Driver output (pin) | U1 | U2 |
|---|---|---|
| HVOUT1–10 (30–39) | T1 digits 0–9 | T4 digits 0–9 |
| HVOUT11–20 (40–44, 1–5) | T2 digits 0–9 | T5 digits 0–9 |
| HVOUT21–30 (6–15) | T3 digits 0–9 | T6 digits 0–9 |
| HVOUT31 (16) | L1 separator (via lamp) | L2 separator |
| HVOUT32 (17) | unused, never set | unused, never set |

Each IN-14 anode goes to HV170 through its own 22 kΩ resistor: T*n* anode ← RA*n*. The IN-14 left and right decimal-point cathodes are left unconnected. Each lamp: HV170 → RL*n* → lamp → driver HVOUT31.

T1 and T2 show hours, T3 and T4 minutes, T5 and T6 seconds. L1 sits between T2 and T3; L2 between T4 and T5.

### Shift order and timing

- Firmware sends 64 bits, **bit 63 first**, then pulses LE. U1 DATA OUT feeds U2 DATA IN.
- Data enters at HVOUT1 and moves toward HVOUT32, so after 64 clocks **bit 0 is U1 HVOUT1** and **bit 63 is U2 HVOUT32**. Frame bit *b* of bank *k* = HVOUT(*b* − 32*k* + 1). This is `kOutReversed = false` in `display_core.h`.
- The data sheet shifts on the CLK falling edge and loads the latches while LE is HIGH. The firmware holds data steady across the whole clock pulse, so either edge would capture it. Confirm with Stage 4 of the build guide by lighting one digit at a time.

## 5. Real-time clock (U3, DS3231SN#, SOIC-16 small-outline package)

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 32kHz | not connected | 13 GND | `GND` |
| 2 VCC | `V5` | 14 VBAT | `VBAT` (J2 pad 1 → CR2032 +) |
| 3 INT/SQW | not connected | 15 SDA | `I2C_SDA` |
| 4 RST | not connected | 16 SCL | `I2C_SCL` |
| 5–12 | `GND` (the data sheet asks for these not-connected (N.C.) pins to be grounded; **verify**) | | |

## 6. HV converter (PS1, NCH8200HV)

Pins per the v2.1 data sheet: VIN, GND, VOUT, GND, GND (numbered 1–5 here). Confirm on the module you receive. The module has **no enable pin, no reverse-polarity protection and no documented current limit**; QP2 is the enable, and QP1 plus F1 protect the input.

## 7. Off-board wiring

| Wire | From | To | Notes |
|---|---|---|---|
| 12 V pigtail | Rear 4.2 mm opening, clamped by part 03 | J1 pads | Strain relief before the solder joint |
| Battery | Insulated CR2032 holder | J2 pads | Primary CR2032 only |
| Neon leads | L1, L2 | PCB | Sleeved ≥300 V (600 V preferred) over their whole exposed length |

Dress all wires away from the HV area around PS1, the anode resistors and the tube leads, and tie them down with the two cable ties.
