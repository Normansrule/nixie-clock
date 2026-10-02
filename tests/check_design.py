#!/usr/bin/env python3
"""Custom consistency checks on the Rev C design tables and enclosure dimensions.

This is NOT native KiCad ERC or DRC. It checks that NET_MAP.csv, COMPONENT_PLACEMENT.csv,
docs/BOM.md quantities and cad/DIMENSIONS.json agree with each other and with the
safety invariants that can be expressed as table rules. Passing it proves nothing about
a real schematic, board, or powered circuit.
"""
import csv
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIM = json.loads((ROOT / "cad" / "DIMENSIONS.json").read_text())
net_rows = list(csv.DictReader(open(ROOT / "hardware" / "NET_MAP.csv")))
place = list(csv.DictReader(open(ROOT / "hardware" / "COMPONENT_PLACEMENT.csv")))

results = []


def rule(name, ok, detail=""):
    results.append((name, bool(ok), detail))


refs = {p["ref"]: p for p in place}
nets = defaultdict(list)
for r in net_rows:
    nets[r["net"]].append((r["ref"], r["pin"]))

# --- Fitted quantities by BOM line (Rev C fitted qty) ---
expected = {
    "IN-14": 6, "NE-2 / VCC A1A": 2, "HV5522PJ-G": 2, "Arduino Nano Classic A000005": 1, "DS3231SN#": 1,
    "NCH8200HV": 1, "1812L075/33DR": 1, "DMP3098L-7": 2, "MMBT3904": 5, "MMBT3906": 1,
    "22 k 1% 1 W PR01": 6, "220 k 1% 1 W PR01": 2, "110 k 1206 >=0.5 W": 2, "1 M 1206": 2,
    "100 k 0805": 7, "10 k 0805": 11, "22 k 0805": 1, "47 k 0805": 1, "4.7 k 0805": 2,
    "100 nF 0805": 3, "10 uF 0805": 2, "47 uF 25 V radial": 1, "10 uF 1210": 1, "100 nF >=250 V 1210": 1, "10 nF 0805": 1,
}
vals = Counter(p["value"].split(" (")[0] for p in place)
for v, n in expected.items():
    rule(f"fitted qty {v} = {n}", vals[v] == n, f"found {vals[v]}")
rule("three B3F-1062-G switches", sum(p["value"].startswith("B3F-1062-G") for p in place) == 3)

# --- Every net-map reference is placed ---
missing = sorted({r["ref"] for r in net_rows} - set(refs))
rule("every NET_MAP ref has a placement row", not missing, ", ".join(missing))
unused = sorted(set(refs) - {r["ref"] for r in net_rows} - {f"H{i}" for i in range(1, 6)})
rule("every placed part (except mounting holes) appears in NET_MAP", not unused, ", ".join(unused))

# --- Safety invariant: Nano pins never share a net with an HV5522 pin ---
nano_nets = {r["net"] for r in net_rows if r["ref"] == "A1" and r["pin"] not in ("VIN", "GND", "5V")}
bad = sorted(n for n in nano_nets if any(ref in ("U1", "U2") for ref, _ in nets[n]))
rule("no Nano pin is on the same net as an HV5522 pin (level shifting present)", not bad, ", ".join(bad))
rule("HV5522 POL tied HIGH on both drivers (BL LOW then blanks)", all(any(r["ref"] == u and r["pin_name"] == "POL" and r["net"] == "V12" for r in net_rows) for u in ("U1", "U2")))
pins_used = Counter((r["ref"], r["pin"]) for r in net_rows)
dup = [k for k, n in pins_used.items() if n > 1]
rule("no pin appears on two nets", not dup, str(dup[:5]))
rule("all 44 PLCC pins of U1 and U2 are assigned", all(len({r["pin"] for r in net_rows if r["ref"] == u}) == 44 for u in ("U1", "U2")))
for n in ("DRV_CLK", "DRV_DIN", "DRV_LE", "DRV_BL"):
    rule(f"{n} has a pull resistor to V12 or GND", any(ref.startswith(("RC", "RD")) for ref, _ in nets[n]))

# --- Startup blanking / default-off: pull-downs on every Nano-driven transistor base ---
for base in ("QL1_B", "QL2_B", "QL3_B", "QL4_B", "QE1_B"):
    rule(f"{base} has a 100 k pull-down to GND", any(ref.startswith("RPD") for ref, _ in nets[base]))
rule("DRV_BL defaults LOW through RD1 (blanked while Nano is in reset)", ("RD1", "1") in nets["DRV_BL"])
rule("QP2 gate pulled to its source (HV converter off by default)", ("RGP", "1") in nets["HV_GATE"])
rule("HV_ARM header sits in series with the converter input", ("JP1", "1") in nets["V12"] and ("JP1", "2") in nets["HV_ARMED_12V"])

# --- One active digit per tube is a firmware rule; hardware rule: one cathode per driver output ---
for u in ("U1", "U2"):
    for o in range(1, 33):
        ns = [r["net"] for r in net_rows if r["ref"] == u and r["pin_name"] == f"HVOUT{o}"]
        rule(f"{u} OUT{o} on exactly one net", len(ns) == 1)
        if not ns:
            continue
        others = [ref for ref, _ in nets[ns[0]] if ref != u]
        if o <= 30:
            ok = len(others) == 1 and others[0].startswith("T")
        elif o == 31:
            ok = len(others) == 1 and others[0].startswith("L")
        else:
            ok = len(others) == 0
        if not ok:
            rule(f"{u} OUT{o} connects to the right element", False, str(others))
for t in range(1, 7):
    bank = "U1" if t <= 3 else "U2"
    rule(f"T{t} cathodes all on {bank}", all(any(ref == bank for ref, _ in nets[f"T{t}_K{d}"]) for d in range(10)))
    rule(f"T{t} anode goes through RA{t}", ("RA" + str(t), "2") in nets[f"ANODE{t}"])

# --- HV rail parts ---
for part in ["CHV", "RH1", "RS1", "PS1", "TP4"] + [f"RA{t}" for t in range(1, 7)] + ["RL1", "RL2"]:
    rule(f"{part} on HV170", any(ref == part for ref, _ in nets["HV170"]))
rule("bleeder chain RH1-RH2 reaches GND", ("RH2", "2") in nets["GND"])
rule("HV sense ends at A0 with RS3 to GND", ("A1", "A0") in nets["HV_SENSE"] and ("RS3", "2") in nets["GND"])

# --- Placement: parts on the PCB, top side reserved for tubes / lamps / buttons ---
x0, y0 = DIM["pcb_offset_x"], DIM["pcb_offset_y"]
x1, y1 = x0 + DIM["pcb_l"], y0 + DIM["pcb_w"]
off = [p["ref"] for p in place if not (x0 < float(p["x_mm"]) < x1 and y0 < float(p["y_mm"]) < y1)]
rule("all placement points inside the PCB outline", not off, ", ".join(off))
top = sorted(p["ref"] for p in place if p["side"] == "top")
rule("top side carries only tubes, lamps and buttons", all(r[0] in "TLS" for r in top), ", ".join(top))

# --- Enclosure geometry ---
tubes = DIM["tube_centers"]
rule("tube pitch pairs match (30 mm within a pair)", all(tubes[i + 1][0] - tubes[i][0] == 30 for i in (0, 2, 4)))
rule("separators centred between pairs", [s[0] for s in DIM["separator_centers"]] == [(tubes[1][0] + tubes[2][0]) / 2, (tubes[3][0] + tubes[4][0]) / 2])
r_open = DIM["tube_opening_d"] / 2
holes = [(x, y, r_open) for x, y in tubes] + [(x, y, DIM["separator_opening_d"] / 2) for x, y in DIM["separator_centers"]]
holes += [(x, y, DIM["button_opening_d"] / 2) for x, y in DIM["buttons"].values()]
posts = [(x, y, DIM["pcb_post_d"] / 2) for x, y in DIM["pcb_screws"]]
min_gap = min(math.dist(a[:2], b[:2]) - a[2] - b[2] for i, a in enumerate(holes + posts) for b in (holes + posts)[i + 1:])
rule("openings and PCB posts do not overlap (min web >= 1.5 mm)", min_gap >= 1.5, f"min web {min_gap:.2f} mm")
inner = DIM["wall_t"]
edge = min(min(x - r, y - r, DIM["base_l"] - x - r, DIM["base_w"] - y - r) for x, y, r in holes)
rule("top openings clear the side walls", edge > inner, f"{edge:.1f} mm from outer edge")
rule("glass fits the opening (nominal)", DIM["tube_glass_d"] < DIM["tube_opening_d"])
rule("button protrudes above the top (7 mm tall switch)", DIM["pcb_top_z"] + DIM["button_height_above_pcb"] > DIM["base_h"])
gap_all = DIM["base_h"] - DIM["top_t"] - DIM["pcb_top_z"]
rule("PCB top to hood underside leaves room for the top-side budget", gap_all >= DIM["top_side_height_budget"], f"{gap_all} mm")
eng_printed = 6 - DIM["pcb_t"]
eng_clear = 4 - DIM["pcb_t"]
post_len = DIM["base_h"] - DIM["top_t"] - DIM["pcb_top_z"]
rule("all-printed M2x6 PCB screw stays inside post + top skin", eng_printed < post_len + DIM["top_t"] - 0.5, f"{eng_printed} mm into {post_len + DIM['top_t']} mm")
rule("clear-top M2x4 PCB screw stops below the acrylic", eng_clear <= post_len, f"{eng_clear} mm into {post_len} mm post")
rule("clear-top M2x6 PCB screw WOULD strike the acrylic (why M2x4)", eng_printed > post_len, f"{eng_printed} mm vs {post_len} mm")
co = DIM["rear_cable_opening_z"] - DIM["rear_cable_opening_d"] / 2
rule("rear cable opening sits above the floor", co > DIM["floor_t"], f"bottom edge z={co}")
f = DIM["fasteners"]
rule("all-printed set = 4x M2x8 + 7x M2x6", f["all_printed"]["M2x8"] == 4 and f["all_printed"]["M2x6"] == 7)
rule("clear-top set = 4x M2x8 + 5x M2x4 + 6x M2x6", (f["clear_top"]["M2x8"], f["clear_top"]["M2x4"], f["clear_top"]["M2x6"]) == (4, 5, 6))

w = max(len(n) for n, _, _ in results)
fails = 0
for n, ok, d in results:
    if not ok or "-v" in sys.argv:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{w}}  {d}")
    fails += not ok
print(f"{len(results) - fails}/{len(results)} custom design checks passed (custom Python checks, not KiCad ERC/DRC)")
sys.exit(1 if fails else 0)
