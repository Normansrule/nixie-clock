#!/usr/bin/env python3
"""Checks on hardware/REQUIREMENTS.csv, hardware/BOM.csv and hardware/BOM_mechanical.csv.

Custom Python checks of the files, not a physical verification.
- every requirement has a method and evidence, and the evidence file exists
- BOM.csv quantities add up to the placement table, and safety items carry their ratings
- every printed part fits a 256 x 256 mm bed (Bambu Lab P1S) with a 5 mm margin
- every file named in BOM_mechanical.csv exists
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
res = []


def rule(name, ok, detail=""):
    res.append((name, bool(ok), detail))


reqs = list(csv.DictReader(open(ROOT / "hardware" / "REQUIREMENTS.csv")))
ids = [r["id"] for r in reqs]
rule("requirement IDs are unique", len(ids) == len(set(ids)))
for r in reqs:
    rule(f"{r['id']} has a valid method", r["method"] and set(re.split(r"[ ,]+", r["method"])) <= {"I", "A", "D", "T"}, r["method"])
    rule(f"{r['id']} status is recorded or open", r["status"] in ("recorded", "open"))
    path = r["evidence"].split(" ")[0].split(",")[0]
    if "/" in path or path.endswith((".csv", ".md", ".py", ".sh")):
        p = ROOT / path if "/" in path else next(ROOT.rglob(path), None)
        rule(f"{r['id']} evidence exists ({path})", p is not None and Path(p).exists())

bom = list(csv.DictReader(open(ROOT / "hardware" / "BOM.csv")))
place = list(csv.DictReader(open(ROOT / "hardware" / "COMPONENT_PLACEMENT.csv")))
skip = {"M2 mounting hole", "GND", "V12", "V5", "HV170"}
n_place = sum(1 for p in place if p["value"] not in skip)
n_bom = sum(int(b["qty"]) for b in bom)
rule("BOM.csv quantities equal fitted parts in COMPONENT_PLACEMENT.csv", n_bom == n_place, f"{n_bom} vs {n_place}")
refs = Counter(ref for b in bom for ref in b["refs"].split())
rule("every BOM ref appears once", all(v == 1 for v in refs.values()))
by_ref = {ref: b for b in bom for ref in b["refs"].split()}
need = {"RA1": ("1 W",), "RL1": ("1 W",), "RH1": ("0.5 W", "200 V"), "RS1": ("200 V",), "CHV": ("250 V",), "F1": ("0.75 A",)}
for ref, words in need.items():
    b = by_ref.get(ref, {})
    rule(f"{ref} is marked safety-critical with its rating", b.get("safety_critical") == "yes" and all(w in b.get("spec", "") for w in words), b.get("spec", ""))

rep = (ROOT / "cad" / "BUILD_REPORT.txt").read_text()
for m in re.finditer(r"^(\S+)\s+print bbox\s+([\d.]+) x\s+([\d.]+) x\s+([\d.]+)", rep, re.M):
    x, y = float(m.group(2)), float(m.group(3))
    rule(f"{m.group(1)} fits a 256 x 256 mm bed with 5 mm margin", max(x, y) <= 246, f"{x:.0f} x {y:.0f} mm")

mech = list(csv.DictReader(open(ROOT / "hardware" / "BOM_mechanical.csv")))
for m in mech:
    if m["file"] not in ("-", "") and m["file"] != "hardware/":
        rule(f"mechanical BOM file exists: {m['file']}", (ROOT / m["file"]).exists())

w = max(len(n) for n, _, _ in res)
fails = 0
for n, ok, d in res:
    if not ok or "-v" in sys.argv:
        print(f"{'PASS' if ok else 'FAIL'}  {n:<{w}}  {d}")
    fails += not ok
print(f"{len(res) - fails}/{len(res)} requirement and BOM checks passed (custom Python checks of the files)")
sys.exit(1 if fails else 0)
