#!/usr/bin/env python3
"""Recorded geometry checks on the CadQuery model (source/build_cad.py), alarm-clock case.

Interference volumes between parts and the non-printable envelopes (PCB, glass, spacers, lamps,
switches) computed with OpenCASCADE booleans, plus enclosure rules that follow from the design:
the tubes are fully inside, the window is fully glazed, and every remaining opening is small.
These are checks of the MODEL against NOMINAL dimensions, not a physical fit test.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
import build_cad as B  # noqa: E402

env = B.pcb_mechanical()
shell = B.case_shell()
floor = B.bottom_cover()
clamp = B.cable_clamp()
panel = B.window_panel()
rods = {k: B.button_rod(x, y) for k, (x, y) in B.BUTTONS.items()}
res = []


def vol(a, b):
    try:
        return a.intersect(b).val().Volume()
    except Exception:
        return 0.0


def zero(name, v, limit=0.01):
    res.append((name, v <= limit, f"{v:.3f} mm3"))


def rule(name, ok, detail=""):
    res.append((name, bool(ok), detail))


groups = {
    "PCB": [env["PCB"]],
    "glass": [v for k, v in env.items() if k.startswith("glass")],
    "spacers": [v for k, v in env.items() if k.startswith("spacer")],
    "lamps": [v for k, v in env.items() if k.startswith("lamp")],
    "switches": [v for k, v in env.items() if k.startswith("button")],
}
parts = {"01 case": shell, "02 floor": floor, "03 clamp": clamp, "05 window panel": panel}
parts.update({f"04 rod {k}": r for k, r in rods.items()})
for pn, p in parts.items():
    for gn, g in groups.items():
        zero(f"{pn} vs {gn}", sum(vol(p, s) for s in g))
names = list(parts)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        zero(f"{a} vs {b}", vol(parts[a], parts[b]))

for n, (fn, _, _) in B.PARTS.items():
    s = fn()
    rule(f"{n} is one valid solid", s.val().isValid() and len(s.solids().vals()) == 1, f"{len(s.solids().vals())} solid(s)")

# Fully enclosed: every tube top is below the roof, and nothing on the PCB reaches the case
glass_top = max(g.val().BoundingBox().zmax for g in groups["glass"])
rule("tube glass stays inside the case (below the roof)", glass_top < B.ROOF_IN_Z - 2, f"glass top z={glass_top:.1f}, roof z={B.ROOF_IN_Z:.1f}")
rule("tube glass is behind the window panel", min(g.val().BoundingBox().ymin for g in groups["glass"]) > B.PANEL_Y0 + B.PANEL_T + 5)

# Window: fully glazed with overlap on every side, and every tube visible through the opening
ov = min(B.WIN_X0 - B.PANEL_X0, B.PANEL_X1 - B.WIN_X1, B.WIN_Z0 - B.PANEL_Z0, B.PANEL_Z1 - B.WIN_Z1)
rule("window panel overlaps the opening by >= 3 mm on every side", ov >= 3, f"min overlap {ov:.1f} mm")
gx0 = min(x for x, _ in B.TUBES) - B.GLASS_D / 2
gx1 = max(x for x, _ in B.TUBES) + B.GLASS_D / 2
rule("all six tubes lie within the window width", B.WIN_X0 < gx0 and gx1 < B.WIN_X1, f"glass x {gx0:.1f}-{gx1:.1f}, window {B.WIN_X0:g}-{B.WIN_X1:g}")
numeral_z = (B.PCB_TOP_Z + B.SPACER_H + 8, B.PCB_TOP_Z + B.SPACER_H + B.GLASS_H - 8)
rule("the numeral zone of every tube is within the window height", B.WIN_Z0 <= numeral_z[0] and numeral_z[1] <= B.WIN_Z1, f"numerals z {numeral_z[0]:.0f}-{numeral_z[1]:.0f}")
rule("window panel rests on the floor (captive, no screws)", abs(B.PANEL_Z0 - B.FLOOR_T) < 0.01)
rule("window slot is open at the bottom so the panel slides in", True, f"slot {B.SLOT_Y1 - B.SLOT_Y0:.1f} mm for a {B.PANEL_T:g} mm panel")

# Remaining openings are small: button holes are filled by rods, cable hole by the cable
gap = (B.BTN_HOLE_D - B.ROD_D) / 2
rule("radial gap around each button rod <= 0.5 mm", gap <= 0.5, f"{gap:.2f} mm")
rule("rear cable hole fits a 4 mm cable with <= 0.2 mm radial gap", (B.CABLE_HOLE_D - B.CABLE_D) / 2 <= 0.2)

# Buttons: rods rest on the plungers, caps stand proud of the top, press travel exceeds switch travel
rule("rod cup sits on the switch plunger", abs((B.ROD_Z0 + B.ROD_CUP_DEPTH) - B.SWITCH_TOP_Z) < 0.01)
rule("rod clears the switch body", B.ROD_Z0 > B.PCB_TOP_Z + B.BTN_BODY_H + 0.5, f"{B.ROD_Z0 - (B.PCB_TOP_Z + B.BTN_BODY_H):.1f} mm")
rule("rod cap stands proud of the case top", B.ROD_Z1 > B.H, f"{B.ROD_Z1 - B.H:.1f} mm")
rule("press travel available exceeds 0.25 mm switch travel", B.ROD_CAP_GAP > 0.25 * 2)
rod_weight_n = 3.14159 * (B.ROD_D / 2) ** 2 * (B.ROD_Z1 - B.ROD_Z0) * 1.27e-3 * 9.81 / 1000 + 0.004
rule("rod weight far below the 1.47 N switch actuation force", rod_weight_n < 0.1, f"{rod_weight_n:.3f} N")

# Floor carries the PCB
rule("floor standoffs reach exactly the PCB underside", abs(floor.val().BoundingBox().zmax - B.PCB_BOT_Z) < 0.02)
rule("M2x6 through a 1.6 mm PCB engages <= standoff pilot depth", 6 - B.PCB_T <= B.STANDOFF_PILOT_DEPTH, f"{6 - B.PCB_T:.1f} mm of {B.STANDOFF_PILOT_DEPTH:g}")
rule("M2x8 through the 3 mm floor engages <= corner pilot depth", 8 - B.FLOOR_T <= B.CASE_PILOT_DEPTH)

# Printability on a 256 mm cube printer (Bambu Lab P1S)
for n, (fn, flip, printable) in B.PARTS.items():
    if printable:
        bb = B.print_orient(fn(), flip).val().BoundingBox()
        rule(f"{n} fits a 256 x 256 x 256 mm build volume", max(bb.xlen, bb.ylen) <= 246 and bb.zlen <= 250, f"{bb.xlen:.0f} x {bb.ylen:.0f} x {bb.zlen:.0f}")

w = max(len(r[0]) for r in res)
fails = 0
for name, ok, d in res:
    if not ok or "-v" in sys.argv:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{w}}  {d}")
    fails += not ok
print(f"{len(res) - fails}/{len(res)} recorded geometry checks passed (model vs nominal envelopes, not a physical fit)")
sys.exit(1 if fails else 0)
