#!/usr/bin/env python3
"""build_cad.py - CadQuery model of record for the Rev C Six-Tube Nixie Clock, heirloom case.

The clock is FULLY ENCLOSED: the six IN-14 tubes stand on the PCB inside a printed inner case
(part 01) that carries every functional feature (window slot, button guides, floor-screw blocks)
and is seen through a front window glazed with a 3 mm smoked cast-acrylic panel. The inner case
is clad in a mitred hardwood box (parts 08-12) with a brass bezel (13) and brass feet (14).
SET, H and M are pressed from the top through button rods, alarm-clock style.
The inner case on its own is a complete, working enclosure (the "printed edition").

Assembly order (no glass ever passes through an opening):
  1. glue up the five mitred boards into the wood box; screw the brass bezel on
  2. slip the wood box over the inner case; four M2x8 up through the inner-case roof into the top board
  3. slide the window panel up into its slot inside the inner case front (from the open bottom)
  4. screw the PCB (with tubes) onto the five standoffs of the floor (part 02): the "chassis"
  5. drop the three button rods into the top holes, lower the case over the chassis,
     screw the floor on through the four brass feet

Every dimension comes from cad/DIMENSIONS.json. Keys listed under "_verify" there are unmeasured.

Outputs (regenerate with scripts/render_cad):
  cad/step/NN_part.step      each part in ENCLOSURE (assembly) coordinates - for CAD reference
  cad/stl/, cad/3mf/         each PRINTABLE part in print orientation - for the slicer
  cad/print/plate_*.3mf      suggested print plates
  cad/Assembly_RevC_heirloom.step, cad/PCB_mechanical_RevC.step (envelopes, NOT printable)
  cad/dxf/*.dxf              1:1 outlines: window panel, brass bezel, the five wood boards
"""
import json
import math
import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "cad" / "DIMENSIONS.json").read_text())

# ---------------- Named variables (all from DIMENSIONS.json) ----------------
L, W, H = D["base_l"], D["base_w"], D["case_h"]
CORNER_R, TOP_R = D["corner_r"], D["top_edge_r"]
WALL_T, ROOF_T, FLOOR_T = D["wall_t"], D["roof_t"], D["floor_t"]
FLOOR_CLEAR = D["floor_clearance"]                     # VERIFY
CORNER_BLOCK, CORNER_BLOCK_H = D["corner_block"], D["corner_block_h"]
PCB_L, PCB_W, PCB_T = D["pcb_l"], D["pcb_w"], D["pcb_t"]
PCB_X, PCB_Y, PCB_TOP_Z = D["pcb_offset_x"], D["pcb_offset_y"], D["pcb_top_z"]
PCB_BOT_Z = PCB_TOP_Z - PCB_T
TUBES = [tuple(p) for p in D["tube_centers"]]
SEPS = [tuple(p) for p in D["separator_centers"]]
BUTTONS = {k: tuple(v) for k, v in D["buttons"].items()}
PCB_SCREWS = [tuple(p) for p in D["pcb_screws"]]
CASE_SCREWS = [tuple(p) for p in D["case_screws"]]
GLASS_D, GLASS_H, SPACER_H = D["tube_glass_d"], D["tube_glass_h"], D["tube_spacer_h"]   # VERIFY
LAMP_H = D["lamp_h"]
WIN_X0, WIN_X1 = D["window_x"]
WIN_Z0, WIN_Z1 = D["window_z"]
WIN_R = D["window_r"]
PANEL_T = D["window_panel_t"]                          # VERIFY (cast acrylic is +/-10 %)
PANEL_X0, PANEL_X1 = D["window_panel_x"]
PANEL_H, PANEL_R = D["window_panel_h"], D["window_panel_r"]
SLOT_CLEAR = D["window_slot_clearance"]                # VERIFY
RAIL_LIP, RAIL_TOP_Z = D["window_rail_lip"], D["window_rail_top_z"]
BTN_H, BTN_BODY, BTN_BODY_H = D["button_height_above_pcb"], D["button_body"], D["button_body_h"]  # VERIFY
BTN_HOLE_D = D["button_hole_d"]                        # VERIFY
GUIDE_D, GUIDE_LEN = D["button_guide_d"], D["button_guide_len"]
ROD_D, ROD_CAP_D, ROD_CAP_T, ROD_CAP_GAP = D["rod_d"], D["rod_cap_d"], D["rod_cap_t"], D["rod_cap_gap"]
ROD_CUP_D, ROD_CUP_DEPTH = D["rod_cup_d"], D["rod_cup_depth"]
CABLE_HOLE_D = D["rear_cable_opening_d"]               # VERIFY
CABLE_HOLE_X, CABLE_HOLE_Z = D["rear_cable_opening_x"], D["rear_cable_opening_z"]
POST_D = D["pcb_post_d"]
PILOT_D, CLEAR_D = D["m2_pilot_d"], D["m2_clearance_d"]            # VERIFY
CBORE_D, CBORE_H = D["m2_head_counterbore_d"], D["m2_head_counterbore_depth"]
CLAMP_SCREWS = [tuple(p) for p in D["clamp_screws"]]
CLAMP_BOSS_D, CLAMP_BOSS_H = D["clamp_boss_d"], D["clamp_boss_h"]
CLAMP_L, CLAMP_W, CLAMP_BAR_T = D["clamp_len"], D["clamp_w"], D["clamp_bar_t"]
CABLE_D, CABLE_PINCH = D["cable_d"], D["cable_pinch"]  # VERIFY
LEAD_N, LEAD_CIRCLE_D, LEAD_HOLE_D = D["in14_lead_count"], D["in14_lead_circle_d"], D["in14_lead_hole_d"]
WOOD_T, WOOD_GAP, WOOD_R = D["wood_t"], D["wood_fit_gap"], D["wood_edge_r"]          # VERIFY
WOOD_MARGIN, WOOD_HOLE_D = D["wood_opening_margin"], D["wood_top_hole_d"]
NOTCH_W, NOTCH_H = D["wood_cable_notch_w"], D["wood_cable_notch_h"]
WOOD_PILOT_D, WOOD_PILOT_DEPTH = D["m2_wood_pilot_d"], D["wood_pilot_depth"]          # VERIFY
ROOF_SCREWS = [tuple(p) for p in D["roof_screws"]]
BAFFLE_X0, BAFFLE_X1 = D["light_baffle_x"]
BAFFLE_Z0 = D["light_baffle_z0"]
BEZEL_T, BEZEL_IN, BEZEL_W = D["bezel_t"], D["bezel_inner_margin"], D["bezel_width"]
BEZEL_SCREWS = [tuple(p) for p in D["bezel_screws"]]
FOOT_D, FOOT_H, FOOT_CH = D["foot_d"], D["foot_h"], D["foot_chamfer"]
FOOT_CBORE_D, FOOT_CBORE_H = D["foot_cbore_d"], D["foot_cbore_h"]

# Derived
ROOF_IN_Z = H - ROOF_T
SLOT_Y0 = WALL_T                                   # slot starts at the inside face of the front wall
SLOT_Y1 = WALL_T + PANEL_T + SLOT_CLEAR
RAIL_Y1 = SLOT_Y1 + RAIL_LIP
PANEL_Y0 = WALL_T + SLOT_CLEAR / 2
PANEL_Z0 = FLOOR_T
PANEL_Z1 = PANEL_Z0 + PANEL_H
SLOT_TOP_Z = PANEL_Z1 + 0.5
SWITCH_TOP_Z = PCB_TOP_Z + BTN_H
ROD_Z0 = SWITCH_TOP_Z - ROD_CUP_DEPTH               # rod bottom (the cup sits over the plunger)
# Hardwood box (outer faces) around the inner case
WO = WOOD_T + WOOD_GAP                              # wood outer face offset from the inner case
WX0, WX1 = -WO, L + WO
WY0, WY1 = -WO, W + WO
WZ1 = H + WOOD_T                                    # top board sits directly on the inner-case roof
WOOD_L, WOOD_W, WOOD_H = WX1 - WX0, WY1 - WY0, WZ1
WOOD_TOP_Z = WZ1
BZ_X0, BZ_X1 = WIN_X0 - BEZEL_IN, WIN_X1 + BEZEL_IN          # bezel inner edge (the visible window edge)
BZ_Z0, BZ_Z1 = WIN_Z0 - BEZEL_IN, WIN_Z1 + BEZEL_IN
BZ_OX0, BZ_OX1 = BZ_X0 - BEZEL_W, BZ_X1 + BEZEL_W            # bezel outer edge
BZ_OZ0, BZ_OZ1 = BZ_Z0 - BEZEL_W, BZ_Z1 + BEZEL_W
ROD_Z1 = WOOD_TOP_Z + ROD_CAP_GAP                   # cap underside, resting height
CRADLE_H = CABLE_HOLE_Z - CABLE_D / 2 - FLOOR_T
CLAMP_UNDER_Z = FLOOR_T + CRADLE_H + CABLE_D - CABLE_PINCH
CLAMP_TOP_Z = CLAMP_UNDER_Z + CLAMP_BAR_T
CLAMP_CBORE_H = 3.0
CASE_PILOT_DEPTH = 10.0
STANDOFF_PILOT_DEPTH = 8.0


def cyl(d, h, x, y, z0):
    return cq.Workplane("XY").circle(d / 2).extrude(h).translate((x, y, z0))


def rrect_xy(l, w, r, h, x0=0.0, y0=0.0, z0=0.0):
    return cq.Workplane("XY").box(l, w, h, centered=False).edges("|Z").fillet(r).translate((x0, y0, z0))


def rounded_rect_xz(x0, x1, z0, z1, r, y0, y1):
    """Prism along Y with a rounded-rectangle cross-section in XZ."""
    return (cq.Workplane("XZ").center((x0 + x1) / 2, (z0 + z1) / 2).rect(x1 - x0, z1 - z0).extrude(-(y1 - y0))
            .edges("|Y").fillet(r).translate((0, y0, 0)))


def loaf(inset, z_bottom, z_top):
    """Rounded box body: plan rounded rectangle, with the top edges rounded in side AND front view.
    Built as the intersection of three prisms so the booleans stay robust."""
    l, w = L - 2 * inset, W - 2 * inset
    h = z_top - z_bottom
    r_plan = max(CORNER_R - inset, 0.5)
    r_top = max(TOP_R - inset, 0.5)
    plan = rrect_xy(l, w, r_plan, h, inset, inset, z_bottom)
    side = (cq.Workplane("YZ").polyline([(0, 0), (w, 0), (w, h), (0, h)]).close().extrude(l)
            .edges("|X").edges(">Z").fillet(r_top).translate((inset, inset, z_bottom)))
    front = (cq.Workplane("XZ").polyline([(0, 0), (l, 0), (l, h), (0, h)]).close().extrude(-w)
             .edges("|Y").edges(">Z").fillet(r_top).translate((inset, inset, z_bottom)))
    return plan.intersect(side).intersect(front)


# ---------------- 01 inner case (printed; carries every functional feature) ----------------
def case_shell():
    body = loaf(0, 0, H).cut(loaf(WALL_T, -1, H - ROOF_T))
    # corner blocks for the four floor screws
    cav = rrect_xy(L - 2 * WALL_T, W - 2 * WALL_T, CORNER_R - WALL_T, CORNER_BLOCK_H, WALL_T, WALL_T, FLOOR_T)
    for cx, cy in CASE_SCREWS:
        bx = 0 if cx < L / 2 else L - CORNER_BLOCK
        by = 0 if cy < W / 2 else W - CORNER_BLOCK
        body = body.union(cq.Workplane("XY").box(CORNER_BLOCK, CORNER_BLOCK, CORNER_BLOCK_H, centered=False)
                          .translate((bx, by, FLOOR_T)).intersect(cav))
    # window panel rails (left, right, top) on the inside of the front wall, then the slot through them
    for x0, x1 in ((PANEL_X0 - 3, WIN_X0 - 1), (WIN_X1 + 1, PANEL_X1 + 3)):
        body = body.union(cq.Workplane("XY").box(x1 - x0, RAIL_Y1 - WALL_T + 0.5, RAIL_TOP_Z - FLOOR_T, centered=False)
                          .translate((x0, WALL_T - 0.5, FLOOR_T)))
    body = body.union(cq.Workplane("XY").box(PANEL_X1 - PANEL_X0 + 6, RAIL_Y1 - WALL_T + 0.5, RAIL_TOP_Z - (WIN_Z1 + 2), centered=False)
                      .translate((PANEL_X0 - 3, WALL_T - 0.5, WIN_Z1 + 2)))
    body = body.cut(cq.Workplane("XY").box(PANEL_X1 - PANEL_X0 + 2 * SLOT_CLEAR, SLOT_Y1 - SLOT_Y0, SLOT_TOP_Z + 1, centered=False)
                    .translate((PANEL_X0 - SLOT_CLEAR, SLOT_Y0, -1)))
    # light baffle: hides the button rods from anyone looking in through the window
    body = body.union(cq.Workplane("XY").box(BAFFLE_X1 - BAFFLE_X0, (W - WALL_T + 0.5) - (RAIL_Y1 - 0.5), ROOF_IN_Z + 0.5 - BAFFLE_Z0, centered=False)
                      .translate((BAFFLE_X0, RAIL_Y1 - 0.5, BAFFLE_Z0)))
    # button guides hanging from the roof, and the holes through them
    for x, y in BUTTONS.values():
        body = body.union(cyl(GUIDE_D, GUIDE_LEN + 1, x, y, ROOF_IN_Z - GUIDE_LEN))
        body = body.cut(cyl(BTN_HOLE_D, GUIDE_LEN + ROOF_T + 4, x, y, ROOF_IN_Z - GUIDE_LEN - 1))
    # front window opening (the wood front and the brass bezel frame it from outside)
    body = body.cut(rounded_rect_xz(WIN_X0, WIN_X1, WIN_Z0, WIN_Z1, WIN_R, -1, WALL_T + 0.5))
    # clearance holes in the roof for the four M2x8 that hold the wood top board
    for x, y in ROOF_SCREWS:
        body = body.cut(cyl(CLEAR_D, ROOF_T + 2, x, y, ROOF_IN_Z - 1))
    # floor-screw pilots and the rear cable hole
    for x, y in CASE_SCREWS:
        body = body.cut(cyl(PILOT_D, CASE_PILOT_DEPTH, x, y, FLOOR_T))
    body = body.cut(cq.Workplane("XZ").circle(CABLE_HOLE_D / 2).extrude(-WALL_T * 3)
                    .translate((CABLE_HOLE_X, W - WALL_T * 1.5, CABLE_HOLE_Z)))
    return body


# ---------------- 02 floor (carries the PCB on five standoffs) ----------------
def bottom_cover():
    inset = WALL_T + FLOOR_CLEAR
    cover = rrect_xy(L - 2 * inset, W - 2 * inset, CORNER_R - inset, FLOOR_T, inset, inset, 0)
    for x, y in PCB_SCREWS:
        cover = cover.union(cyl(POST_D, PCB_BOT_Z - FLOOR_T + 0.005, x, y, FLOOR_T - 0.005))
    for x, y in CLAMP_SCREWS:
        cover = cover.union(cyl(CLAMP_BOSS_D, CLAMP_BOSS_H, x, y, FLOOR_T))
    cx = (CLAMP_SCREWS[0][0] + CLAMP_SCREWS[1][0]) / 2
    cover = cover.union(cq.Workplane("XY").box(10, CLAMP_W + 4, CRADLE_H, centered=False)
                        .translate((cx - 5, CLAMP_SCREWS[0][1] - (CLAMP_W + 4) / 2, FLOOR_T)))
    for x, y in PCB_SCREWS:
        cover = cover.cut(cyl(PILOT_D, STANDOFF_PILOT_DEPTH + 0.01, x, y, PCB_BOT_Z - STANDOFF_PILOT_DEPTH))
    for x, y in CASE_SCREWS:
        cover = cover.cut(cyl(CLEAR_D, FLOOR_T + 1, x, y, -0.5))   # screw heads sit in the brass feet
    for x, y in CLAMP_SCREWS:
        cover = cover.cut(cyl(PILOT_D, FLOOR_T + CLAMP_BOSS_H - 0.6, x, y, 0.6))
    return cover


# ---------------- 03 cable clamp (low-voltage strain relief) ----------------
def cable_clamp():
    (x0, y0), _ = CLAMP_SCREWS
    cx = (CLAMP_SCREWS[0][0] + CLAMP_SCREWS[1][0]) / 2
    z_leg = FLOOR_T + CLAMP_BOSS_H
    clamp = cq.Workplane("XY").box(CLAMP_L, CLAMP_W, CLAMP_BAR_T, centered=False).translate((cx - CLAMP_L / 2, y0 - CLAMP_W / 2, CLAMP_UNDER_Z))
    for x, _ in CLAMP_SCREWS:
        clamp = clamp.union(cq.Workplane("XY").box(CLAMP_BOSS_D + 1, CLAMP_W, CLAMP_UNDER_Z - z_leg, centered=False)
                            .translate((x - (CLAMP_BOSS_D + 1) / 2, y0 - CLAMP_W / 2, z_leg)))
    for x, y in CLAMP_SCREWS:
        clamp = clamp.cut(cyl(CLEAR_D, CLAMP_TOP_Z - z_leg + 1, x, y, z_leg - 0.5))
        clamp = clamp.cut(cyl(CBORE_D, CLAMP_CBORE_H + 0.01, x, y, CLAMP_TOP_Z - CLAMP_CBORE_H))
    return clamp


# ---------------- 04 button rod (print 3) ----------------
def button_rod(x=None, y=None):
    """Rod in assembly position over switch (x, y); default SET. Cap on top, cup underneath."""
    if x is None:
        x, y = BUTTONS["SET"]
    rod = cyl(ROD_D, ROD_Z1 - ROD_Z0 + 0.01, x, y, ROD_Z0)
    cap = cyl(ROD_CAP_D, ROD_CAP_T, x, y, ROD_Z1).edges(">Z").fillet(1.2)
    return rod.union(cap).cut(cyl(ROD_CUP_D, ROD_CUP_DEPTH, x, y, ROD_Z0 - 0.001))


# ---------------- 05 window panel (laser-cut acrylic, not printed) ----------------
def window_panel():
    p = (cq.Workplane("XZ").center((PANEL_X0 + PANEL_X1) / 2, (PANEL_Z0 + PANEL_Z1) / 2)
         .rect(PANEL_X1 - PANEL_X0, PANEL_H).extrude(-PANEL_T).edges("|Y").fillet(PANEL_R))
    return p.translate((0, PANEL_Y0, 0))


# ---------------- 06 fit coupon ----------------
def fit_coupon():
    c = cq.Workplane("XY").box(90, 32, 3, centered=False).edges("|Z").fillet(4)
    # (a) PCB standoff with pilot: tap M2, drive an M2x6 through a scrap of 1.6 mm board
    c = c.union(cyl(POST_D, 10, 10, 10, 3)).cut(cyl(PILOT_D, STANDOFF_PILOT_DEPTH, 10, 10, 13 - STANDOFF_PILOT_DEPTH + 0.01))
    # (b) floor-screw block with pilot from the top (like the case corner blocks)
    c = c.union(cq.Workplane("XY").box(10, 10, CORNER_BLOCK_H, centered=False).translate((20, 5, 3)))
    c = c.cut(cyl(PILOT_D, CASE_PILOT_DEPTH, 25, 10, 3 + CORNER_BLOCK_H - CASE_PILOT_DEPTH + 0.01))
    # (c) button hole with guide: a printed rod (part 04) must slide freely
    c = c.union(cyl(GUIDE_D, 8, 42, 16, 3)).cut(cyl(BTN_HOLE_D, 14, 42, 16, -1))
    # (d) window slot: a 25 mm sample of your acrylic must slide in without force
    c = c.union(cq.Workplane("XY").box(30, PANEL_T + SLOT_CLEAR + 2 * 2.0, 12, centered=False).translate((55, 8, 3)))
    c = c.cut(cq.Workplane("XY").box(32, PANEL_T + SLOT_CLEAR, 12, centered=False).translate((54, 10, 4)))
    # (e) M2 clearance hole and counterbore, as in the floor
    c = c.cut(cyl(CLEAR_D, 5, 10, 25, -1)).cut(cyl(CBORE_D, CBORE_H, 10, 25, -0.001))
    return c.cut(cq.Workplane("XY").box(4, 2, 5, centered=False).translate((0, 0, -1)))   # orientation notch


# ---------------- 07 unpowered lead-pattern coupon ----------------
def lead_coupon():
    c = cq.Workplane("XY").circle(14).extrude(2.0)
    for i in range(LEAD_N):
        a = 2 * math.pi * i / LEAD_N
        c = c.cut(cyl(LEAD_HOLE_D, 4, LEAD_CIRCLE_D / 2 * math.cos(a), LEAD_CIRCLE_D / 2 * math.sin(a), -1))
    return c.cut(cq.Workplane("XY").box(6, 2, 4, centered=False).translate((10, -1, -1)))   # "never powered" slot


# ---------------- 08-12 hardwood box (five mitred boards) ----------------
def wood_box():
    """The glued-up hardwood box as one solid: outer edges rounded, open at the bottom."""
    box = cq.Workplane("XY").box(WOOD_L, WOOD_W, WOOD_H, centered=False).translate((WX0, WY0, 0)).edges().fillet(WOOD_R)
    box = box.cut(cq.Workplane("XY").box(L + 2 * WOOD_GAP, W + 2 * WOOD_GAP, H + 1, centered=False)
                  .translate((-WOOD_GAP, -WOOD_GAP, -1)))
    # front opening: slightly larger than the inner-case window, its edge hidden behind the brass bezel
    m = WOOD_MARGIN
    box = box.cut(rounded_rect_xz(WIN_X0 - m, WIN_X1 + m, WIN_Z0 - m, WIN_Z1 + m, WIN_R + m, WY0 - 1, 0))
    # pilot holes for the brass bezel screws (front face) and the roof screws (underside of the top board)
    for x, z in BEZEL_SCREWS:
        box = box.cut(cq.Workplane("XZ").circle(WOOD_PILOT_D / 2).extrude(-WOOD_PILOT_DEPTH).translate((x, WY0, z)))
    for x, y in ROOF_SCREWS:
        box = box.cut(cyl(WOOD_PILOT_D, WOOD_PILOT_DEPTH, x, y, H - 0.01))
    # button holes in the top board
    for x, y in BUTTONS.values():
        box = box.cut(cyl(WOOD_HOLE_D, WOOD_T + 2, x, y, H - 1))
    # cable notch in the bottom edge of the back board
    notch = (cq.Workplane("XZ").center(CABLE_HOLE_X, (NOTCH_H - 1) / 2).rect(NOTCH_W, NOTCH_H + 1).extrude(-(WOOD_T + 2))
             .edges("|Y").edges(">Z").fillet(NOTCH_W / 2 - 0.01).translate((0, W, 0)))
    return box.cut(notch)


def _board_regions():
    """45-degree mitre regions: each point of the box belongs to the outer face it is closest to."""
    big = 40.0   # < half the box depth so the mitre pyramid stays well formed
    top = (cq.Workplane("XY").workplane(offset=WZ1 - big).rect(WOOD_L - 2 * big, WOOD_W - 2 * big)
           .workplane(offset=big + 2).rect(WOOD_L + 2 * 2, WOOD_W + 2 * 2).loft()
           .translate(((WX0 + WX1) / 2, (WY0 + WY1) / 2, 0)))
    zlo, zhi = -2.0, WZ1 + 4
    def prism(pts):
        return cq.Workplane("XY").polyline(pts).close().extrude(zhi - zlo).translate((0, 0, zlo)).cut(top)
    e = 2.0
    front = prism([(WX0 - e, WY0 - e), (WX1 + e, WY0 - e), (WX1 - big, WY0 + big), (WX0 + big, WY0 + big)])
    back = prism([(WX0 - e, WY1 + e), (WX0 + big, WY1 - big), (WX1 - big, WY1 - big), (WX1 + e, WY1 + e)])
    left = prism([(WX0 - e, WY0 - e), (WX0 + big, WY0 + big), (WX0 + big, WY1 - big), (WX0 - e, WY1 + e)])
    right = prism([(WX1 + e, WY0 - e), (WX1 + e, WY1 + e), (WX1 - big, WY1 - big), (WX1 - big, WY0 + big)])
    return {"front": front, "back": back, "end_left": left, "end_right": right, "top": top}


_BOARDS = {}


def wood_board(name):
    if not _BOARDS:
        box = wood_box()
        for k, reg in _board_regions().items():
            _BOARDS[k] = box.intersect(reg)
    return _BOARDS[name]


def wood_front():
    return wood_board("front")


def wood_back():
    return wood_board("back")


def wood_end_left():
    return wood_board("end_left")


def wood_end_right():
    return wood_board("end_right")


def wood_top():
    return wood_board("top")


# ---------------- 13 brass bezel (1 mm brass sheet, cut) ----------------
def brass_bezel():
    outer = rounded_rect_xz(BZ_OX0, BZ_OX1, BZ_OZ0, BZ_OZ1, WIN_R + BEZEL_IN + BEZEL_W, WY0 - BEZEL_T, WY0)
    inner = rounded_rect_xz(BZ_X0, BZ_X1, BZ_Z0, BZ_Z1, WIN_R + BEZEL_IN, WY0 - BEZEL_T - 1, WY0 + 1)
    bz = outer.cut(inner)
    for x, z in BEZEL_SCREWS:
        bz = bz.cut(cq.Workplane("XZ").circle(CLEAR_D / 2).extrude(-(BEZEL_T + 2)).translate((x, WY0 - BEZEL_T - 1, z)))
    return bz


# ---------------- 14 brass foot (make 4: turned or drilled from 14 mm brass bar) ----------------
def brass_foot(x=None, y=None):
    if x is None:
        x, y = CASE_SCREWS[0]
    f = cyl(FOOT_D, FOOT_H, x, y, -FOOT_H).faces("<Z").edges().chamfer(FOOT_CH)
    f = f.cut(cyl(CLEAR_D, FOOT_H + 2, x, y, -FOOT_H - 1))
    return f.cut(cyl(FOOT_CBORE_D, FOOT_CBORE_H, x, y, -FOOT_H - 0.001))


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
        parts[f"lamp_{i}"] = cyl(6.35, LAMP_H, x, y, PCB_TOP_Z + 1)
    for k, (x, y) in BUTTONS.items():
        parts[f"button_{k}"] = (cq.Workplane("XY").box(BTN_BODY, BTN_BODY, BTN_BODY_H).translate((x, y, PCB_TOP_Z + BTN_BODY_H / 2))
                                .union(cyl(3.5, BTN_H - BTN_BODY_H, x, y, PCB_TOP_Z + BTN_BODY_H)))
    return parts


def print_orient(shape, flip):
    s = shape.rotate((0, 0, 0), (1, 0, 0), 180) if flip else shape
    bb = s.val().BoundingBox()
    return s.translate((-bb.xmin, -bb.ymin, -bb.zmin))


PARTS = {
    # name: (builder, flip for printing, printable)
    "01_inner_case": (case_shell, False, True),
    "02_floor": (bottom_cover, False, True),
    "03_cable_clamp": (cable_clamp, True, True),
    "04_button_rod": (button_rod, True, True),
    "05_window_panel_3mm_acrylic": (window_panel, False, False),
    "06_fit_coupon": (fit_coupon, False, True),
    "07_unpowered_lead_pattern_coupon": (lead_coupon, False, True),
    "08_wood_front": (wood_front, False, False),
    "09_wood_back": (wood_back, False, False),
    "10_wood_end_left": (wood_end_left, False, False),
    "11_wood_end_right": (wood_end_right, False, False),
    "12_wood_top": (wood_top, False, False),
    "13_brass_bezel_1mm": (brass_bezel, False, False),
    "14_brass_foot": (brass_foot, True, True),
}
WOOD_PARTS = ["08_wood_front", "09_wood_back", "10_wood_end_left", "11_wood_end_right", "12_wood_top"]


def _dxf_doc():
    import ezdxf
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.layers.add("CUT", color=1)
    doc.layers.add("DRILL", color=3)
    doc.layers.add("MITRE_45", color=5)
    doc.layers.add("NOTES", color=7)
    return doc


def _rrect(msp, x0, y0, x1, y1, r, layer="CUT"):
    a = {"layer": layer}
    msp.add_line((x0 + r, y0), (x1 - r, y0), dxfattribs=a)
    msp.add_line((x1, y0 + r), (x1, y1 - r), dxfattribs=a)
    msp.add_line((x1 - r, y1), (x0 + r, y1), dxfattribs=a)
    msp.add_line((x0, y1 - r), (x0, y0 + r), dxfattribs=a)
    if r > 0:
        msp.add_arc((x1 - r, y0 + r), r, 270, 0, dxfattribs=a)
        msp.add_arc((x1 - r, y1 - r), r, 0, 90, dxfattribs=a)
        msp.add_arc((x0 + r, y1 - r), r, 90, 180, dxfattribs=a)
        msp.add_arc((x0 + r, y0 + r), r, 180, 270, dxfattribs=a)


def _note(msp, text, x, y, h=3.0):
    msp.add_text(text, height=h, dxfattribs={"layer": "NOTES"}).set_placement((x, y))


def write_dxfs(out):
    """1:1 outlines in mm. Each DXF has its origin at the bottom-left corner of the part as seen from outside."""
    files = {}
    # window panel
    doc = _dxf_doc(); msp = doc.modelspace()
    w, h = PANEL_X1 - PANEL_X0, PANEL_H
    _rrect(msp, 0, 0, w, h, PANEL_R)
    _note(msp, "05 window panel: 3 mm CAST acrylic, smoked grey or bronze. 1:1 mm. VERIFY scale before cutting.", 0, h + 5, 2.5)
    doc.saveas(out / "Window_panel_3mm_1to1.dxf"); files["Window_panel_3mm_1to1.dxf"] = (w, h)
    # brass bezel, seen from the front, origin at the bezel's outer bottom-left corner
    doc = _dxf_doc(); msp = doc.modelspace()
    ox, oz = BZ_OX0, BZ_OZ0
    _rrect(msp, 0, 0, BZ_OX1 - ox, BZ_OZ1 - oz, WIN_R + BEZEL_IN + BEZEL_W)
    _rrect(msp, BZ_X0 - ox, BZ_Z0 - oz, BZ_X1 - ox, BZ_Z1 - oz, WIN_R + BEZEL_IN)
    for x, z in BEZEL_SCREWS:
        msp.add_circle((x - ox, z - oz), CLEAR_D / 2, dxfattribs={"layer": "DRILL"})
    _note(msp, f"13 brass bezel: {BEZEL_T:g} mm brass sheet (CuZn37 / C272 or C260), laser, waterjet or fret saw. 6 holes 2.4 mm. 1:1 mm.", 0, BZ_OZ1 - oz + 5, 2.5)
    doc.saveas(out / "Brass_bezel_1mm_1to1.dxf"); files["Brass_bezel_1mm_1to1.dxf"] = (BZ_OX1 - BZ_OX0, BZ_OZ1 - BZ_OZ0)
    # wood boards: outer-face outlines laid out on one sheet, with cut-outs, holes and mitred edges marked
    doc = _dxf_doc(); msp = doc.modelspace()
    m = WOOD_MARGIN
    gap = 25.0
    # front (seen from the front): x right, z up; origin at WX0, 0
    fx, fy = 0.0, 0.0
    _rrect(msp, fx, fy, fx + WOOD_L, fy + WOOD_H, 0)
    _rrect(msp, fx + WIN_X0 - m - WX0, fy + WIN_Z0 - m, fx + WIN_X1 + m - WX0, fy + WIN_Z1 + m, WIN_R + m)
    for x, z in BEZEL_SCREWS:
        msp.add_circle((fx + x - WX0, fy + z), WOOD_PILOT_D / 2, dxfattribs={"layer": "DRILL"})
    for a, b in (((fx, fy), (fx, fy + WOOD_H)), ((fx + WOOD_L, fy), (fx + WOOD_L, fy + WOOD_H)), ((fx, fy + WOOD_H), (fx + WOOD_L, fy + WOOD_H))):
        msp.add_line(a, b, dxfattribs={"layer": "MITRE_45"})
    _note(msp, f"08 FRONT {WOOD_L:g} x {WOOD_H:g} x {WOOD_T:g} mm (outer face). 45 deg mitre: both ends and top edge. Bottom edge square. "
          f"Window {WIN_X1 - WIN_X0 + 2 * m:g} x {WIN_Z1 - WIN_Z0 + 2 * m:g} R{WIN_R + m:g}. 6 pilots {WOOD_PILOT_D:g} x {WOOD_PILOT_DEPTH:g} deep.", fx, fy - 8)
    # back (seen from the BACK, so x runs right-to-left in enclosure terms)
    bx, by = 0.0, WOOD_H + gap + 10
    _rrect(msp, bx, by, bx + WOOD_L, by + WOOD_H, 0)
    nx = bx + (WX1 - CABLE_HOLE_X)
    _rrect(msp, nx - NOTCH_W / 2, by - 0.01, nx + NOTCH_W / 2, by + NOTCH_H, 0)
    _note(msp, f"09 BACK {WOOD_L:g} x {WOOD_H:g} x {WOOD_T:g} mm (outer face, seen from behind). Mitre both ends and top. "
          f"Cable notch {NOTCH_W:g} wide x {NOTCH_H:g} high in the bottom edge, centre {WX1 - CABLE_HOLE_X:g} mm from the left end as seen from behind.", bx, by - 8)
    # ends
    ex, ey = 0.0, 2 * (WOOD_H + gap + 10)
    for k, label in enumerate(("10 END LEFT", "11 END RIGHT")):
        x0 = ex + k * (WOOD_W + gap)
        _rrect(msp, x0, ey, x0 + WOOD_W, ey + WOOD_H, 0)
        _note(msp, f"{label} {WOOD_W:g} x {WOOD_H:g} x {WOOD_T:g} mm. Mitre both vertical edges and top.", x0, ey - 8, 2.5)
    # top (seen from above: x right, y up = toward the back)
    tx, ty = 2 * (WOOD_W + gap), ey
    _rrect(msp, tx, ty, tx + WOOD_L, ty + WOOD_W, 0)
    for x, y in BUTTONS.values():
        msp.add_circle((tx + x - WX0, ty + y - WY0), WOOD_HOLE_D / 2, dxfattribs={"layer": "DRILL"})
    for x, y in ROOF_SCREWS:
        msp.add_circle((tx + x - WX0, ty + y - WY0), WOOD_PILOT_D / 2, dxfattribs={"layer": "DRILL"})
    _note(msp, f"12 TOP {WOOD_L:g} x {WOOD_W:g} x {WOOD_T:g} mm, seen from above. Mitre all four edges. 3 holes {WOOD_HOLE_D:g} through; "
          f"4 pilots {WOOD_PILOT_D:g} x {WOOD_PILOT_DEPTH:g} deep drilled from the UNDERSIDE (do not break through).", tx, ty - 8, 2.5)
    _note(msp, "Rev C heirloom case, hardwood boards, 1:1 mm. Grain runs along the long side of every board. VERIFY scale before cutting.", 0, ey + WOOD_H + 12, 4)
    doc.saveas(out / "Wood_boards_1to1.dxf"); files["Wood_boards_1to1.dxf"] = (tx + WOOD_L, ey + WOOD_H)
    return files


def main(out=ROOT / "cad"):
    for sub in ("step", "stl", "3mf", "print", "dxf"):
        (out / sub).mkdir(parents=True, exist_ok=True)
        for old in (out / sub).glob("*"):
            old.unlink()   # remove outputs of parts that no longer exist
    for old in out.glob("Assembly_RevC_*.step"):
        old.unlink()
    for old in out.glob("*.dxf"):
        old.unlink()
    built, report = {}, []
    for name, (fn, flip, printable) in PARTS.items():
        shp = fn()
        solid = shp.val()
        assert solid.isValid(), f"{name} is not a valid solid"
        built[name] = shp
        cq.exporters.export(shp, str(out / "step" / f"{name}.step"))
        po = print_orient(shp, flip)
        bb = po.val().BoundingBox()
        if printable:
            cq.exporters.export(po, str(out / "stl" / f"{name}.stl"), tolerance=0.02, angularTolerance=0.1)
            cq.exporters.export(po, str(out / "3mf" / f"{name}.3mf"), tolerance=0.02, angularTolerance=0.1)
            report.append(f"{name:36s} print bbox {bb.xlen:6.1f} x {bb.ylen:5.1f} x {bb.zlen:5.1f} mm  volume {solid.Volume() / 1000:6.1f} cm3")
        else:
            report.append(f"{name:36s} made, not printed: bbox {bb.xlen:6.1f} x {bb.ylen:5.1f} x {bb.zlen:5.1f} mm  volume {solid.Volume() / 1000:6.1f} cm3")
    wood_cm3 = sum(built[n].val().Volume() for n in WOOD_PARTS) / 1000
    report.append(f"hardwood box total {wood_cm3:.0f} cm3, about {wood_cm3 * 0.64:.0f} g in walnut; outer {WOOD_L:g} x {WOOD_W:g} x {WOOD_H:g} mm, {WOOD_H + FOOT_H:g} mm tall on its feet")

    env = pcb_mechanical()
    colors = {"PCB": (0.1, 0.35, 0.15), "glass": (0.9, 0.55, 0.2, 0.35), "spacer": (0.2, 0.2, 0.2),
              "lamp": (1.0, 0.45, 0.1, 0.6), "button": (0.3, 0.3, 0.3)}
    pcb_asm = cq.Assembly(name="PCB_mechanical_RevC")
    for k, v in env.items():
        pcb_asm.add(v, name=k, color=cq.Color(*colors[k.split("_")[0]]))
    pcb_asm.export(str(out / "PCB_mechanical_RevC.step"))

    walnut, brass = cq.Color(0.36, 0.22, 0.13), cq.Color(0.80, 0.62, 0.30)
    asm = cq.Assembly(name="Assembly_RevC_heirloom")
    asm.add(built["01_inner_case"], name="01_inner_case", color=cq.Color(0.12, 0.12, 0.13))
    asm.add(built["02_floor"], name="02_floor", color=cq.Color(0.2, 0.2, 0.21))
    asm.add(built["03_cable_clamp"], name="03_cable_clamp", color=cq.Color(0.2, 0.2, 0.21))
    for k, (x, y) in BUTTONS.items():
        asm.add(button_rod(x, y), name=f"04_button_rod_{k}", color=brass)
    asm.add(built["05_window_panel_3mm_acrylic"], name="05_window_panel", color=cq.Color(0.25, 0.22, 0.2, 0.45))
    for n in WOOD_PARTS:
        asm.add(built[n], name=n, color=walnut)
    asm.add(built["13_brass_bezel_1mm"], name="13_brass_bezel", color=brass)
    for i, (x, y) in enumerate(CASE_SCREWS, 1):
        asm.add(brass_foot(x, y), name=f"14_brass_foot_{i}", color=brass)
    asm.add(pcb_asm, name="PCB_mechanical")
    asm.export(str(out / "Assembly_RevC_heirloom.step"))

    def plate(items, fname):
        y, shapes = 0.0, []
        for n, copies in items:
            fn, flip, _ = PARTS[n]
            po = print_orient(built[n], flip)
            bb = po.val().BoundingBox()
            for c in range(copies):
                shapes.append(po.translate((c * (bb.xlen + 8), y, 0)).val())
            y += bb.ylen + 8
        cq.exporters.export(cq.Workplane().add(cq.Compound.makeCompound(shapes)), str(out / "print" / fname), tolerance=0.02, angularTolerance=0.1)

    plate([("06_fit_coupon", 1), ("07_unpowered_lead_pattern_coupon", 1)], "plate_0_fit_coupons.3mf")
    plate([("01_inner_case", 1)], "plate_A_inner_case.3mf")
    plate([("02_floor", 1), ("03_cable_clamp", 1)], "plate_B_floor_clamp.3mf")
    plate([("04_button_rod", 3)], "plate_C_button_rods_silk_brass.3mf")

    for f, (w, h) in write_dxfs(out / "dxf").items():
        report.append(f"dxf/{f:32s} sheet {w:.1f} x {h:.1f} mm")
    (out / "BUILD_REPORT.txt").write_text("Generated by source/build_cad.py from cad/DIMENSIONS.json\n" + "\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "cad")
