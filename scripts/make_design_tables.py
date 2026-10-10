#!/usr/bin/env python3
"""Generate hardware/NET_MAP.csv and hardware/COMPONENT_PLACEMENT.csv for Rev C.

These tables are DESIGN INTENT. They were written before native KiCad schematic
capture and have not been checked by KiCad ERC/DRC. When the native schematic exists,
it becomes the source of truth and this script should be retired or made to read it.

Pin numbers are given where they are stable and well known (the Arduino Nano silk
labels, the DS3231SN SOIC-16 pinout) or taken from a data sheet (HV5522 PLCC-44, status DATASHEET). Everything else is a pin NAME that must be matched
to the manufacturer's pinout during schematic capture (status column = VERIFY).
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIM = json.loads((ROOT / "cad" / "DIMENSIONS.json").read_text())

rows = []  # (net, ref, pin, pin_name, domain, status, note)


def c(net, ref, pin, pin_name, domain, status="VERIFY", note=""):
    rows.append((net, ref, pin, pin_name, domain, status, note))


# ---------------- 12 V input and protection ----------------
c("+12V_IN", "J1", "1", "12V", "LV", note="insulated DC-jack pigtail, centre positive")
c("GND", "J1", "2", "GND", "LV")
c("+12V_IN", "F1", "1", "PTC", "LV", note="Littelfuse 1812L075/33DR")
c("12V_FUSED", "F1", "2", "PTC", "LV")
c("12V_FUSED", "QP1", "D", "drain", "LV", note="reverse-polarity PMOS: input on drain")
c("V12", "QP1", "S", "source", "LV")
c("GND", "QP1", "G", "gate", "LV", note="gate to GND; check Vgs(max) vs adapter overshoot")
c("V12", "C5", "1", "+", "LV", note="47 uF 25 V radial")
c("GND", "C5", "2", "-", "LV")
c("V12", "TP2", "1", "TP", "LV")
c("GND", "TP1", "1", "TP", "LV")

# ---------------- Nano power ----------------
c("V12", "A1", "VIN", "VIN", "LV", "OK", "Nano Classic silk label")
c("GND", "A1", "GND", "GND", "LV", "OK")
c("V5", "A1", "5V", "5V", "LV", "OK")
c("V5", "TP3", "1", "TP", "LV")

# ---------------- RTC ----------------
c("V5", "U3", "2", "VCC", "LV", "OK", "DS3231SN# SOIC-16")
for p in range(5, 13):
    c("GND", "U3", str(p), "N.C. (ground per datasheet)", "LV", note="datasheet: unused pins 5-12 to ground")
c("GND", "U3", "13", "GND", "LV", "OK")
c("VBAT", "U3", "14", "VBAT", "LV", "OK")
c("I2C_SDA", "U3", "15", "SDA", "LV", "OK")
c("I2C_SCL", "U3", "16", "SCL", "LV", "OK")
c("U3_32K_NC", "U3", "1", "32kHz", "LV", "OK", "not connected")
c("U3_INT_NC", "U3", "3", "INT/SQW", "LV", "OK", "not connected")
c("U3_RST_NC", "U3", "4", "RST", "LV", "OK", "not connected (internal pull-up)")
c("V5", "C8", "1", "", "LV", note="100 nF at U3 VCC")
c("GND", "C8", "2", "", "LV")
c("VBAT", "J2", "1", "+", "LV", note="to insulated CR2032 holder (primary cell only)")
c("GND", "J2", "2", "-", "LV")
c("I2C_SDA", "A1", "A4", "A4/SDA", "LV", "OK")
c("I2C_SCL", "A1", "A5", "A5/SCL", "LV", "OK")
c("I2C_SDA", "RI1", "1", "", "LV", note="4.7 k pull-up")
c("V5", "RI1", "2", "", "LV")
c("I2C_SCL", "RI2", "1", "", "LV", note="4.7 k pull-up")
c("V5", "RI2", "2", "", "LV")

# ---------------- Buttons (INPUT_PULLUP, press = LOW) ----------------
for sw, pin, net in (("SW1", "D2", "BTN_SET"), ("SW2", "D3", "BTN_H"), ("SW3", "D4", "BTN_M")):
    c(net, "A1", pin, pin, "LV", "OK")
    c(net, sw, "1", "A", "LV", note="B3F-1062-G; pins 1-2 and 3-4 are internally paired")
    c(net, sw, "2", "A", "LV")
    c("GND", sw, "3", "B", "LV")
    c("GND", sw, "4", "B", "LV")

# ---------------- VIN sense ----------------
c("V12", "RV1", "1", "", "LV", note="47 k")
c("VIN_SENSE", "RV1", "2", "", "LV")
c("VIN_SENSE", "RV2", "1", "", "LV", note="10 k")
c("GND", "RV2", "2", "", "LV")
c("VIN_SENSE", "A1", "A1", "A1", "LV", "OK")

# ---------------- 5 V Nano logic -> 12 V HV5522 logic level shifters ----------------
# Each Nano output drives an NPN through a base resistor. The Nano never touches a driver pin.
shifters = [
    # nano pin, nano net,  Q,     Rbase, Rpd,    collector net, Rpull
    ("D13", "CLOCK_N", "QL1", "RB1", "RPD1", "DRV_CLK", "RC1"),
    ("D10", "DATA_N", "QL2", "RB2", "RPD2", "DRV_DIN", "RC2"),
    ("D9", "LATCH_N", "QL3", "RB3", "RPD3", "DRV_LE", "RC3"),
]
for pin, nnet, q, rb, rpd, cnet, rc in shifters:
    c(nnet, "A1", pin, pin, "LV", "OK")
    c(nnet, rb, "1", "", "LV", note="10 k base resistor")
    base = f"{q}_B"
    c(base, rb, "2", "", "LV")
    c(base, q, "B", "base", "LV", note="MMBT3904")
    c(base, rpd, "1", "", "LV", note="100 k base pull-down: off while Nano is in reset")
    c("GND", rpd, "2", "", "LV")
    c("GND", q, "E", "emitter", "LV")
    c(cnet, q, "C", "collector", "LOGIC12", note="inverting: Nano HIGH -> driver input LOW")
    c(cnet, rc, "1", "", "LOGIC12", note="10 k pull-up to V12")
    c("V12", rc, "2", "", "LOGIC12")

# RUN -> BL: two stages (QL4 NPN + QL5 PNP) so the default with the Nano in reset is BLANKED.
c("RUN", "A1", "D6", "D6", "LV", "OK")
c("RUN", "RB4", "1", "", "LV", note="10 k")
c("QL4_B", "RB4", "2", "", "LV")
c("QL4_B", "QL4", "B", "base", "LV", note="MMBT3904")
c("QL4_B", "RPD4", "1", "", "LV", note="100 k pull-down")
c("GND", "RPD4", "2", "", "LV")
c("GND", "QL4", "E", "emitter", "LV")
c("QL4_C", "QL4", "C", "collector", "LOGIC12")
c("QL4_C", "RB6", "1", "", "LOGIC12", note="10 k")
c("QL5_B", "RB6", "2", "", "LOGIC12")
c("QL5_B", "QL5", "B", "base", "LOGIC12", note="MMBT3906")
c("QL5_B", "RPU5", "1", "", "LOGIC12", note="100 k base pull-up: PNP off by default")
c("V12", "RPU5", "2", "", "LOGIC12")
c("V12", "QL5", "E", "emitter", "LOGIC12")
c("DRV_BL", "QL5", "C", "collector", "LOGIC12", note="RUN HIGH -> BL HIGH (outputs enabled)")
c("DRV_BL", "RD1", "1", "", "LOGIC12", note="10 k pull-down: BL LOW = blanked by default")
c("GND", "RD1", "2", "", "LOGIC12")

# ---------------- HV5522 drivers ----------------
# PLCC-44 (PJ) pin numbers from the Supertex/Microchip HV5522 data sheet:
#   30..44 = HVOUT1..HVOUT15, 1..17 = HVOUT16..HVOUT32, 18 DATA OUT, 19-21 and 29 N/C,
#   22 POL, 23 CLK, 24 VSS, 25 VDD, 26 LE, 27 DATA IN, 28 BL.
# Function table: POL HIGH + BL LOW = all outputs OFF; POL LOW + BL LOW = all outputs ON.
# POL is therefore hard-tied to VDD so that the default-low BL line blanks the tubes.
HV5522_PIN = {"DOUT": "18", "POL": "22", "CLK": "23", "VSS": "24", "VDD": "25", "LE": "26", "DIN": "27", "BL": "28"}
for o in range(1, 33):
    HV5522_PIN[f"HVOUT{o}"] = str(29 + o) if o <= 15 else str(o - 15)
DS_NOTE = "pin number from HV5522 data sheet; re-check against current Microchip DS20005699"
for u, cvdd, cbulk in (("U1", "C1", "C3"), ("U2", "C2", "C4")):
    c("V12", u, HV5522_PIN["VDD"], "VDD", "LOGIC12", "DATASHEET", DS_NOTE)
    c("GND", u, HV5522_PIN["VSS"], "VSS", "LOGIC12", "DATASHEET")
    c("DRV_CLK", u, HV5522_PIN["CLK"], "CLK", "LOGIC12", "DATASHEET", "data shifts on CLK falling edge")
    c("DRV_LE", u, HV5522_PIN["LE"], "LE", "LOGIC12", "DATASHEET", "latches load while LE is HIGH")
    c("DRV_BL", u, HV5522_PIN["BL"], "BL", "LOGIC12", "DATASHEET", "BL LOW + POL HIGH = all outputs OFF")
    c("V12", u, HV5522_PIN["POL"], "POL", "LOGIC12", "DATASHEET", "SAFETY: POL tied HIGH; POL LOW + BL LOW would turn every cathode ON")
    for nc in ("19", "20", "21", "29"):
        c(f"{u}_NC{nc}", u, nc, "N/C", "LOGIC12", "DATASHEET", "not connected")
    c("V12", cvdd, "1", "", "LOGIC12", note="100 nF at VDD")
    c("GND", cvdd, "2", "", "LOGIC12")
    c("V12", cbulk, "1", "", "LOGIC12", note="10 uF 0805, rated >=25 V")
    c("GND", cbulk, "2", "", "LOGIC12")
c("DRV_DIN", "U1", HV5522_PIN["DIN"], "DATA IN", "LOGIC12", "DATASHEET")
c("DRV_CHAIN", "U1", HV5522_PIN["DOUT"], "DATA OUT", "LOGIC12", "DATASHEET", "U1 DATA OUT -> U2 DATA IN")
c("DRV_CHAIN", "U2", HV5522_PIN["DIN"], "DATA IN", "LOGIC12", "DATASHEET")
c("U2_DOUT_NC", "U2", HV5522_PIN["DOUT"], "DATA OUT", "LOGIC12", "DATASHEET", "not connected")

# ---------------- HV enable and converter ----------------
c("HV_EN", "A1", "D7", "D7", "LV", "OK")
c("HV_EN", "RB5", "1", "", "LV", note="10 k")
c("QE1_B", "RB5", "2", "", "LV")
c("QE1_B", "QE1", "B", "base", "LV", note="MMBT3904")
c("QE1_B", "RPD5", "1", "", "LV", note="100 k pull-down: HV off while Nano is in reset")
c("GND", "RPD5", "2", "", "LV")
c("GND", "QE1", "E", "emitter", "LV")
c("HV_GATE", "QE1", "C", "collector", "LV")
c("HV_GATE", "QP2", "G", "gate", "LV", note="DMP3098L-7 high-side switch, default OFF")
c("HV_GATE", "RGP", "1", "", "LV", note="100 k gate pull-up to source")
c("HV_ARMED_12V", "RGP", "2", "", "LV")
c("V12", "JP1", "1", "HV_ARM", "LV", note="remove shunt = converter input open (NOT proof of discharge)")
c("HV_ARMED_12V", "JP1", "2", "HV_ARM", "LV")
c("HV_ARMED_12V", "QP2", "S", "source", "LV")
c("HV_IN_12V", "QP2", "D", "drain", "LV")
c("HV_IN_12V", "C6", "1", "", "LV", note="10 uF 1210, rated >=25 V")
c("GND", "C6", "2", "", "LV")
# NCH8200HV v2.1 data sheet: pins VIN, GND, VOUT, GND, GND; input 2.5-15 V; fixed ~170 V out;
# no enable pin, no reverse-polarity protection, no documented current limit (QP2 is the enable).
c("HV_IN_12V", "PS1", "1", "VIN", "LV", note="NCH8200HV: pin order per data sheet; confirm on the module you receive")
c("GND", "PS1", "2", "GND", "LV")
c("HV170", "PS1", "3", "VOUT", "HV")
c("GND", "PS1", "4", "GND", "LV")
c("GND", "PS1", "5", "GND", "LV")

# ---------------- HV rail: storage, bleeder, sense ----------------
c("HV170", "CHV", "1", "", "HV", note="100 nF >=250 V 1210, <=3 mm tall")
c("GND", "CHV", "2", "", "HV")
c("HV170", "TP4", "1", "TP", "HV", note="HV test pad: measure only per SAFETY.md")
c("HV170", "RH1", "1", "", "HV", note="110 k 1206 >=0.5 W >=200 V bleeder")
c("HV_BLEED_MID", "RH1", "2", "", "HV")
c("HV_BLEED_MID", "RH2", "1", "", "HV")
c("GND", "RH2", "2", "", "HV")
c("HV170", "RS1", "1", "", "HV", note="1 M 1206 >=200 V")
c("HV_SENSE_MID", "RS1", "2", "", "HV")
c("HV_SENSE_MID", "RS2", "1", "", "HV")
c("HV_SENSE", "RS2", "2", "", "HV")
c("HV_SENSE", "RS3", "1", "", "LV", note="22 k 0805 (NOT an anode resistor)")
c("GND", "RS3", "2", "", "LV")
c("HV_SENSE", "C7", "1", "", "LV", note="10 nF filter")
c("GND", "C7", "2", "", "LV")
c("HV_SENSE", "A1", "A0", "A0", "LV", "OK")

# ---------------- Tubes, anode resistors, cathodes ----------------
for t in range(1, 7):
    ra = f"RA{t}"
    c("HV170", ra, "1", "", "HV", note="22 k 1% 1 W PR01 axial - safety item")
    c(f"ANODE{t}", ra, "2", "", "HV")
    c(f"ANODE{t}", f"T{t}", "A", "anode", "HV", note="IN-14 direct solder, factory spacer kept")
    bank = "U1" if t <= 3 else "U2"
    slot = (t - 1) % 3
    for d in range(10):
        out = 1 + slot * 10 + d
        net = f"T{t}_K{d}"
        c(net, f"T{t}", f"K{d}", f"cathode {d}", "HV")
        c(net, bank, HV5522_PIN[f"HVOUT{out}"], f"HVOUT{out}", "HV", "DATASHEET")
    c(f"T{t}_LDP_NC", f"T{t}", "LDP", "left decimal point", "HV", note="not connected")
    c(f"T{t}_RDP_NC", f"T{t}", "RDP", "right decimal point", "HV", note="not connected")

for l, rl, bank in ((1, "RL1", "U1"), (2, "RL2", "U2")):
    c("HV170", rl, "1", "", "HV", note="220 k 1% 1 W PR01 axial")
    c(f"LAMP{l}_A", rl, "2", "", "HV")
    c(f"LAMP{l}_A", f"L{l}", "1", "lead", "HV", note="NE-2: sleeve both leads >=300 V (600 V preferred)")
    c(f"SEP{l}_K", f"L{l}", "2", "lead", "HV")
    c(f"SEP{l}_K", bank, HV5522_PIN["HVOUT31"], "HVOUT31", "HV", "DATASHEET")
    c(f"{bank}_OUT32_NC", bank, HV5522_PIN["HVOUT32"], "HVOUT32", "HV", "DATASHEET", "unused, never set")

with open(ROOT / "hardware" / "NET_MAP.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["net", "ref", "pin", "pin_name", "domain", "status", "note"])
    for r in rows:
        w.writerow(r)

# ---------------- Planning placement (enclosure coordinates) ----------------
P = []  # ref, value, footprint_intent, side, x, y, rot_deg, note


def p(ref, value, fp, side, x, y, rot=0, note="planning position"):
    P.append((ref, value, fp, side, x, y, rot, note))


for i, (x, y) in enumerate(DIM["tube_centers"], 1):
    p(f"T{i}", "IN-14", "local:IN-14_direct_solder", "top", x, y, 0, "fixed by enclosure; numerals face -Y (front)")
for i, (x, y) in enumerate(DIM["separator_centers"], 1):
    p(f"L{i}", "NE-2 / VCC A1A", "local:NE2_upright_sleeved", "top", x, y, 0, "fixed by enclosure")
for i, (name, (x, y)) in enumerate(DIM["buttons"].items(), 1):
    p(f"SW{i}", f"B3F-1062-G ({name})", "Button_Switch_THT:SW_PUSH_6mm", "top", x, y, 0, "fixed by enclosure")
for i, (x, y) in enumerate(DIM["pcb_screws"], 1):
    p(f"H{i}", "M2 mounting hole", "MountingHole:MountingHole_2.2mm_M2", "both", x, y, 0, "fixed by enclosure")

# Bottom side. Tube and lamp leads come through the board, so bottom parts keep clear of a
# 14 mm circle under each tube (checked as a courtyard by native KiCad DRC in make_kicad.py).
bottom = [
    ("U1", "HV5522PJ-G", "Package_LCC:PLCC-44", 80, 18),
    ("U2", "HV5522PJ-G", "Package_LCC:PLCC-44", 152, 18),
    ("A1", "Arduino Nano Classic A000005", "Module:Arduino_Nano (2x 1x15 headers, 6 mm)", 40, 58),
    ("PS1", "NCH8200HV", "Nixie_RevC:PLACEHOLDER_NCH8200HV_30x21 (size VERIFY)", 125, 58),
    ("U3", "DS3231SN#", "Package_SO:SOIC-16W_7.5x10.3mm", 186, 18),
    ("F1", "1812L075/33DR", "Fuse:Fuse_1812", 211, 67),
    ("QP1", "DMP3098L-7", "Package_TO_SOT_SMD:SOT-23", 211, 61),
    ("QP2", "DMP3098L-7", "Package_TO_SOT_SMD:SOT-23", 100, 50),
    ("J1", "12 V pigtail pads", "Nixie_RevC:WirePads_2 (to author)", 204, 67),
    ("J2", "CR2032 lead pads", "Nixie_RevC:WirePads_2 (to author)", 224, 45),
    ("C5", "47 uF 25 V radial", "Capacitor_THT:CP_Radial_D6.3mm_P2.50mm", 196, 60),
    ("C6", "10 uF 1210", "Capacitor_SMD:C_1210", 100, 54),
    ("CHV", "100 nF >=250 V 1210", "Capacitor_SMD:C_1210", 145, 50),
    ("RH1", "110 k 1206 >=0.5 W", "Resistor_SMD:R_1206", 145, 54),
    ("RH2", "110 k 1206 >=0.5 W", "Resistor_SMD:R_1206", 145, 58),
    ("RS1", "1 M 1206", "Resistor_SMD:R_1206", 149, 50),
    ("RS2", "1 M 1206", "Resistor_SMD:R_1206", 149, 54),
    ("RS3", "22 k 0805", "Resistor_SMD:R_0805", 149, 58),
    ("C7", "10 nF 0805", "Capacitor_SMD:C_0805", 149, 62),
]
for ref, val, fp, x, y in bottom:
    p(ref, val, fp, "bottom", x, y)
for t, (x, y) in enumerate(DIM["tube_centers"], 1):
    p(f"RA{t}", "22 k 1% 1 W PR01", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "bottom", x + 10, y, 90, "HV: keep >=2 mm creepage from LV nets")
for l, (x, y) in enumerate(DIM["separator_centers"], 1):
    p(f"RL{l}", "220 k 1% 1 W PR01", "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal", "bottom", x + 4, y, 90)
small = [
    ("C1", "100 nF 0805", 93, 12), ("C3", "10 uF 0805", 93, 16), ("C2", "100 nF 0805", 165, 12), ("C4", "10 uF 0805", 165, 16),
    ("C8", "100 nF 0805", 186, 27), ("RI1", "4.7 k 0805", 196, 12), ("RI2", "4.7 k 0805", 196, 16),
    ("RV1", "47 k 0805", 66, 50), ("RV2", "10 k 0805", 66, 54),
    # level shifters, Nano side -> 12 V driver side (group A between U1 and H2)
    ("QL1", "MMBT3904", 97, 11), ("RB1", "10 k 0805", 101, 11), ("RPD1", "100 k 0805", 105, 11), ("RC1", "10 k 0805", 109, 11),
    ("QL2", "MMBT3904", 97, 15), ("RB2", "10 k 0805", 101, 15), ("RPD2", "100 k 0805", 105, 15), ("RC2", "10 k 0805", 109, 15),
    ("QL3", "MMBT3904", 97, 19), ("RB3", "10 k 0805", 101, 19), ("RPD3", "100 k 0805", 105, 19), ("RC3", "10 k 0805", 109, 19),
    ("QL4", "MMBT3904", 97, 23), ("RB4", "10 k 0805", 101, 23), ("RPD4", "100 k 0805", 105, 23), ("RD1", "10 k 0805", 109, 23),
    # group B between H2 and U2: blanking PNP stage
    ("QL5", "MMBT3906", 123, 11), ("RB6", "10 k 0805", 127, 11), ("RPU5", "100 k 0805", 131, 11),
    # HV enable, next to the converter input switch
    ("QE1", "MMBT3904", 96, 62), ("RB5", "10 k 0805", 100, 62), ("RPD5", "100 k 0805", 104, 62), ("RGP", "100 k 0805", 104, 50),
]
# Service items on the TOP side along the rear edge: with the case lifted off the chassis you can measure
# TP4 against TP1 and pull the HV_ARM shunt without reaching under the board (enclosed case).
for ref, val, fp, x, y in (("JP1", "1x2 header + shunt (HV_ARM)", "Connector_PinHeader_2.54mm:PinHeader_1x02", 90, 66),
                           ("TP1", "GND", "TestPoint:TestPoint_Pad_D1.5mm", 100, 68), ("TP4", "HV170", "TestPoint:TestPoint_Pad_D1.5mm", 106, 68),
                           ("TP2", "V12", "TestPoint:TestPoint_Pad_D1.5mm", 180, 68), ("TP3", "V5", "TestPoint:TestPoint_Pad_D1.5mm", 186, 68)):
    p(ref, val, fp, "top", x, y, 0, "top-side service access with the case lifted off")
for ref, val, x, y in small:
    fp = ("Resistor_SMD:R_0805" if ref.startswith("R") else "Capacitor_SMD:C_0805" if ref.startswith("C")
          else "Package_TO_SOT_SMD:SOT-23" if ref.startswith("Q") else "TestPoint:TestPoint_Pad_D1.5mm")
    p(ref, val, fp, "bottom", x, y)

with open(ROOT / "hardware" / "COMPONENT_PLACEMENT.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ref", "value", "footprint_intent", "side", "x_mm", "y_mm", "rot_deg", "note"])
    for r in P:
        w.writerow(r)

print(f"NET_MAP.csv: {len(rows)} connections; COMPONENT_PLACEMENT.csv: {len(P)} parts")
