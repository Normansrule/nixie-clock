#!/usr/bin/env python3
"""Recorded geometry checks on the CadQuery model (source/build_cad.py).

Interference volumes between enclosure parts and the non-printable envelopes
(PCB, glass, lamps, buttons) computed with OpenCASCADE booleans. These are checks of the
MODEL against NOMINAL dimensions. They are not a physical fit test: real tubes, boards,
printers and acrylic vary. See docs/VALIDATION.md.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
import build_cad as B  # noqa: E402

env = B.pcb_mechanical()
parts = {n: fn() for n, (fn, _) in B.PARTS.items()}
results = []


def vol_int(a, b):
    try:
        return a.intersect(b).val().Volume()
    except Exception:
        return 0.0


def check(name, v, limit=0.01):
    results.append((name, v <= limit, v))


glass = [v for k, v in env.items() if k.startswith(("glass", "lamp"))]
for enc in ("01_printed_hood", "04_optional_acrylic_frame", "05_optional_top_plate_3mm", "02_bottom_cover", "03_cable_clamp"):
    check(f"{enc} vs PCB board", vol_int(parts[enc], env["PCB"]))
    check(f"{enc} vs glass/lamp envelopes", sum(vol_int(parts[enc], g) for g in glass))
    check(f"{enc} vs tube spacers", sum(vol_int(parts[enc], v) for k, v in env.items() if k.startswith("spacer")))
    check(f"{enc} vs button bodies", sum(vol_int(parts[enc], v) for k, v in env.items() if k.startswith("button")))
check("hood vs bottom cover", vol_int(parts["01_printed_hood"], parts["02_bottom_cover"]))
check("frame vs bottom cover", vol_int(parts["04_optional_acrylic_frame"], parts["02_bottom_cover"]))
check("frame vs 3 mm top", vol_int(parts["04_optional_acrylic_frame"], parts["05_optional_top_plate_3mm"]))
check("clamp vs bottom cover", vol_int(parts["03_cable_clamp"], parts["02_bottom_cover"]))
for n, p in parts.items():
    results.append((f"{n} is one valid solid", p.val().isValid() and len(p.solids().vals()) == 1, len(p.solids().vals())))

# Button tops must rise above the enclosure top so they can be pressed.
btn_top = max(v.val().BoundingBox().zmax for k, v in env.items() if k.startswith("button"))
results.append(("button plunger above top surface", btn_top > B.BASE_H, btn_top))

w = max(len(r[0]) for r in results)
fails = 0
for name, ok, v in results:
    print(f"{'PASS' if ok else 'FAIL'}  {name:<{w}}  {v:.3f}")
    fails += not ok
print(f"{len(results) - fails}/{len(results)} recorded geometry checks passed (model vs nominal envelopes, not a physical fit)")
sys.exit(1 if fails else 0)
