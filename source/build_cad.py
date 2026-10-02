#!/usr/bin/env python3
"""build_cad.py - CadQuery model of record for the Rev C Six-Tube Nixie Clock enclosure.

Every dimension comes from cad/DIMENSIONS.json. Values listed under "_verify" there are
fit allowances or third-party dimensions that have NOT been checked against real parts.

Outputs (regenerate with scripts/render_cad):
  cad/step/NN_part.step      each part in ENCLOSURE (assembly) coordinates - for CAD reference
  cad/stl/NN_part.stl        each printable part in PRINT orientation - for the slicer
  cad/3mf/NN_part.3mf        same as stl/, 3MF container
  cad/print/plate_*.3mf      suggested print plates (one enclosure option per plate)
  cad/Assembly_RevC_all_printed.step, cad/Assembly_RevC_clear_top.step
  cad/PCB_mechanical_RevC.step   board outline, holes, glass/lamp/button envelopes (NOT printable)
  cad/Acrylic_top_3mm_1to1.dxf   laser-cut outline for the 3 mm cast-acrylic top (1:1, mm)

Never print glass_*, PCB or envelope bodies. Never slice the step/ files: they are in
assembly coordinates, not print orientation.
"""
import json
import math
import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "cad" / "DIMENSIONS.json").read_text())

# ---------------- Named variables (all from DIMENSIONS.json) ----------------
BASE_L, BASE_W, BASE_H = D["base_l"], D["base_w"], D["base_h"]
CORNER_R = D["corner_r"]
WALL_T, TOP_T, FLOOR_T = D["wall_t"], D["top_t"], D["floor_t"]
FLOOR_CLEAR = D["floor_clearance"]                    # VERIFY
PCB_L, PCB_W, PCB_T = D["pcb_l"], D["pcb_w"], D["pcb_t"]
PCB_X, PCB_Y, PCB_TOP_Z = D["pcb_offset_x"], D["pcb_offset_y"], D["pcb_top_z"]
TUBES = [tuple(p) for p in D["tube_centers"]]
SEPS = [tuple(p) for p in D["separator_centers"]]
BUTTONS = {k: tuple(v) for k, v in D["buttons"].items()}
PCB_SCREWS = [tuple(p) for p in D["pcb_screws"]]
CASE_SCREWS = [tuple(p) for p in D["case_screws"]]
TUBE_HOLE_D = D["tube_opening_d"]                      # VERIFY
SEP_HOLE_D = D["separator_opening_d"]                  # VERIFY
BTN_HOLE_D = D["button_opening_d"]                     # VERIFY
BTN_H = D["button_height_above_pcb"]                   # VERIFY
BTN_BODY, BTN_BODY_H = D["button_body"], D["button_body_h"]  # VERIFY
BTN_POCKET, BTN_POCKET_DEPTH = D["button_pocket"], D["button_pocket_depth"]  # VERIFY
ACR_BTN_HOLE_D = D["acrylic_button_hole_d"]            # VERIFY
CABLE_HOLE_D = D["rear_cable_opening_d"]               # VERIFY
CABLE_HOLE_X, CABLE_HOLE_Z = D["rear_cable_opening_x"], D["rear_cable_opening_z"]
GLASS_D, GLASS_H, SPACER_H = D["tube_glass_d"], D["tube_glass_h"], D["tube_spacer_h"]  # VERIFY
BAFFLE_T = D["baffle_wall_t"]
BAFFLE_GAP = D["baffle_bottom_gap_above_pcb"]
POST_D = D["pcb_post_d"]
PILOT_D = D["m2_pilot_d"]                              # VERIFY (tap M2 after the coupon)
CLEAR_D = D["m2_clearance_d"]                          # VERIFY
CBORE_D, CBORE_H = D["m2_head_counterbore_d"], D["m2_head_counterbore_depth"]  # VERIFY
ACR_T = D["acrylic_t"]
ACR_CLEAR = D["acrylic_pocket_clearance"]              # VERIFY
LEDGE_W, LEDGE_T = D["acrylic_ledge_w"], D["acrylic_ledge_t"]
CLAMP_SCREWS = [tuple(p) for p in D["clamp_screws"]]
CLAMP_BOSS_D, CLAMP_BOSS_H = D["clamp_boss_d"], D["clamp_boss_h"]
CLAMP_L, CLAMP_W, CLAMP_BAR_T = D["clamp_len"], D["clamp_w"], D["clamp_bar_t"]
CABLE_D, CABLE_PINCH = D["cable_d"], D["cable_pinch"]  # VERIFY
LEAD_N, LEAD_CIRCLE_D, LEAD_HOLE_D = D["in14_lead_count"], D["in14_lead_circle_d"], D["in14_lead_hole_d"]  # VERIFY

# Derived
TOP_UNDER_Z = BASE_H - TOP_T                  # underside of hood top / acrylic seat (27)
PCB_BOT_Z = PCB_TOP_Z - PCB_T                 # 22.4
POST_LEN = TOP_UNDER_Z - PCB_TOP_Z            # 3.0
BAFFLE_BOT_Z = PCB_TOP_Z + BAFFLE_GAP         # 25.0
CORNER_BLOCK = 12.0                           # corner block reach from each corner (mm)
CRADLE_H = CABLE_HOLE_Z - CABLE_D / 2 - FLOOR_T   # floor pad so the cable lines up with the rear hole
CLAMP_UNDER_Z = FLOOR_T + CRADLE_H + CABLE_D - CABLE_PINCH
CLAMP_TOP_Z = CLAMP_UNDER_Z + CLAMP_BAR_T
CLAMP_CBORE_H = 3.0
BOTTOM_PILOT_DEPTH = 10.0
TOP_PILOT_DEPTH = POST_LEN  # M2x6 through 3 mm acrylic = 3 mm engagement


def rrect(l, w, r, h, x0=0.0, y0=0.0, z0=0.0):
    """Rounded rectangle prism with its min corner at (x0, y0, z0)."""
    s = cq.Workplane("XY").box(l, w, h, centered=False).edges("|Z").fillet(r)
    return s.translate((x0, y0, z0))


def cyl(d, h, x, y, z0):
    return cq.Workplane("XY").circle(d / 2).extrude(h).translate((x, y, z0))


def inner_outline(h, z0, inset):
    return rrect(BASE_L - 2 * inset, BASE_W - 2 * inset, CORNER_R - inset, h, inset, inset, z0)


def corner_blocks(z0, z1):
    """Solid corner fillers inside the walls that carry the case-screw pilots."""
    cav = inner_outline(z1 - z0, z0, WALL_T)
    out = None
    for cx, cy in CASE_SCREWS:
        bx = 0 if cx < BASE_L / 2 else BASE_L - CORNER_BLOCK
        by = 0 if cy < BASE_W / 2 else BASE_W - CORNER_BLOCK
        blk = cq.Workplane("XY").box(CORNER_BLOCK, CORNER_BLOCK, z1 - z0, centered=False).translate((bx, by, z0)).intersect(cav)
        out = blk if out is None else out.union(blk)
    return out


def top_openings(z0, h, btn_d=None):
    btn_d = BTN_HOLE_D if btn_d is None else btn_d
    cut = None
    for x, y in TUBES:
        c = cyl(TUBE_HOLE_D, h, x, y, z0)
        cut = c if cut is None else cut.union(c)
    for x, y in SEPS:
        cut = cut.union(cyl(SEP_HOLE_D, h, x, y, z0))
    for x, y in BUTTONS.values():
        cut = cut.union(cyl(btn_d, h, x, y, z0))
    return cut


def rear_cable_hole():
    return (cq.Workplane("XZ").circle(CABLE_HOLE_D / 2).extrude(-WALL_T * 3)
            .translate((CABLE_HOLE_X, BASE_W - WALL_T * 1.5, CABLE_HOLE_Z)))


# ---------------- 01 printed hood (all-printed option) ----------------
def printed_hood():
    body = rrect(BASE_L, BASE_W, CORNER_R, BASE_H).cut(inner_outline(TOP_UNDER_Z, 0, WALL_T))
    body = body.union(corner_blocks(FLOOR_T, PCB_BOT_Z - 0.5))   # stop below the PCB corners
    # HV baffle collars around tube and lamp openings: block line of sight to leads.
    for x, y in TUBES:
        body = body.union(cyl(TUBE_HOLE_D + 2 * BAFFLE_T, TOP_UNDER_Z - BAFFLE_BOT_Z, x, y, BAFFLE_BOT_Z))
    for x, y in SEPS:
        body = body.union(cyl(SEP_HOLE_D + 2 * BAFFLE_T, TOP_UNDER_Z - BAFFLE_BOT_Z, x, y, BAFFLE_BOT_Z))
    for x, y in PCB_SCREWS:
        body = body.union(cyl(POST_D, POST_LEN, x, y, PCB_TOP_Z))
    body = body.cut(top_openings(BAFFLE_BOT_Z - 1, BASE_H))
    for x, y in BUTTONS.values():   # underside pocket: the switch body is taller than the 3 mm gap
        body = body.cut(cq.Workplane("XY").box(BTN_POCKET, BTN_POCKET, BTN_POCKET_DEPTH + 0.01).translate(
            (x, y, TOP_UNDER_Z + (BTN_POCKET_DEPTH - 0.01) / 2)))
    for x, y in PCB_SCREWS:   # blind pilot, 1 mm skin left on the visible top
        body = body.cut(cyl(PILOT_D, BASE_H - 1.0 - PCB_TOP_Z, x, y, PCB_TOP_Z))
    for x, y in CASE_SCREWS:
        body = body.cut(cyl(PILOT_D, BOTTOM_PILOT_DEPTH, x, y, FLOOR_T))
    return body.cut(rear_cable_hole())


# ---------------- 04 optional acrylic frame (clear-top option) ----------------
def acrylic_frame():
    body = rrect(BASE_L, BASE_W, CORNER_R, BASE_H).cut(inner_outline(BASE_H, 0, WALL_T))
    # Seat ledge under the acrylic. Its underside is chamfered at ~45 degrees (stepped in
    # 0.25 mm increments) so the ledge itself prints upright without supports.
    ledge_h = LEDGE_T + LEDGE_W
    z0 = TOP_UNDER_Z - ledge_h
    body = body.union(inner_outline(ledge_h, z0, WALL_T).cut(inner_outline(ledge_h, z0, WALL_T + LEDGE_W)))
    steps = 16
    for i in range(steps):
        body = body.cut(inner_outline(LEDGE_W / steps + 0.002, z0 + i * LEDGE_W / steps - 0.001,
                                      WALL_T + (i + 1) * LEDGE_W / steps))
    # Corner blocks: below the PCB for the bottom screws, above the PCB for the top screws.
    body = body.union(corner_blocks(FLOOR_T, PCB_BOT_Z - 0.5)).union(corner_blocks(PCB_TOP_Z, TOP_UNDER_Z))
    for x, y in PCB_SCREWS:
        body = body.union(cyl(POST_D, POST_LEN, x, y, PCB_TOP_Z))
        if CORNER_BLOCK < x < BASE_L - CORNER_BLOCK:
            # mid-wall boss: rib back to the nearest wall at post height (needs a support when printing)
            y0, y1 = (WALL_T - 0.5, y) if y < BASE_W / 2 else (y, BASE_W - WALL_T + 0.5)
            body = body.union(cq.Workplane("XY").box(POST_D, y1 - y0, POST_LEN, centered=False)
                              .translate((x - POST_D / 2, y0, PCB_TOP_Z)))
    for x, y in PCB_SCREWS:
        body = body.cut(cyl(PILOT_D, POST_LEN + 0.01, x, y, PCB_TOP_Z - 0.005))
    for x, y in CASE_SCREWS:
        body = body.cut(cyl(PILOT_D, BOTTOM_PILOT_DEPTH, x, y, FLOOR_T))
        body = body.cut(cyl(PILOT_D, TOP_PILOT_DEPTH, x, y, TOP_UNDER_Z - TOP_PILOT_DEPTH))
    return body.cut(rear_cable_hole())


# ---------------- 05 optional 3 mm top plate (print alternative to acrylic) ----------------
def top_plate():
    inset = WALL_T + ACR_CLEAR
    plate = inner_outline(ACR_T, TOP_UNDER_Z, inset)
    plate = plate.cut(top_openings(TOP_UNDER_Z - 1, ACR_T + 2, ACR_BTN_HOLE_D))
    for x, y in CASE_SCREWS:
        plate = plate.cut(cyl(CLEAR_D, ACR_T + 2, x, y, TOP_UNDER_Z - 1))
    return plate


# ---------------- 02 bottom cover (shared by both options) ----------------
def bottom_cover():
    inset = WALL_T + FLOOR_CLEAR
    cover = inner_outline(FLOOR_T, 0, inset)
    for x, y in CLAMP_SCREWS:
        cover = cover.union(cyl(CLAMP_BOSS_D, CLAMP_BOSS_H, x, y, FLOOR_T))
    cx = (CLAMP_SCREWS[0][0] + CLAMP_SCREWS[1][0]) / 2
    cover = cover.union(cq.Workplane("XY").box(10, CLAMP_W + 4, CRADLE_H, centered=False)
                        .translate((cx - 5, CLAMP_SCREWS[0][1] - (CLAMP_W + 4) / 2, FLOOR_T)))
    for x, y in CASE_SCREWS:
        cover = cover.cut(cyl(CLEAR_D, FLOOR_T + 1, x, y, -0.5))
        cover = cover.cut(cyl(CBORE_D, CBORE_H, x, y, -0.001))
    for x, y in CLAMP_SCREWS:
        cover = cover.cut(cyl(PILOT_D, FLOOR_T + CLAMP_BOSS_H - 0.6, x, y, 0.6))
    return cover


# ---------------- 03 cable clamp (low-voltage strain relief) ----------------
def cable_clamp():
    (x0, y0), (x1, _) = CLAMP_SCREWS
    cx = (x0 + x1) / 2
    z_leg = FLOOR_T + CLAMP_BOSS_H
    bar = cq.Workplane("XY").box(CLAMP_L, CLAMP_W, CLAMP_BAR_T, centered=False).translate((cx - CLAMP_L / 2, y0 - CLAMP_W / 2, CLAMP_UNDER_Z))
    clamp = bar
    for x, _ in CLAMP_SCREWS:
        clamp = clamp.union(cq.Workplane("XY").box(CLAMP_BOSS_D + 1, CLAMP_W, CLAMP_UNDER_Z - z_leg, centered=False)
                            .translate((x - (CLAMP_BOSS_D + 1) / 2, y0 - CLAMP_W / 2, z_leg)))
    for x, y in CLAMP_SCREWS:
        clamp = clamp.cut(cyl(CLEAR_D, CLAMP_TOP_Z - z_leg + 1, x, y, z_leg - 0.5))
        clamp = clamp.cut(cyl(CBORE_D, CLAMP_CBORE_H + 0.01, x, y, CLAMP_TOP_Z - CLAMP_CBORE_H))
    return clamp


# ---------------- 06 fit coupon ----------------
def fit_coupon():
    c = rrect(84, 34, 4, TOP_T)
    c = c.union(cyl(TUBE_HOLE_D + 2 * BAFFLE_T, TOP_UNDER_Z - BAFFLE_BOT_Z, 16, 17, TOP_T))
    c = c.union(cyl(POST_D, POST_LEN, 58, 9, TOP_T))
    c = c.union(cq.Workplane("XY").box(9, 9, BOTTOM_PILOT_DEPTH + 2, centered=False).translate((68, 12.5, TOP_T)))
    c = c.cut(cyl(TUBE_HOLE_D, 20, 16, 17, -1))
    c = c.cut(cyl(SEP_HOLE_D, 10, 36, 17, -1))
    c = c.cut(cyl(BTN_HOLE_D, 10, 48, 17, -1))
    c = c.cut(cq.Workplane("XY").box(BTN_POCKET, BTN_POCKET, BTN_POCKET_DEPTH + 0.01).translate((48, 17, TOP_T - (BTN_POCKET_DEPTH - 0.01) / 2)))
    c = c.cut(cyl(PILOT_D, POST_LEN + TOP_T - 1, 58, 9, 1))        # PCB-post pilot (tap M2)
    c = c.cut(cyl(CLEAR_D, 10, 58, 25, -1))                        # M2 clearance
    c = c.cut(cyl(PILOT_D, BOTTOM_PILOT_DEPTH, 72.5, 17, TOP_T + 2))  # case-screw pilot, from the top
    # index notch so you know which way up the coupon was printed
    return c.cut(cq.Workplane("XY").box(4, 2, TOP_T + 2, centered=False).translate((0, 0, -1)))


# ---------------- 07 unpowered lead-pattern coupon ----------------
def lead_coupon():
    c = cq.Workplane("XY").circle(14).extrude(2.0)
    for i in range(LEAD_N):
        a = 2 * math.pi * i / LEAD_N
        c = c.cut(cyl(LEAD_HOLE_D, 4, LEAD_CIRCLE_D / 2 * math.cos(a), LEAD_CIRCLE_D / 2 * math.sin(a), -1))
    # "never powered" marker: a slot through the rim
    return c.cut(cq.Workplane("XY").box(6, 2, 4, centered=False).translate((10, -1, -1)))


# ---------------- Non-printable envelopes ----------------
def pcb_mechanical():
    board = cq.Workplane("XY").box(PCB_L, PCB_W, PCB_T, centered=False).translate((PCB_X, PCB_Y, PCB_BOT_Z))
    for x, y in PCB_SCREWS:
        board = board.cut(cyl(2.2, PCB_T + 2, x, y, PCB_BOT_Z - 1))
    parts = {"PCB": board}
    for i, (x, y) in enumerate(TUBES, 1):
        parts[f"glass_{i}"] = cyl(GLASS_D, GLASS_H, x, y, PCB_TOP_Z + SPACER_H)
        parts[f"spacer_{i}"] = cyl(12, SPACER_H, x, y, PCB_TOP_Z)
    for i, (x, y) in enumerate(SEPS, 1):
        parts[f"lamp_{i}"] = cyl(6.35, 13, x, y, PCB_TOP_Z + 1)
    for k, (x, y) in BUTTONS.items():
        b = (cq.Workplane("XY").box(BTN_BODY, BTN_BODY, BTN_BODY_H).translate((x, y, PCB_TOP_Z + BTN_BODY_H / 2))
             .union(cyl(3.5, BTN_H - BTN_BODY_H, x, y, PCB_TOP_Z + BTN_BODY_H)))
        parts[f"button_{k}"] = b
    return parts


def print_orient(shape, flip):
    s = shape.rotate((0, 0, 0), (1, 0, 0), 180) if flip else shape
    bb = s.val().BoundingBox()
    return s.translate((-bb.xmin, -bb.ymin, -bb.zmin))


PARTS = {
    # name: (builder, flip for printing)
    "01_printed_hood": (printed_hood, True),
    "02_bottom_cover": (bottom_cover, False),
    "03_cable_clamp": (cable_clamp, True),
    "04_optional_acrylic_frame": (acrylic_frame, False),
    "05_optional_top_plate_3mm": (top_plate, False),
    "06_fit_coupon": (fit_coupon, False),
    "07_unpowered_lead_pattern_coupon": (lead_coupon, False),
}


def write_dxf(path):
    """1:1 laser-cut outline for the 3 mm acrylic top, drawn with exact lines and arcs."""
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    doc.layers.add("CUT", color=1)
    doc.layers.add("NOTES", color=7)
    i = WALL_T + ACR_CLEAR
    x0, y0, x1, y1, r = i, i, BASE_L - i, BASE_W - i, CORNER_R - i
    cut = {"layer": "CUT"}
    msp.add_line((x0 + r, y0), (x1 - r, y0), dxfattribs=cut)
    msp.add_line((x1, y0 + r), (x1, y1 - r), dxfattribs=cut)
    msp.add_line((x1 - r, y1), (x0 + r, y1), dxfattribs=cut)
    msp.add_line((x0, y1 - r), (x0, y0 + r), dxfattribs=cut)
    msp.add_arc((x1 - r, y0 + r), r, 270, 0, dxfattribs=cut)
    msp.add_arc((x1 - r, y1 - r), r, 0, 90, dxfattribs=cut)
    msp.add_arc((x0 + r, y1 - r), r, 90, 180, dxfattribs=cut)
    msp.add_arc((x0 + r, y0 + r), r, 180, 270, dxfattribs=cut)
    for x, y in TUBES:
        msp.add_circle((x, y), TUBE_HOLE_D / 2, dxfattribs=cut)
    for x, y in SEPS:
        msp.add_circle((x, y), SEP_HOLE_D / 2, dxfattribs=cut)
    for x, y in BUTTONS.values():
        msp.add_circle((x, y), ACR_BTN_HOLE_D / 2, dxfattribs=cut)
    for x, y in CASE_SCREWS:
        msp.add_circle((x, y), CLEAR_D / 2, dxfattribs=cut)
    msp.add_text("Rev C acrylic top, 3 mm clear CAST acrylic, 1:1 mm, enclosure coordinates. VERIFY scale before cutting.",
                 height=2.5, dxfattribs={"layer": "NOTES"}).set_placement((x0, y1 + 6))
    doc.saveas(path)
    return (x1 - x0, y1 - y0)


def main(out=ROOT / "cad"):
    for sub in ("step", "stl", "3mf", "print"):
        (out / sub).mkdir(parents=True, exist_ok=True)
    built = {}
    report = []
    for name, (fn, flip) in PARTS.items():
        shp = fn()
        solid = shp.val()
        assert solid.isValid(), f"{name} is not a valid solid"
        built[name] = shp
        cq.exporters.export(shp, str(out / "step" / f"{name}.step"))
        po = print_orient(shp, flip)
        cq.exporters.export(po, str(out / "stl" / f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(po, str(out / "3mf" / f"{name}.3mf"), tolerance=0.02, angularTolerance=0.1)
        bb = po.val().BoundingBox()
        report.append(f"{name:36s} print bbox {bb.xlen:6.1f} x {bb.ylen:5.1f} x {bb.zlen:5.1f} mm  volume {solid.Volume() / 1000:6.1f} cm3")

    env = pcb_mechanical()
    colors = {"PCB": (0.1, 0.35, 0.15), "glass": (0.9, 0.55, 0.2, 0.35), "spacer": (0.2, 0.2, 0.2),
              "lamp": (1.0, 0.45, 0.1, 0.6), "button": (0.3, 0.3, 0.3)}
    pcb_asm = cq.Assembly(name="PCB_mechanical_RevC")
    for k, v in env.items():
        pcb_asm.add(v, name=k, color=cq.Color(*colors[k.split("_")[0]]))
    pcb_asm.export(str(out / "PCB_mechanical_RevC.step"))

    for option, parts in (("all_printed", ["01_printed_hood", "02_bottom_cover", "03_cable_clamp"]),
                          ("clear_top", ["04_optional_acrylic_frame", "05_optional_top_plate_3mm", "02_bottom_cover", "03_cable_clamp"])):
        asm = cq.Assembly(name=f"Assembly_RevC_{option}")
        for p in parts:
            col = cq.Color(0.75, 0.9, 1.0, 0.3) if p.startswith("05") else cq.Color(0.12, 0.12, 0.13)
            asm.add(built[p], name=p, color=col)
        asm.add(pcb_asm, name="PCB_mechanical")
        asm.export(str(out / f"Assembly_RevC_{option}.step"))

    # Print plates (one enclosure option per plate). Parts are spaced along Y.
    def plate(names, fname):
        y = 0.0
        shapes = []
        for n in names:
            fn, flip = PARTS[n]
            po = print_orient(built[n], flip)
            bb = po.val().BoundingBox()
            shapes.append(po.translate((0, y, 0)).val())
            y += bb.ylen + 8
        cq.exporters.export(cq.Workplane().add(cq.Compound.makeCompound(shapes)), str(out / "print" / fname), tolerance=0.02, angularTolerance=0.1)

    plate(["06_fit_coupon", "07_unpowered_lead_pattern_coupon"], "plate_0_fit_coupons.3mf")
    plate(["01_printed_hood"], "plate_A_all_printed_hood.3mf")
    plate(["04_optional_acrylic_frame"], "plate_B_clear_top_frame.3mf")
    plate(["02_bottom_cover", "03_cable_clamp"], "plate_C_shared_floor_and_clamp.3mf")

    size = write_dxf(out / "Acrylic_top_3mm_1to1.dxf")
    report.append(f"Acrylic_top_3mm_1to1.dxf outline {size[0]:.1f} x {size[1]:.1f} mm")
    (out / "BUILD_REPORT.txt").write_text("Generated by source/build_cad.py from cad/DIMENSIONS.json\n" + "\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "cad")
