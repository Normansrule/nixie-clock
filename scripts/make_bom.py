#!/usr/bin/env python3
"""make_bom.py - machine-readable bills of materials for Rev C.

Writes:
  hardware/BOM.csv             electrical parts, grouped from COMPONENT_PLACEMENT.csv (fitted quantities)
  hardware/BOM_mechanical.csv  enclosure, fasteners and off-board items, with the enclosure option each belongs to

Quantities are FITTED quantities (one clock). Add your own spares when ordering.
Where the brief names a manufacturer part number (MPN) it is given. For generic passives the "spec" column
is the requirement; any part meeting it may be used unless "substitution" says otherwise.
Verify every package, footprint and pinout against the manufacturer's data sheet before ordering.
"""
import csv
import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware"
DIM = json.loads((ROOT / "cad" / "DIMENSIONS.json").read_text())

SAFETY = "SAFETY ITEM: same ratings or better only"
ANY = "any part meeting the spec"

# value in COMPONENT_PLACEMENT.csv -> (category, description, manufacturer, mpn_or_series, package, spec, substitution, safety_critical)
CATALOG = OrderedDict([
    ("IN-14", ("Tube", "IN-14 Nixie tube with factory spacers", "various (NOS, new old stock)", "IN-14", "13-lead direct solder", "test each tube before soldering; bulb about 19 mm", "IN-14 only (enclosure is sized for it)", "no")),
    ("NE-2 / VCC A1A", ("Lamp", "NE-2 neon lamp, separator", "VCC (Visual Communications Company)", "A1A (NE-2 type)", "wire leads", "about 60 V maintaining voltage (verify)", "NE-2 equivalent", "no")),
    ("B3F-1062-G", ("Switch", "Tactile switch 6x6 mm, 7 mm tall", "Omron", "B3F-1062-G", "THT 4-pin", "7 mm actuator height", "not the 4.3 mm B3F-1002", "no")),
    ("HV5522PJ-G", ("IC", "32-channel serial-to-parallel driver, open-drain, 220 V", "Microchip", "HV5522PJ-G", "PLCC-44", "220 V outputs, VDD 10.8-13.2 V", "not the HV5522PG-G (different package)", "yes")),
    ("Arduino Nano Classic A000005", ("Module", "Arduino Nano Classic (ATmega328P)", "Arduino", "A000005", "2x 1x15 headers, 15.24 mm row spacing", "ATmega328P, 16 MHz, 5 V", "not Nano Every or Nano ESP32", "no")),
    ("NCH8200HV", ("Module", "12 V to ~170 V DC-DC boost module", "Omnixie", "NCH8200HV", "module (outline VERIFY)", "2.5-15 V in, ~170 V out, 30 mA peak", "none without re-checking HV design", "yes")),
    ("DS3231SN#", ("IC", "Temperature-compensated real-time clock (RTC)", "Analog Devices", "DS3231SN#", "SOIC-16 wide", "+/-2 ppm 0-40 C", "DS3231SN# only (not DS3231M)", "no")),
    ("1812L075/33DR", ("Protection", "Resettable fuse (PTC, positive temperature coefficient)", "Littelfuse", "1812L075/33DR", "1812", "0.75 A hold, 33 V", SAFETY, "yes")),
    ("DMP3098L-7", ("Transistor", "P-channel MOSFET (metal-oxide-semiconductor field-effect transistor)", "Diodes Inc.", "DMP3098L-7", "SOT-23", "-30 V", "equivalent P-MOSFET only after V_GS and R_DS(on) review", "yes")),
    ("MMBT3904", ("Transistor", "NPN bipolar transistor", "onsemi or equivalent", "MMBT3904", "SOT-23", "40 V, 200 mA", ANY, "no")),
    ("MMBT3906", ("Transistor", "PNP bipolar transistor", "onsemi or equivalent", "MMBT3906", "SOT-23", "-40 V, -200 mA", ANY, "no")),
    ("1x2 header + shunt (HV_ARM)", ("Connector", "1x2 pin header + jumper shunt (HV_ARM)", "generic", "2.54 mm header + shunt", "THT 2.54 mm", "gold or tin, 2.54 mm", ANY, "yes")),
    ("12 V pigtail pads", ("Connector", "Wire pads for 12 V input pigtail", "(PCB pads)", "-", "pads", "see BOM_mechanical.csv for the pigtail", "-", "no")),
    ("CR2032 lead pads", ("Connector", "Wire pads for CR2032 holder", "(PCB pads)", "-", "pads", "see BOM_mechanical.csv for the holder", "-", "no")),
    ("22 k 1% 1 W PR01", ("Resistor", "22 kOhm 1 % 1 W axial: tube anode", "Vishay", "PR01 series, 22K0, 1 %", "axial DIN0207, 10.16 mm pitch", "1 % , 1 W, metal film", SAFETY, "yes")),
    ("220 k 1% 1 W PR01", ("Resistor", "220 kOhm 1 % 1 W axial: neon lamp", "Vishay", "PR01 series, 220K, 1 %", "axial DIN0207, 10.16 mm pitch", "1 %, 1 W", SAFETY, "yes")),
    ("110 k 1206 >=0.5 W", ("Resistor", "110 kOhm 1206: HV bleeder", "generic", "-", "1206", ">=0.5 W, >=200 V working voltage", SAFETY, "yes")),
    ("1 M 1206", ("Resistor", "1 MOhm 1206: HV sense divider top", "generic", "-", "1206", ">=0.25 W, >=200 V working voltage", SAFETY, "yes")),
    ("22 k 0805", ("Resistor", "22 kOhm 0805: HV sense bottom (NOT an anode resistor)", "generic", "-", "0805", "1 %, >=0.125 W, >=50 V", ANY, "no")),
    ("47 k 0805", ("Resistor", "47 kOhm 0805: VIN sense top", "generic", "-", "0805", "1 %, >=0.125 W, >=50 V", ANY, "no")),
    ("10 k 0805", ("Resistor", "10 kOhm 0805", "generic", "-", "0805", "1 %, >=0.125 W, >=50 V", ANY, "no")),
    ("100 k 0805", ("Resistor", "100 kOhm 0805: default-off pull-ups/pull-downs", "generic", "-", "0805", "1 %, >=0.125 W, >=50 V", ANY, "no")),
    ("4.7 k 0805", ("Resistor", "4.7 kOhm 0805: I2C pull-ups", "generic", "-", "0805", "1 %, >=0.125 W, >=50 V", ANY, "no")),
    ("100 nF 0805", ("Capacitor", "100 nF 0805 decoupling", "generic", "-", "0805", "X7R, >=25 V", ANY, "no")),
    ("10 uF 0805", ("Capacitor", "10 uF 0805 driver bulk", "generic", "-", "0805", "X5R/X7R, >=25 V (check capacitance at 12 V bias)", ANY, "no")),
    ("10 nF 0805", ("Capacitor", "10 nF 0805 HV-sense filter", "generic", "-", "0805", "X7R, >=25 V", ANY, "no")),
    ("10 uF 1210", ("Capacitor", "10 uF 1210 converter input", "generic", "-", "1210", "X5R/X7R, >=25 V", ANY, "no")),
    ("47 uF 25 V radial", ("Capacitor", "47 uF electrolytic, 12 V input bulk", "generic", "-", "radial <=6.3x8 mm, 2.5 mm pitch", "25 V, 105 C", ANY, "no")),
    ("100 nF >=250 V 1210", ("Capacitor", "100 nF HV rail capacitor (CHV)", "generic", "-", "1210, <=3 mm tall", ">=250 V, X7R", SAFETY, "yes")),
])
SKIP = {"M2 mounting hole", "GND", "V12", "V5", "HV170"}  # holes and test pads are PCB features

groups = OrderedDict()
for r in csv.DictReader(open(HW / "COMPONENT_PLACEMENT.csv")):
    v = r["value"]
    if v in SKIP:
        continue
    key = "B3F-1062-G" if v.startswith("B3F-1062-G") else v
    groups.setdefault(key, []).append(r["ref"])
missing = [k for k in groups if k not in CATALOG]
assert not missing, f"no catalog entry for {missing}"

with open(HW / "BOM.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["line", "qty", "refs", "category", "description", "manufacturer", "mpn_or_series", "package", "spec", "substitution", "safety_critical"])
    order = sorted(groups, key=lambda k: (CATALOG[k][7] != "yes", list(CATALOG).index(k)))
    for i, k in enumerate(order, 1):
        cat, desc, mfr, mpn, pkg, spec, sub, safe = CATALOG[k]
        w.writerow([i, len(groups[k]), " ".join(groups[k]), cat, desc, mfr, mpn, pkg, spec, sub, safe])

fs = DIM["fasteners"]
MECH = [
    # option, qty, item, spec, source file / note
    ("both", 1, "4-layer FR-4 printed circuit board (PCB) 218 x 64 x 1.6 mm", "NOT YET ROUTED: see docs/MANUFACTURING.md release gate", "hardware/"),
    ("both", 1, "Isolated regulated 12 V adapter, >=1 A, centre-positive 5.5 x 2.1 mm", "SAFETY ITEM: isolated, regulated, from a reputable maker", "-"),
    ("both", 1, "Insulated DC-jack pigtail, 5.5 x 2.1 mm female, about 150 mm", "outer diameter about 4 mm to suit the 4.2 mm rear hole and clamp", "-"),
    ("both", 1, "CR2032 primary lithium cell", "never a rechargeable LIR2032", "-"),
    ("both", 1, "Insulated CR2032 holder with leads", "<=30 x 25 x 7 mm", "-"),
    ("both", 2, "1x15 female headers, 2.54 mm", "Nano socket, about 6 mm stack", "-"),
    ("both", 1, "Converter mount set (stand-offs) for the NCH8200HV", "4 mm separation from the board", "-"),
    ("both", 1, "Insulation sleeving for neon leads, about 300 mm", "SAFETY ITEM: rated >=300 V, 600 V preferred", "-"),
    ("both", 2, "Cable ties, small", "wire dressing", "-"),
    ("both", 4, "Rubber feet, self-adhesive, about 8 mm", "keep clear of the four screw heads", "-"),
    ("both", 1, "USB Mini-B data cable", "data-capable, for flashing", "-"),
    ("both", 1, "PETG filament, matte", "under 200 g for either option", "-"),
    ("both", 1, "Printed part 02 bottom cover", "PETG", "cad/stl/02_bottom_cover.stl"),
    ("both", 1, "Printed part 03 cable clamp", "PETG", "cad/stl/03_cable_clamp.stl"),
    ("both", 1, "Printed part 06 fit coupon (print first)", "PETG", "cad/stl/06_fit_coupon.stl"),
    ("both", 1, "Printed part 07 unpowered lead-pattern coupon (never powered)", "PETG", "cad/stl/07_unpowered_lead_pattern_coupon.stl"),
    ("both", 1, "Printed HV warning and rating labels", "docs/labels.pdf, on the bottom cover", "docs/labels.pdf"),
    ("all_printed", 1, "Printed part 01 hood", "PETG", "cad/stl/01_printed_hood.stl"),
    ("all_printed", fs["all_printed"]["M2x8"], "M2 x 8 screw", "bottom cover", "-"),
    ("all_printed", fs["all_printed"]["M2x6"], "M2 x 6 screw", "5 PCB + 2 cable clamp", "-"),
    ("clear_top", 1, "Printed part 04 acrylic frame", "PETG", "cad/stl/04_optional_acrylic_frame.stl"),
    ("clear_top", 1, "3 mm clear CAST acrylic top, laser cut", "228.8 x 74.8 mm", "cad/Acrylic_top_3mm_1to1.dxf"),
    ("clear_top", fs["clear_top"]["M2x8"], "M2 x 8 screw", "bottom cover", "-"),
    ("clear_top", fs["clear_top"]["M2x4"], "M2 x 4 screw", "PCB (longer screws strike the acrylic)", "-"),
    ("clear_top", fs["clear_top"]["M2x6"], "M2 x 6 screw", "4 acrylic top + 2 cable clamp", "-"),
]
with open(HW / "BOM_mechanical.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["option", "qty", "item", "spec", "file"])
    for row in MECH:
        w.writerow(row)

n = sum(len(v) for v in groups.values())
print(f"BOM.csv: {len(groups)} lines, {n} fitted parts; BOM_mechanical.csv: {len(MECH)} lines")
