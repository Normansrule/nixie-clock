#!/usr/bin/env python3
"""make_drawings.py - dimensioned drawings and flow diagrams generated from cad/DIMENSIONS.json and the BOM.

Writes (docs/img/):
  dimensions.svg   heirloom case front and side views with key dimensions
  pcb_drawing.svg  PCB mechanical drawing: outline, M2 holes, tube/lamp/switch positions
  make_it.svg      what to make, from which file, and what is ready
  build_flow.svg   build stages 0-7 with their gates
All numbers come from the data files, so the drawings never drift from the CAD.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "cad" / "DIMENSIONS.json").read_text())
IMG = ROOT / "docs" / "img"

BG, PANEL, LINE, INK, MUTE, GLOW, HV, OK = "#14110f", "#1f1915", "#5a4d42", "#f4e9dc", "#b9a99a", "#ff9a3c", "#ff5a3c", "#7fd18b"
STYLE = f"""<style>
.o{{fill:none;stroke:{INK};stroke-width:1.4}}.t{{fill:none;stroke:{GLOW};stroke-width:1.2}}.h{{fill:none;stroke:{MUTE};stroke-width:1}}
.d{{stroke:{MUTE};stroke-width:.8;fill:none}}.dt{{fill:{MUTE};font-size:11px}}.lb{{fill:{INK};font-size:12px}}.ti{{fill:{INK};font-size:16px;font-weight:600}}
.sm{{fill:{MUTE};font-size:10px}}
</style>
<defs><marker id="ar" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTE}"/></marker></defs>"""


def dim_h(x1, x2, y, text, off=0):
    return (f'<line class="d" x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" marker-start="url(#ar)" marker-end="url(#ar)"/>'
            f'<text class="dt" x="{(x1 + x2) / 2 + off}" y="{y - 4}" text-anchor="middle">{text}</text>')


def dim_v(x, y1, y2, text):
    return (f'<line class="d" x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" marker-start="url(#ar)" marker-end="url(#ar)"/>'
            f'<text class="dt" x="{x - 6}" y="{(y1 + y2) / 2 + 4}" text-anchor="end">{text}</text>')


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="system-ui,-apple-system,Segoe UI,sans-serif">'
            f'<title>{title}</title>{STYLE}<rect width="{w}" height="{h}" rx="14" fill="{BG}"/>{body}</svg>')


def dimensions():
    """Heirloom case: front view (wood, brass bezel, window, tubes, buttons, feet) and side view."""
    s = 2.8
    to = D["wood_t"] + D["wood_fit_gap"]                       # wood outer face offset from the inner case
    L, W_, H = D["base_l"], D["base_w"], D["case_h"]
    WL, WW, WH = L + 2 * to, W_ + 2 * to, H + D["wood_t"]
    fh = D["foot_h"]
    wx0, wx1 = D["window_x"]
    wz0, wz1 = D["window_z"]
    bi, bw = D["bezel_inner_margin"], D["bezel_width"]
    rod_top = WH + D["rod_cap_gap"] + D["rod_cap_t"]
    ox, oy = 130, 124
    X = lambda x: ox + (x + to) * s                              # enclosure x -> drawing
    Z = lambda z: oy + (rod_top - z) * s
    WOOD, BRASS = "#8a5a36", "#d9a441"
    b = [f'<text class="ti" x="24" y="34">Heirloom case: front and side views (mm)</text>',
         f'<text class="sm" x="24" y="52">From cad/DIMENSIONS.json. Walnut box ({D["wood_t"]:g} mm boards, 45° mitres) over the printed inner case; brass bezel and feet. Values marked VERIFY there are unmeasured.</text>',
         f'<text class="lb" x="{ox}" y="{oy - 44}">Front</text>']
    b.append(f'<rect x="{X(-to)}" y="{Z(WH)}" width="{WL * s}" height="{WH * s}" rx="{D["wood_edge_r"] * s}" fill="{WOOD}" fill-opacity=".22" stroke="{WOOD}" stroke-width="1.6"/>')
    for x, _ in D["case_screws"][:2]:
        b.append(f'<rect x="{X(x - D["foot_d"] / 2)}" y="{Z(0)}" width="{D["foot_d"] * s}" height="{fh * s}" rx="3" fill="{BRASS}" fill-opacity=".5" stroke="{BRASS}"/>')
    r_o = D["window_r"] + bi + bw
    b.append(f'<rect x="{X(wx0 - bi - bw)}" y="{Z(wz1 + bi + bw)}" width="{(wx1 - wx0 + 2 * (bi + bw)) * s}" height="{(wz1 - wz0 + 2 * (bi + bw)) * s}" rx="{r_o * s}" fill="{BRASS}" fill-opacity=".28" stroke="{BRASS}" stroke-width="1.4"/>')
    b.append(f'<rect x="{X(wx0 - bi)}" y="{Z(wz1 + bi)}" width="{(wx1 - wx0 + 2 * bi) * s}" height="{(wz1 - wz0 + 2 * bi) * s}" rx="{(D["window_r"] + bi) * s}" fill="{BG}" stroke="{BRASS}" stroke-width="1.2"/>')
    for x, z in D["bezel_screws"]:
        b.append(f'<circle cx="{X(x)}" cy="{Z(z)}" r="{1.9 * s}" fill="{BRASS}"/>')
    g = D["tube_glass_d"] / 2
    z0 = D["pcb_top_z"] + D["tube_spacer_h"]
    for i, (x, _) in enumerate(D["tube_centers"], 1):
        b.append(f'<rect class="t" x="{X(x - g)}" y="{Z(z0 + D["tube_glass_h"])}" width="{2 * g * s}" height="{D["tube_glass_h"] * s}" rx="{g * s}" stroke-dasharray="3 3"/>'
                 f'<text x="{X(x)}" y="{Z(z0 + 30)}" fill="{GLOW}" font-size="28" text-anchor="middle">{"100842"[i - 1]}</text>')
    for x, y in D["buttons"].values():
        b.append(f'<rect x="{X(x - D["rod_cap_d"] / 2)}" y="{Z(rod_top)}" width="{D["rod_cap_d"] * s}" height="{D["rod_cap_t"] * s}" rx="3" fill="{BRASS}"/>')
    b.append(dim_h(X(-to), X(L + to), oy - 28, f"{WL:g}"))
    b.append(dim_v(X(-to) - 14, Z(WH), Z(-fh), f"{WH + fh:g} on feet"))
    b.append(dim_h(X(wx0 - bi), X(wx1 + bi), Z(-fh) + 22, f"visible window {wx1 - wx0 + 2 * bi:g} × {wz1 - wz0 + 2 * bi:g}"))
    b.append(f'<text class="dt" x="{X(L + to) - 4}" y="{Z(rod_top) - 6}" text-anchor="end">brass SET · H · M caps on top</text>')
    # side view
    sx = X(L + to) + 80
    Y = lambda y: sx + (y + to) * s
    b.append(f'<text class="lb" x="{sx}" y="{oy - 44}">Side (left end)</text>')
    b.append(f'<rect x="{Y(-to)}" y="{Z(WH)}" width="{WW * s}" height="{WH * s}" rx="{D["wood_edge_r"] * s}" fill="{WOOD}" fill-opacity=".22" stroke="{WOOD}" stroke-width="1.6"/>')
    b.append(f'<rect class="h" x="{Y(0)}" y="{Z(H)}" width="{W_ * s}" height="{H * s}" stroke-dasharray="4 3"/>')
    for x, y in D["case_screws"][::2]:
        b.append(f'<rect x="{Y(y - D["foot_d"] / 2)}" y="{Z(0)}" width="{D["foot_d"] * s}" height="{fh * s}" rx="3" fill="{BRASS}" fill-opacity=".5" stroke="{BRASS}"/>')
    for _, y in D["buttons"].values():
        b.append(f'<rect x="{Y(y - D["rod_cap_d"] / 2)}" y="{Z(rod_top)}" width="{D["rod_cap_d"] * s}" height="{D["rod_cap_t"] * s}" rx="3" fill="{BRASS}"/>')
    ty = D["tube_centers"][0][1]
    b.append(f'<rect class="t" x="{Y(ty - g)}" y="{Z(z0 + D["tube_glass_h"])}" width="{2 * g * s}" height="{D["tube_glass_h"] * s}" rx="{g * s}" stroke-dasharray="3 3"/>')
    b.append(f'<line class="h" x1="{Y(D["pcb_offset_y"])}" y1="{Z(D["pcb_top_z"])}" x2="{Y(D["pcb_offset_y"] + D["pcb_w"])}" y2="{Z(D["pcb_top_z"])}" stroke-width="3"/>')
    b.append(f'<line class="h" x1="{Y(D["wall_t"]) + 4}" y1="{Z(D["floor_t"])}" x2="{Y(D["wall_t"]) + 4}" y2="{Z(D["floor_t"] + D["window_panel_h"])}" stroke-width="3" stroke="#8a6a50"/>')
    b.append(dim_h(Y(-to), Y(W_ + to), oy - 28, f"{WW:g}"))
    b.append(dim_v(Y(W_ + to) + 44, Z(rod_top), Z(-fh), f"{rod_top + fh:g}"))
    b.append(f'<text class="sm" x="{sx}" y="{Z(-fh) + 20}">front ←  window panel · PCB · tube; dashed = printed inner case</text>')
    h = Z(-fh) + 52
    b.append(f'<text class="sm" x="{ox}" y="{h - 8}">Wood outer edges rounded R{D["wood_edge_r"]:g}. Inner case {L:g} × {W_:g} × {H:g}. Glass Ø{D["tube_glass_d"]:g} × {D["tube_glass_h"]:g} on {D["tube_spacer_h"]:g} mm spacers; PCB top at z = {D["pcb_top_z"]:g}. Brass: bezel {D["bezel_t"]:g} mm sheet, feet Ø{D["foot_d"]:g} × {fh:g}.</text>')
    (IMG / "dimensions.svg").write_text(svg(Y(W_ + to) + 110, h + 10, "".join(b), "Heirloom case dimensions"))


def pcb():
    s = 3.6
    L, W_ = D["pcb_l"], D["pcb_w"]
    px, py = D["pcb_offset_x"], D["pcb_offset_y"]
    ox, oy = 70, 100
    X = lambda x: ox + (x - px) * s
    Y = lambda y: oy + (py + W_ - y) * s
    b = [f'<text class="ti" x="24" y="34">PCB mechanical drawing (top view, mm)</text>',
         f'<text class="sm" x="24" y="52">{L:g} × {W_:g} × {D["pcb_t"]:g} mm, {D["pcb_layers"]} layers. Coordinates in enclosure frame; PCB corner at ({px:g}, {py:g}). Not a fabrication drawing until the gate in MANUFACTURING.md passes.</text>',
         f'<rect class="o" x="{ox}" y="{oy}" width="{L * s}" height="{W_ * s}"/>']
    for i, (x, y) in enumerate(D["tube_centers"], 1):
        b.append(f'<circle class="t" cx="{X(x)}" cy="{Y(y)}" r="{D["tube_courtyard_d"] / 2 * s}" stroke-dasharray="3 3"/>'
                 f'<text class="lb" x="{X(x)}" y="{Y(y) + 4}" text-anchor="middle">T{i}</text>'
                 f'<text class="sm" x="{X(x)}" y="{Y(y) + 17}" text-anchor="middle">({x:g}, {y:g})</text>')
    for i, (x, y) in enumerate(D["separator_centers"], 1):
        b.append(f'<circle class="t" cx="{X(x)}" cy="{Y(y)}" r="{3.2 * s}"/><text class="sm" x="{X(x)}" y="{Y(y) - 15}" text-anchor="middle">L{i}</text>')
    for k, (x, y) in D["buttons"].items():
        b.append(f'<rect class="h" x="{X(x) - 3 * s}" y="{Y(y) - 3 * s}" width="{6 * s}" height="{6 * s}"/><text class="sm" x="{X(x) - 3.5 * s - 4}" y="{Y(y) + 3}" text-anchor="end">{k}</text>')
    for i, (x, y) in enumerate(D["pcb_screws"], 1):
        b.append(f'<circle class="o" cx="{X(x)}" cy="{Y(y)}" r="{1.1 * s}"/><circle class="h" cx="{X(x)}" cy="{Y(y)}" r="{D["pcb_post_d"] / 2 * s}" stroke-dasharray="2 2"/>'
                 f'<text class="sm" x="{X(x) + 12}" y="{Y(y) + (12 if y < 40 else -6)}">H{i} ({x:g}, {y:g})</text>')
    b.append(dim_h(ox, ox + L * s, oy - 16, f"{L:g}"))
    b.append(dim_v(ox - 16, oy, oy + W_ * s, f"{W_:g}"))
    yl = oy + W_ * s + 30
    items = [("o", f"Ø2.2 non-plated M2 hole; dashed ring = Ø{D['pcb_post_d']:g} post / screw-head keep-out"),
             ("t", "tube (dashed = Ø19.4 courtyard) and lamp positions; top side carries only tubes, lamps and switches"),
             ("h", "switch: pressed from the case top through a printed rod")]
    for i, (c, t) in enumerate(items):
        b.append(f'<line class="{c}" x1="{ox}" y1="{yl + i * 18 - 4}" x2="{ox + 24}" y2="{yl + i * 18 - 4}"/><text class="sm" x="{ox + 32}" y="{yl + i * 18}">{t}</text>')
    (IMG / "pcb_drawing.svg").write_text(svg(ox * 2 + L * s, yl + 60, "".join(b), "PCB mechanical drawing"))


def box(x, y, w, h, title, lines, state):
    col = {"ready": OK, "blocked": HV, "waits": MUTE}[state]
    label = {"ready": "READY", "blocked": "BLOCKED", "waits": "AFTER PCB"}[state]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{PANEL}" stroke="{col}" stroke-width="{2 if state != "waits" else 1.2}"/>',
           f'<text x="{x + 14}" y="{y + 24}" fill="{INK}" font-size="14" font-weight="600">{title}</text>',
           f'<rect x="{x + w - 14 - len(label) * 7.2}" y="{y + 10}" width="{len(label) * 7.2 + 4}" height="18" rx="9" fill="{col}" opacity=".18"/>',
           f'<text x="{x + w - 12}" y="{y + 23}" fill="{col}" font-size="10.5" font-weight="700" text-anchor="end">{label}</text>']
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x + 14}" y="{y + 46 + i * 16}" fill="{MUTE}" font-size="11.5">{ln}</text>')
    return "".join(out)


def make_it():
    n_lines = sum(1 for _ in csv.DictReader(open(ROOT / "hardware" / "BOM.csv")))
    n_parts = sum(int(r["qty"]) for r in csv.DictReader(open(ROOT / "hardware" / "BOM.csv")))
    W_, gap, bw, bh = 1000, 20, 300, 112
    cells = [
        ("1  Buy parts", [f"hardware/BOM.csv: {n_lines} lines, {n_parts} parts", "hardware/BOM_mechanical.csv", "safety items: rating or better only"], "ready"),
        ("2  3D print (PETG)", ["cad/print/*.3mf plates", "coupons, inner case, floor, rods", "fits a Bambu Lab P1S (256 mm)"], "ready"),
        ("3  Cut acrylic + brass", ["cad/dxf/Window_panel_3mm_1to1.dxf", "cad/dxf/Brass_bezel_1mm_1to1.dxf", "laser / waterjet service or by hand"], "ready"),
        ("4  Woodwork", ["cad/dxf/Wood_boards_1to1.dxf", "5 walnut boards, 45° mitres", "docs/WOODWORK.md, oil finish"], "ready"),
        ("5  PCB fabrication", ["hardware/ KiCad project", "not routed yet: no Gerbers", "scripts/make_fab_outputs.sh gate"], "blocked"),
        ("6  Assemble + program", ["docs/BUILD_GUIDE.md stages 1-4", "LV first, HV last, one tube first", "firmware compiles; never run"], "waits"),
        ("7  Brass feet", ["cad/step/14_brass_foot.step", "14 mm brass bar, 8 mm slices", "or print in silk brass"], "ready"),
        ("8  Enclose", ["12 V pigtail + clamp, CR2032", "neon leads sleeved >=300 V", "M2 screws only"], "ready"),
        ("9  Label, test, record", ["docs/labels.pdf, TEST_RECORD.csv", "PASS / FIX / STOP per step", "discharge gate every time"], "ready"),
    ]
    b = [f'<text class="ti" x="24" y="36">Make it: what to send where</text>',
         f'<text class="sm" x="24" y="54">Every input is an open file in this repository. The PCB is the one blocked step: it must be routed and reviewed before Gerbers exist.</text>']
    for i, (t, lines, st) in enumerate(cells):
        r, c = divmod(i, 3)
        x = 24 + c * (bw + gap + 12)
        y = 72 + r * (bh + gap)
        b.append(box(x, y, bw + 12, bh, t, lines, st))
    (IMG / "make_it.svg").write_text(svg(W_ + 48, 72 + 3 * (bh + gap) + 6, "".join(b), "Manufacturing flow"))


def build_flow():
    stages = [("0", "Fit coupons", "print, check tube, tap M2", "ok"), ("1", "Low voltage", "12 V, polarity, V5", "ok"),
              ("2", "Logic + RTC", "no HV module; fault latch", "ok"), ("!", "HV gate", "experienced reviewer signs", "gate"),
              ("3", "HV supply", "170 V, measure discharge", "hv"), ("4", "Tubes", "one digit, then all six", "hv"),
              ("5", "Thermal", "2 h closed case", "hv"), ("6", "Close case", "wood box on, window in, case over", "ok"), ("7", "Record", "VALIDATION.md", "ok")]
    bw, bh, gap = 104, 92, 10
    W_ = 48 + 9 * bw + 8 * gap
    b = [f'<text class="ti" x="24" y="34">Build stages: each ends in PASS, FIX or STOP</text>']
    for i, (n, t, sub, k) in enumerate(stages):
        x, y = 24 + i * (bw + gap), 54
        col = {"ok": GLOW, "hv": HV, "gate": "#ffd400"}[k]
        b.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{PANEL}" stroke="{col}" stroke-width="{2.4 if k == "gate" else 1.6}"/>')
        b.append(f'<circle cx="{x + 20}" cy="{y + 22}" r="12" fill="{col}"/><text x="{x + 20}" y="{y + 27}" fill="{BG}" font-size="13" font-weight="700" text-anchor="middle">{n}</text>')
        b.append(f'<text x="{x + 10}" y="{y + 54}" fill="{INK}" font-size="12.5" font-weight="600">{t}</text>')
        words, line, ys = sub.split(), "", y + 72
        for wd in words:
            if len(line + " " + wd) > 16:
                b.append(f'<text x="{x + 10}" y="{ys}" fill="{MUTE}" font-size="10.5">{line.strip()}</text>'); ys += 13; line = ""
            line += " " + wd
        b.append(f'<text x="{x + 10}" y="{ys}" fill="{MUTE}" font-size="10.5">{line.strip()}</text>')
        if i < len(stages) - 1:
            b.append(f'<path d="M{x + bw + 1} {y + bh / 2}h{gap - 2}" stroke="{MUTE}" stroke-width="1.5" marker-end="url(#ar)"/>')
    y = 54 + bh + 26
    for xo, c, t in [(24, GLOW, "low voltage"), (170, HV, "about 170 V present: guarded, measure before touching"), (560, "#ffd400", "gate: nothing HV until signed")]:
        b.append(f'<rect x="{xo}" y="{y - 10}" width="14" height="12" rx="3" fill="{c}"/><text x="{xo + 20}" y="{y}" fill="{MUTE}" font-size="11.5">{t}</text>')
    (IMG / "build_flow.svg").write_text(svg(W_, y + 20, "".join(b), "Build stages"))


if __name__ == "__main__":
    dimensions(); pcb(); make_it(); build_flow()
    print("wrote docs/img/dimensions.svg, pcb_drawing.svg, make_it.svg, build_flow.svg")
