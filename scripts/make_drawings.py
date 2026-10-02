#!/usr/bin/env python3
"""make_drawings.py - dimensioned drawings and flow diagrams generated from cad/DIMENSIONS.json and the BOM.

Writes (docs/img/):
  dimensions.svg   enclosure top and front views with key dimensions
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
    s = 3.2                     # px per mm
    L, W_, H = D["base_l"], D["base_w"], D["base_h"]
    ox, oy = 70, 96             # top view origin (front-left corner at bottom-left)
    Y = lambda y: oy + (W_ - y) * s
    b = [f'<text class="ti" x="24" y="34">Enclosure: top and front views (mm)</text>',
         f'<text class="sm" x="24" y="52">From cad/DIMENSIONS.json. Fit allowances marked VERIFY there are unmeasured.</text>',
         f'<rect class="o" x="{ox}" y="{oy}" width="{L * s}" height="{W_ * s}" rx="{D["corner_r"] * s}"/>']
    for i, (x, y) in enumerate(D["tube_centers"], 1):
        b.append(f'<circle class="t" cx="{ox + x * s}" cy="{Y(y)}" r="{D["tube_opening_d"] / 2 * s}"/>'
                 f'<text class="sm" x="{ox + x * s}" y="{Y(y) + 4}" text-anchor="middle">T{i}</text>')
    for x, y in D["separator_centers"]:
        b.append(f'<circle class="t" cx="{ox + x * s}" cy="{Y(y)}" r="{D["separator_opening_d"] / 2 * s}"/>')
    for k, (x, y) in D["buttons"].items():
        b.append(f'<circle class="h" cx="{ox + x * s}" cy="{Y(y)}" r="{D["button_opening_d"] / 2 * s}"/>'
                 f'<text class="sm" x="{ox + x * s - 9}" y="{Y(y) + 3}" text-anchor="end">{k}</text>')
    for x, y in D["case_screws"]:
        b.append(f'<circle class="h" cx="{ox + x * s}" cy="{Y(y)}" r="{D["m2_clearance_d"] / 2 * s}"/>')
    b.append(dim_h(ox, ox + L * s, oy - 14, f"{L:g}"))
    b.append(dim_v(ox - 14, oy, oy + W_ * s, f"{W_:g}"))
    t = D["tube_centers"]
    yb = oy + W_ * s + 22
    b.append(dim_h(ox + t[0][0] * s, ox + t[1][0] * s, yb, f"{t[1][0] - t[0][0]:g}"))
    b.append(dim_h(ox + t[1][0] * s, ox + t[2][0] * s, yb, f"{t[2][0] - t[1][0]:g}"))
    b.append(dim_h(ox, ox + t[0][0] * s, yb, f"{t[0][0]:g}"))
    b.append(f'<text class="dt" x="{ox + t[0][0] * s}" y="{Y(t[0][1]) - D["tube_opening_d"] / 2 * s - 6}" text-anchor="middle">Ø{D["tube_opening_d"]:g}</text>')
    b.append(f'<text class="dt" x="{ox + L * s + 12}" y="{Y(t[0][1]) + 4}">tube row y = {t[0][1]:g}</text>')
    b.append(f'<text class="dt" x="{ox + L * s - 12}" y="{oy + W_ * s - 8}" text-anchor="end">corner R{D["corner_r"]:g} · 4 × M2 case screws</text>')
    # front view
    fy = yb + 70
    tube_top = D["pcb_top_z"] + D["tube_spacer_h"] + D["tube_glass_h"]
    Z = lambda z: fy + (tube_top - z) * s
    b.append(f'<text class="lb" x="{ox}" y="{fy - 12}">Front view</text>')
    b.append(f'<rect class="o" x="{ox}" y="{Z(H)}" width="{L * s}" height="{H * s}" rx="4"/>')
    for x, _ in t:
        g = D["tube_glass_d"] / 2
        b.append(f'<rect class="t" x="{ox + (x - g) * s}" y="{Z(tube_top)}" width="{2 * g * s}" height="{(tube_top - H) * s}" rx="{g * s}"/>')
    b.append(dim_v(ox - 14, Z(H), Z(0), f"{H:g}"))
    b.append(dim_v(ox + L * s + 40, Z(tube_top), Z(0), f"≈{tube_top:.0f}"))
    b.append(f'<text class="sm" x="{ox}" y="{Z(0) + 20}">Glass Ø{D["tube_glass_d"]:g} × {D["tube_glass_h"]:g} on {D["tube_spacer_h"]:g} mm factory spacers; PCB top at z = {D["pcb_top_z"]:g}</text>')
    h = Z(0) + 40
    (IMG / "dimensions.svg").write_text(svg(ox * 2 + L * s + 40, h, "".join(b), "Enclosure dimensions"))


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
        b.append(f'<circle class="t" cx="{X(x)}" cy="{Y(y)}" r="{D["tube_opening_d"] / 2 * s}" stroke-dasharray="3 3"/>'
                 f'<circle class="h" cx="{X(x)}" cy="{Y(y)}" r="{(D["tube_opening_d"] / 2 + D["baffle_wall_t"]) * s}" stroke-dasharray="1 3"/>'
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
             ("t", "tube (dashed = Ø19.4 opening) and lamp positions"),
             ("h", "dotted = 21.8 mm baffle ring: keep the top side clear")]
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
        ("2  3D print (PETG)", ["cad/print/*.3mf plates", "coupons first, then hood or frame", "fits a 256 mm bed (Bambu Lab P1S)"], "ready"),
        ("3  Laser cut", ["cad/Acrylic_top_3mm_1to1.dxf", "3 mm clear CAST acrylic", "clear-top option only"], "ready"),
        ("4  PCB fabrication", ["hardware/ KiCad project", "not routed yet: no Gerbers", "scripts/make_fab_outputs.sh gate"], "blocked"),
        ("5  Assemble", ["docs/BUILD_GUIDE.md stages 1-4", "LV first, HV last, one tube first", "discharge gate every time"], "waits"),
        ("6  Program", ["firmware/Nixie_RevC/*.ino", "or build/Nixie_RevC.hex + avrdude", "compiles; never run on a board"], "ready"),
        ("7  Wire and enclose", ["12 V pigtail + clamp, CR2032", "neon leads sleeved >=300 V", "M2 screws only"], "ready"),
        ("8  Label", ["docs/labels.pdf (print at 100 %)", "HV warning + rating plate", "markers near PS1 and JP1"], "ready"),
        ("9  Test and record", ["hardware/TEST_RECORD.csv", "PASS / FIX / STOP per step", "docs/VALIDATION.md"], "ready"),
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
              ("5", "Thermal", "2 h closed case", "hv"), ("6", "Enclosure", "no HV visible", "ok"), ("7", "Record", "VALIDATION.md", "ok")]
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
