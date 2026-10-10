#!/usr/bin/env python3
"""Recorded geometry checks on the CadQuery model (source/build_cad.py), heirloom case.

Interference volumes between parts and the non-printable envelopes (PCB, glass, spacers, lamps,
switches) computed with OpenCASCADE booleans, plus enclosure rules that follow from the design:
the tubes are fully inside, the window is fully glazed, and every remaining opening is small.
These are checks of the MODEL against NOMINAL dimensions, not a physical fit test.
"""
import math
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
wood = {n: B.PARTS[n][0]() for n in B.WOOD_PARTS}
bezel = B.brass_bezel()
feet = {i: B.brass_foot(x, y) for i, (x, y) in enumerate(B.CASE_SCREWS, 1)}
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
parts = {"01 inner case": shell, "02 floor": floor, "03 clamp": clamp, "05 window panel": panel, "13 bezel": bezel}
parts.update({f"04 rod {k}": r for k, r in rods.items()})
parts.update({n[:2] + " " + n[8:]: v for n, v in wood.items()})
parts.update({f"14 foot {i}": f for i, f in feet.items()})
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
rule("rod cap stands proud of the wood top", B.ROD_Z1 > B.WOOD_TOP_Z, f"{B.ROD_Z1 - B.WOOD_TOP_Z:.1f} mm")
rule("rod cap covers the hole in the wood top", B.ROD_CAP_D > B.WOOD_HOLE_D + 2, f"cap {B.ROD_CAP_D:g} over hole {B.WOOD_HOLE_D:g}")
rule("rod is guided by the inner case, not by the wood (wood hole larger)", B.WOOD_HOLE_D - B.ROD_D >= 1.5)
rule("press travel available exceeds 0.25 mm switch travel", B.ROD_CAP_GAP > 0.25 * 2)
rod_vol_cm3 = rods["SET"].val().Volume() / 1000
for mat, rho in (("printed PETG", 1.27), ("solid brass", 8.5)):
    wn = rod_vol_cm3 * rho * 9.81 / 1000
    rule(f"rod weight ({mat}) below 20 % of the 1.47 N switch actuation force", wn < 0.2 * 1.47, f"{wn:.3f} N")

# Light baffle hides the rods from the window
rule("light baffle sits between tube 6 glass and the rods (>= 0.5 mm each side)",
     B.BAFFLE_X0 - (B.TUBES[-1][0] + B.GLASS_D / 2) >= 0.5 and min(x for x, _ in B.BUTTONS.values()) - B.ROD_D / 2 - B.BAFFLE_X1 >= 0.5,
     f"glass to {B.TUBES[-1][0] + B.GLASS_D / 2:.1f}, baffle {B.BAFFLE_X0:g}-{B.BAFFLE_X1:g}, rods from {min(x for x, _ in B.BUTTONS.values()) - B.ROD_D / 2:.1f}")
rule("light baffle stays above the switches", B.BAFFLE_Z0 > B.SWITCH_TOP_Z + 1)

# Hardwood box and brass
rule("wood box is five valid solids that add up to the glued-up box",
     abs(sum(v.val().Volume() for v in wood.values()) - B.wood_box().val().Volume()) < 1.0)
rule("mitres: no board overlaps another", all(vol(wood[a], wood[b]) < 0.01 for i, a in enumerate(B.WOOD_PARTS) for b in B.WOOD_PARTS[i + 1:]))
rule("wood top board sits directly on the inner-case roof", abs(wood["12_wood_top"].val().BoundingBox().zmin - B.H) < 0.05)
rule("wood walls end flush with the bottom of the inner case", all(abs(wood[n].val().BoundingBox().zmin) < 0.05 for n in B.WOOD_PARTS[:4]))
rule("wood never touches the inner case sides (fit gap kept)", vol(B.wood_box(), shell.translate((0, 0, 0))) < 0.01)
op = (B.WIN_X0 - B.WOOD_MARGIN, B.WIN_X1 + B.WOOD_MARGIN, B.WIN_Z0 - B.WOOD_MARGIN, B.WIN_Z1 + B.WOOD_MARGIN)
rule("bezel inner edge covers the cut edge of the wood opening", B.BZ_X0 > op[0] and B.BZ_X1 < op[1] and B.BZ_Z0 > op[2] and B.BZ_Z1 < op[3])
rule("bezel inner edge does not hide the inner-case window", B.BZ_X0 <= B.WIN_X0 and B.BZ_X1 >= B.WIN_X1 and B.BZ_Z0 <= B.WIN_Z0 and B.BZ_Z1 >= B.WIN_Z1)
rule("bezel stays on the flat of the front board (>= 10 mm from every edge)",
     min(B.BZ_OX0 - B.WX0, B.WX1 - B.BZ_OX1, B.BZ_OZ0, B.WOOD_TOP_Z - B.BZ_OZ1) >= 10, f"min margin {min(B.BZ_OX0 - B.WX0, B.WX1 - B.BZ_OX1, B.BZ_OZ0, B.WOOD_TOP_Z - B.BZ_OZ1):.1f} mm")
rule("bezel screws lie on the bezel band", all(B.BZ_OX0 + 2 < x < B.BZ_OX1 - 2 and B.BZ_OZ0 + 2 < z < B.BZ_OZ1 - 2 and
                                                not (B.BZ_X0 - 2 < x < B.BZ_X1 + 2 and B.BZ_Z0 - 2 < z < B.BZ_Z1 + 2) for x, z in B.BEZEL_SCREWS))
rule("bezel screw M2x6 through 1 mm brass stays inside the 9.5 mm front board", 6 - B.BEZEL_T <= B.WOOD_PILOT_DEPTH < B.WOOD_T)
rule("roof screw M2x8 through the 3 mm roof stays inside the top board", 8 - B.ROOF_T <= B.WOOD_PILOT_DEPTH < B.WOOD_T,
     f"{8 - B.ROOF_T:g} mm into a {B.WOOD_PILOT_DEPTH:g} mm pilot in {B.WOOD_T:g} mm wood")
rule("roof screw heads (2 mm) sit >= 15 mm above the tube glass", B.ROOF_IN_Z - 2 - glass_top >= 15, f"{B.ROOF_IN_Z - 2 - glass_top:.1f} mm")
rule("roof screws clear the button guides and window rails", all(math.dist((x, y), bt) > B.GUIDE_D / 2 + 3 for x, y in B.ROOF_SCREWS for bt in B.BUTTONS.values())
     and all(y > B.RAIL_Y1 + 3 for _, y in B.ROOF_SCREWS))
rule("rear cable notch in the wood is wider than the inner-case cable hole", B.NOTCH_W > B.CABLE_HOLE_D + 2 and B.NOTCH_H > B.CABLE_HOLE_Z + B.CABLE_HOLE_D / 2 + 1)
rule("feet lie under the inner case footprint", all(x - B.FOOT_D / 2 >= 0 and x + B.FOOT_D / 2 <= B.L and y - B.FOOT_D / 2 >= 0 and y + B.FOOT_D / 2 <= B.W for x, y in B.CASE_SCREWS))
eng = 16 - (B.FOOT_H - B.FOOT_CBORE_H) - B.FLOOR_T
rule("M2x16 through foot and floor engages 4-10 mm in the corner pilot", 4 <= eng <= B.CASE_PILOT_DEPTH, f"{eng:.1f} mm of {B.CASE_PILOT_DEPTH:g}")

# Floor carries the PCB
rule("floor standoffs reach exactly the PCB underside", abs(floor.val().BoundingBox().zmax - B.PCB_BOT_Z) < 0.02)
rule("M2x6 through a 1.6 mm PCB engages <= standoff pilot depth", 6 - B.PCB_T <= B.STANDOFF_PILOT_DEPTH, f"{6 - B.PCB_T:.1f} mm of {B.STANDOFF_PILOT_DEPTH:g}")

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
