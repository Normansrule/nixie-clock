#!/usr/bin/env python3
"""make_kicad.py - generate the Rev C KiCad files from the design tables, then check them
with KiCad's own code.

Generates (in hardware/):
  Nixie_RevC.kicad_sym           local symbol library (generic box symbols, one per part type)
  Nixie_RevC.kicad_sch           root sheet (power, logic, level shifters, HV supply, RTC)
  digit_1.kicad_sch              U1 bank: T1-T3, L1, anode/lamp resistors
  digit_2.kicad_sch              U2 bank: T4-T6, L2, anode/lamp resistors
  Nixie_RevC.pretty/             PLACEHOLDER footprints (courtyard + fab outline, NO pads)
  sym-lib-table, fp-lib-table    project-local library tables
  Nixie_RevC.kicad_dru           custom rules for the future routed board (HV clearance)
  Nixie_RevC.kicad_pro           project file
  Nixie_RevC_placement.kicad_pcb board outline, M2 holes and placeholder courtyards (no copper)
  reports/                       native netlist export + native DRC report of the placement board

Tested with KiCad 7.0.11. A compatibility shim covers the KiCad 8+ footprint-graphics API, but it
has not been run on KiCad 8 or newer: check the reports if you regenerate on a newer KiCad.

Native checks run here (need KiCad 7.x or newer: kicad-cli and the pcbnew Python module):
  1. kicad-cli exports a netlist from the generated schematic; every net is compared with
     NET_MAP.csv. This proves the schematic FILES encode the net map. It is not ERC.
  2. pcbnew.WriteDRCReport runs DRC on the placement board (outline, holes, courtyards).
     There is no copper, so this says nothing about clearances, routing or connectivity.
Nothing here is a routed board and no Gerbers are produced.
"""
import csv
import json
import re
import subprocess
import sys
import uuid
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware"
REP = HW / "reports"
REP.mkdir(parents=True, exist_ok=True)
DIM = json.loads((ROOT / "cad" / "DIMENSIONS.json").read_text())
LIB = "Nixie_RevC"
NS = uuid.UUID("6f1c1d8e-0c5b-4f0e-9a51-3f7c5a0d2c11")
U = lambda *k: str(uuid.uuid5(NS, "/".join(map(str, k))))  # deterministic UUIDs

rows = list(csv.DictReader(open(HW / "NET_MAP.csv")))
place = {p["ref"]: p for p in csv.DictReader(open(HW / "COMPONENT_PLACEMENT.csv"))}

# Arduino Nano header numbering (KiCad Module:Arduino_Nano): silk label -> pin number
NANO = ["D1/TX", "D0/RX", "RESET", "GND", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12",
        "D13", "3V3", "AREF", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "5V", "RESET2", "GND2", "VIN"]
NANO_NUM = {n: str(i + 1) for i, n in enumerate(NANO)}


def pin_number(ref, pin):
    return NANO_NUM[pin] if ref == "A1" else pin


# ---------------- symbol types ----------------
def sym_type(ref, value):
    v = value
    if ref.startswith("RA") or ref.startswith("RL"):
        return "R_1W_axial"
    if ref.startswith("R"):
        return "R"
    if ref in ("C5",):
        return "C_polarised"
    if ref.startswith("C"):
        return "C"
    if ref.startswith("QP"):
        return "PMOS_GSD"
    if ref == "QL5":
        return "PNP_BCE"
    if ref.startswith("Q"):
        return "NPN_BCE"
    if ref.startswith("TP"):
        return "TestPad"
    if ref.startswith("T"):
        return "IN-14"
    if ref.startswith("L"):
        return "NE-2"
    if ref.startswith("SW"):
        return "SW_B3F_4pin"
    if ref.startswith("TP"):
        return "TestPad"
    if ref.startswith("J") or ref == "JP1":
        return "Conn_1x02"
    if ref == "F1":
        return "PTC"
    if ref.startswith("U") and "HV5522" in v:
        return "HV5522PJ-G"
    if ref == "U3":
        return "DS3231SN"
    if ref == "A1":
        return "Arduino_Nano_Classic"
    if ref == "PS1":
        return "NCH8200HV"
    raise ValueError(ref)


refs = OrderedDict()
for r in rows:
    refs.setdefault(r["ref"], []).append(r)
types = {ref: sym_type(ref, place[ref]["value"]) for ref in refs}

# Pin list per type: union over all refs of that type, ordered as first seen.
type_pins = defaultdict(OrderedDict)
for ref, rs in refs.items():
    for r in rs:
        type_pins[types[ref]].setdefault(pin_number(ref, r["pin"]), r["pin_name"] or r["pin"])
for n, name in zip(range(1, 31), NANO):
    type_pins["Arduino_Nano_Classic"].setdefault(str(n), name)
type_pins["Arduino_Nano_Classic"] = OrderedDict(sorted(type_pins["Arduino_Nano_Classic"].items(), key=lambda kv: int(kv[0])))
if "HV5522PJ-G" in type_pins:
    type_pins["HV5522PJ-G"] = OrderedDict(sorted(type_pins["HV5522PJ-G"].items(), key=lambda kv: int(kv[0])))
if "DS3231SN" in type_pins:
    type_pins["DS3231SN"] = OrderedDict(sorted(type_pins["DS3231SN"].items(), key=lambda kv: int(kv[0])))

G = 2.54
FONT = '(effects (font (size 1.27 1.27)))'
HIDE = '(effects (font (size 1.27 1.27)) hide)'


def sym_geometry(t):
    """Returns (half_width, [(number, name, side, y)], half_height). Left side first."""
    pins = list(type_pins[t].items())
    n = len(pins)
    left = (n + 1) // 2
    width = max(4, max(len(nm) for _, nm in pins) * 1.0 + 2)  # grid units
    hw = G * int(round(width))
    geo = []
    for i, (num, nm) in enumerate(pins):
        side = "L" if i < left else "R"
        k = i if side == "L" else i - left
        geo.append((num, nm, side, -G * k))
    rows_n = left
    top = G
    bottom = -G * rows_n
    return hw, geo, top, bottom


def sym_body(t, prefixed):
    hw, geo, top, bottom = sym_geometry(t)
    name = f"{LIB}:{t}" if prefixed else t
    out = [f'(symbol "{name}" (pin_names (offset 0.508)) (in_bom yes) (on_board yes)',
           f'  (property "Reference" "X" (at 0 {top + G:.2f} 0) {FONT})',
           f'  (property "Value" "{t}" (at 0 {bottom - G:.2f} 0) {FONT})',
           f'  (property "Footprint" "" (at 0 0 0) {HIDE})',
           f'  (property "Datasheet" "" (at 0 0 0) {HIDE})',
           f'  (symbol "{t}_0_1" (rectangle (start {-hw:.2f} {top:.2f}) (end {hw:.2f} {bottom:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))',
           f'  (symbol "{t}_1_1"']
    for num, nm, side, y in geo:
        x, ang = (-hw - G, 0) if side == "L" else (hw + G, 180)
        out.append(f'    (pin passive line (at {x:.2f} {y:.2f} {ang}) (length {G}) (name "{nm}" {FONT}) (number "{num}" {FONT}))')
    out.append("  )")
    out.append(")")
    return "\n".join(out)


def pin_points(t, X, Y):
    hw, geo, _, _ = sym_geometry(t)
    pts = {}
    for num, nm, side, y in geo:
        x = -hw - G if side == "L" else hw + G
        pts[num] = (round(X + x, 2), round(Y - y, 2), side)
    return pts


# ---------------- symbol library file ----------------
lib = ['(kicad_symbol_lib (version 20220914) (generator nixie_revc_make_kicad)']
for t in sorted(set(types.values())):
    lib.append(sym_body(t, prefixed=False))
lib.append(")")
(HW / f"{LIB}.kicad_sym").write_text("\n".join(lib) + "\n")

# ---------------- schematic sheets ----------------
DIGIT = {1: ["U1", "C1", "C3", "T1", "T2", "T3", "L1", "RA1", "RA2", "RA3", "RL1"],
         2: ["U2", "C2", "C4", "T4", "T5", "T6", "L2", "RA4", "RA5", "RA6", "RL2"]}
in_child = {r: k for k, lst in DIGIT.items() for r in lst}
ROOT_UUID = U("root")
SHEET_UUID = {k: U("sheet", k) for k in DIGIT}
FILE_UUID = {k: U("file", k) for k in DIGIT}
fp_of = {ref: place[ref]["footprint_intent"] for ref in refs}


def net_of(ref):
    return {pin_number(ref, r["pin"]): r["net"] for r in refs[ref]}


PAPER_W = {"A0": 1189, "A1": 841, "A2": 594, "A3": 420}


def layout(ref_list, paper):
    """Simple shelf packing on a 2.54 grid."""
    pos = {}
    x, y, row_h = 30 * G, 20 * G, 0
    for ref in ref_list:
        hw, geo, top, bottom = sym_geometry(types[ref])
        w = 2 * hw + 14 * G   # room for labels
        h = top - bottom + 6 * G
        if x + w > PAPER_W[paper] - 20 * G:
            x, y, row_h = 30 * G, y + row_h, 0
        pos[ref] = (round((x + w / 2) / G) * G, round((y - top + 2 * G) / G) * G)
        x += w
        row_h = max(row_h, h)
    return pos


def sheet_text(ref_list, file_uuid, path, paper, extra=""):
    used_types = sorted({types[r] for r in ref_list})
    out = [f'(kicad_sch (version 20230121) (generator nixie_revc_make_kicad)',
           f'  (uuid {file_uuid})',
           f'  (paper "{paper}")',
           '  (title_block (title "Six-Tube Nixie Clock - Rev C") (rev "C") (company "UNVALIDATED ENGINEERING PROTOTYPE")',
           '    (comment 1 "Generated by scripts/make_kicad.py from hardware/NET_MAP.csv - connections by global labels")',
           '    (comment 2 "HV170 is about 170 V DC: hazardous. See docs/SAFETY.md"))',
           '  (lib_symbols']
    for t in used_types:
        out.append("\n".join("    " + l for l in sym_body(t, prefixed=True).splitlines()))
    out.append("  )")
    pos = layout(ref_list, paper)
    for ref in ref_list:
        t = types[ref]
        X, Y = pos[ref]
        nets = net_of(ref)
        hw, geo, top, bottom = sym_geometry(t)
        val = place[ref]["value"].replace('"', "'")
        out.append(f'  (symbol (lib_id "{LIB}:{t}") (at {X:.2f} {Y:.2f} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {U("sym", ref)})')
        out.append(f'    (property "Reference" "{ref}" (at {X:.2f} {Y - top - G:.2f} 0) {FONT})')
        out.append(f'    (property "Value" "{val}" (at {X:.2f} {Y - bottom + G:.2f} 0) {FONT})')
        out.append(f'    (property "Footprint" "{fp_of[ref]}" (at {X:.2f} {Y:.2f} 0) {HIDE})')
        out.append(f'    (property "Datasheet" "" (at {X:.2f} {Y:.2f} 0) {HIDE})')
        for num, _, _, _ in geo:
            out.append(f'    (pin "{num}" (uuid {U("pin", ref, num)}))')
        out.append(f'    (instances (project "{LIB}" (path "{path}" (reference "{ref}") (unit 1))))')
        out.append("  )")
        for num, (px, py, side) in pin_points(t, X, Y).items():
            net = nets.get(num)
            if net is None or "_NC" in net or net.endswith("_NC"):
                out.append(f'  (no_connect (at {px:.2f} {py:.2f}) (uuid {U("nc", ref, num)}))')
                continue
            ang, just = (180, "right") if side == "L" else (0, "left")
            out.append(f'  (global_label "{net}" (shape passive) (at {px:.2f} {py:.2f} {ang}) (fields_autoplaced)'
                       f' (effects (font (size 1.27 1.27)) (justify {just})) (uuid {U("gl", ref, num)})'
                       f' (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {px:.2f} {py:.2f} 0) {HIDE}))')
    out.append(extra)
    out.append(")")
    return "\n".join(out) + "\n"


root_refs = [r for r in refs if r not in in_child]
sheets = []
for k in DIGIT:
    x, y = (20 + 40 * (k - 1)) * G, 190 * G
    sheets.append(
        f'  (sheet (at {x:.2f} {y:.2f}) (size {30 * G:.2f} {10 * G:.2f}) (fields_autoplaced) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid {SHEET_UUID[k]})\n'
        f'    (property "Sheetname" "digit_{k}" (at {x:.2f} {y - 0.7:.2f} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))\n'
        f'    (property "Sheetfile" "digit_{k}.kicad_sch" (at {x:.2f} {y + 10 * G + 0.6:.2f} 0) (effects (font (size 1.27 1.27)) (justify left top)))\n'
        f'    (instances (project "{LIB}" (path "/{ROOT_UUID}" (page "{k + 1}"))))\n'
        f'  )')
root_extra = "\n".join(sheets) + '\n  (sheet_instances (path "/" (page "1")))'
(HW / f"{LIB}.kicad_sch").write_text(sheet_text(root_refs, ROOT_UUID, f"/{ROOT_UUID}", "A1", root_extra))
for k, lst in DIGIT.items():
    (HW / f"digit_{k}.kicad_sch").write_text(sheet_text(lst, FILE_UUID[k], f"/{ROOT_UUID}/{SHEET_UUID[k]}", "A2"))

# ---------------- library tables, rules, project ----------------
(HW / "sym-lib-table").write_text(f'(sym_lib_table\n  (lib (name "{LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{LIB}.kicad_sym")(options "")(descr "Rev C local symbols (generated)"))\n)\n')
(HW / "fp-lib-table").write_text(f'(fp_lib_table\n  (lib (name "{LIB}")(type "KiCad")(uri "${{KIPRJMOD}}/{LIB}.pretty")(options "")(descr "Rev C PLACEHOLDER footprints: courtyards only, no pads"))\n)\n')
(HW / f"{LIB}.kicad_dru").write_text('''(version 1)
# Rev C custom rules for the FUTURE routed board. Starting values, not a safety certification.
# Assign nets HV170, ANODE*, T*_K*, LAMP*_A, SEP*_K, HV_BLEED_MID, HV_SENSE_MID to a net class named "HV".
# Check every value against IPC-2221B Table 6-1 (and your fab's capability) before routing.

(rule "HV to non-HV clearance"
  (condition "A.NetClass == 'HV' && B.NetClass != 'HV'")
  (constraint clearance (min 1.0mm)))

(rule "HV to HV clearance"
  (condition "A.NetClass == 'HV' && B.NetClass == 'HV'")
  (constraint clearance (min 0.65mm)))

(rule "HV hole to non-HV copper"
  (condition "A.NetClass == 'HV' && B.NetClass != 'HV'")
  (constraint hole_clearance (min 1.0mm)))

(rule "HV parts stay clear of the board edge"
  (condition "A.NetClass == 'HV'")
  (constraint edge_clearance (min 2.0mm)))

(rule "Top-side keep-out ring under the baffle collars"
  (condition "A.insideArea('BAFFLE_KEEPOUT')")
  (constraint disallow footprint))
''')
pro = {
    "meta": {"filename": f"{LIB}.kicad_pro", "version": 1},
    "board": {"design_settings": {"rules": {"min_clearance": 0.2}}},
    "net_settings": {"classes": [
        {"name": "Default", "clearance": 0.2, "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3,
         "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3, "microvia_drill": 0.1,
         "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"},
        {"name": "HV", "clearance": 1.0, "track_width": 0.3, "via_diameter": 0.8, "via_drill": 0.4,
         "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "microvia_diameter": 0.3, "microvia_drill": 0.1,
         "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(255, 90, 40, 0.800)", "schematic_color": "rgba(255, 90, 40, 1.000)"}],
        "meta": {"version": 3},
        "netclass_patterns": [{"netclass": "HV", "pattern": p} for p in
                              ("HV170", "ANODE*", "T?_K?", "LAMP?_A", "SEP?_K", "HV_BLEED_MID", "HV_SENSE_MID")]},
    "sheets": [[ROOT_UUID, ""], [SHEET_UUID[1], "digit_1"], [SHEET_UUID[2], "digit_2"]],
    "text_variables": {"REVISION": "C", "STATUS": "UNVALIDATED ENGINEERING PROTOTYPE"},
}
(HW / f"{LIB}.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")

# ---------------- native check 1: netlist export and comparison ----------------
net_file = REP / "Nixie_RevC_native_netlist.net"
res = subprocess.run(["kicad-cli", "sch", "export", "netlist", "-o", str(net_file), str(HW / f"{LIB}.kicad_sch")],
                     capture_output=True, text=True)
print(res.stdout.strip(), res.stderr.strip())
txt = net_file.read_text()
native = defaultdict(set)
for m in re.finditer(r'\(net \(code "?\d+"?\) \(name "([^"]*)"\)(.*?)\)\s*(?=\(net |\)\s*\)\s*$)', txt, re.S):
    name = m.group(1).lstrip("/")
    for ref, pin in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', m.group(2)):
        native[name].add((ref, pin))
expected = defaultdict(set)
for r in rows:
    if "_NC" in r["net"]:
        continue
    expected[r["net"]].add((r["ref"], pin_number(r["ref"], r["pin"])))
mism = []
for n, nodes in expected.items():
    if native.get(n) != nodes:
        mism.append((n, sorted(nodes ^ native.get(n, set()))[:6]))
extra = [n for n, nodes in native.items() if n not in expected and not n.startswith("unconnected-")]
lines = [f"native netlist: {len(native)} nets from kicad-cli {subprocess.run(['kicad-cli', 'version'], capture_output=True, text=True).stdout.strip()}",
         f"NET_MAP.csv:    {len(expected)} multi-use nets (NC nets excluded)",
         f"mismatched nets: {len(mism)}", f"extra native nets: {extra}"]
lines += [f"  MISMATCH {n}: {d}" for n, d in mism]
netcheck_ok = not mism and not extra
lines.append("NETLIST vs NET_MAP: " + ("MATCH" if netcheck_ok else "DIFFERENT"))
(REP / "netlist_vs_netmap.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))

# ---------------- placeholder footprints + placement board (pcbnew) ----------------
import pcbnew  # noqa: E402

MM = pcbnew.FromMM
OX, OY = 20.0, 20.0  # board origin on the page


def to_board(x, y):
    """Enclosure coordinates (Y toward the back) -> KiCad board coordinates (Y down, front at the bottom)."""
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + DIM["base_w"] - y))


SIZE = {  # courtyard envelopes (mm) for placeholder footprints: w, h or ("circle", d)
    "IN-14": ("circle", DIM["tube_opening_d"]), "NE-2": ("circle", DIM["separator_opening_d"]),
    "SW_B3F_4pin": (7.0, 7.0), "HV5522PJ-G": (18.0, 18.0), "Arduino_Nano_Classic": (44.0, 19.0),
    "NCH8200HV": (30.0, 21.0), "DS3231SN": (11.0, 11.5), "PTC": (5.6, 4.0), "PMOS_GSD": (3.4, 3.2),
    "NPN_BCE": (3.4, 3.2), "PNP_BCE": (3.4, 3.2), "Conn_1x02": (3.0, 5.6), "C_polarised": (7.0, 7.0),
    "R_1W_axial": (13.0, 3.2), "R": (3.0, 2.0), "C": (3.0, 2.0), "TestPad": (2.0, 2.0),
}


def placeholder(ref, t, value):
    fp = pcbnew.FOOTPRINT(None)
    fpid = pcbnew.LIB_ID(LIB, f"PLACEHOLDER_{t}")
    fp.SetFPID(fpid)
    fp.SetReference(ref)
    fp.SetValue(value)
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    s = SIZE[t]
    for layer, grow in ((pcbnew.F_CrtYd, 0.0), (pcbnew.F_Fab, -0.25)):
        if s[0] == "circle":
            fp_circle(fp, layer, s[1] / 2 + grow, 0.05 if layer == pcbnew.F_CrtYd else 0.1)
        else:
            fp_rect(fp, layer, s[0] + 2 * grow, s[1] + 2 * grow, 0.05 if layer == pcbnew.F_CrtYd else 0.1)
    if t == "IN-14":  # baffle collar footprint on the top side: keep this ring free of parts
        fp_circle(fp, pcbnew.User_1, DIM["tube_opening_d"] / 2 + DIM["baffle_wall_t"], 0.1)
    # Through-board leads: reserve the area on the bottom side too.
    thru = {"IN-14": ("c", 7.0), "NE-2": ("c", 2.0), "SW_B3F_4pin": ("r", 7.0, 7.0)}.get(t)
    if thru and thru[0] == "c":
        fp_circle(fp, pcbnew.B_CrtYd, thru[1], 0.05)
    elif thru:
        fp_rect(fp, pcbnew.B_CrtYd, thru[1], thru[2], 0.05)
    return fp


def fp_shape(fp, kind, layer, w, a, b):
    """Footprint graphic that works on KiCad 7 (FP_SHAPE, local coords) and KiCad 8+ (PCB_SHAPE).
    Footprints are built at the origin and moved afterwards, so local and board coordinates agree."""
    if hasattr(pcbnew, "FP_SHAPE"):
        sh = pcbnew.FP_SHAPE(fp, kind)
        sh.SetLayer(layer)
        sh.SetWidth(MM(w))
        sh.SetStart0(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
        sh.SetEnd0(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
        sh.SetDrawCoord()
    else:
        sh = pcbnew.PCB_SHAPE(fp, kind)
        sh.SetLayer(layer)
        sh.SetWidth(MM(w))
        sh.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
        sh.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
    return sh


def fp_circle(fp, layer, r, w):
    sh = fp_shape(fp, pcbnew.SHAPE_T_CIRCLE, layer, w, (0, 0), (r, 0))
    fp.Add(sh)


def fp_rect(fp, layer, w_mm, h_mm, w):
    pts = [(-w_mm / 2, -h_mm / 2), (w_mm / 2, -h_mm / 2), (w_mm / 2, h_mm / 2), (-w_mm / 2, h_mm / 2)]
    for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
        sh = fp_shape(fp, pcbnew.SHAPE_T_SEGMENT, layer, w, (ax, ay), (bx, by))
        fp.Add(sh)


def mounting_hole(ref):
    fp = pcbnew.FOOTPRINT(None)
    fp.SetFPID(pcbnew.LIB_ID(LIB, "MountingHole_M2_NPTH_2.2mm"))
    fp.SetReference(ref)
    fp.SetValue("M2")
    fp.SetAttributes(pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_EXCLUDE_FROM_BOM)
    pad = pcbnew.PAD(fp)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)
    pad.SetShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(MM(2.2), MM(2.2)))
    pad.SetDrillSize(pcbnew.VECTOR2I(MM(2.2), MM(2.2)))
    pad.SetLayerSet(pad.UnplatedHoleMask())
    pad.SetNumber("")
    fp.Add(pad)
    for layer in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):   # post / screw-head contact area
        fp_circle(fp, layer, DIM["pcb_post_d"] / 2 + 0.25, 0.05)
    return fp


pretty = HW / f"{LIB}.pretty"
pretty.mkdir(exist_ok=True)
for f in pretty.glob("*.kicad_mod"):
    f.unlink()
saved = set()
board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
x0, y0 = DIM["pcb_offset_x"], DIM["pcb_offset_y"]
x1, y1 = x0 + DIM["pcb_l"], y0 + DIM["pcb_w"]
corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
    e = pcbnew.PCB_SHAPE(board)
    e.SetShape(pcbnew.SHAPE_T_SEGMENT)
    e.SetLayer(pcbnew.Edge_Cuts)
    e.SetWidth(MM(0.1))
    e.SetStart(to_board(ax, ay))
    e.SetEnd(to_board(bx, by))
    board.Add(e)
txt = pcbnew.PCB_TEXT(board)
txt.SetText("Nixie Rev C PLACEMENT ONLY - no copper - UNVALIDATED - do not fabricate")
txt.SetLayer(pcbnew.Cmts_User)
txt.SetPosition(to_board((x0 + x1) / 2, y1 + 6))
txt.SetTextSize(pcbnew.VECTOR2I(MM(2), MM(2)))
board.Add(txt)

for ref, p in place.items():
    if ref.startswith("H"):
        fp = mounting_hole(ref)
        if "MountingHole" not in saved:
            pcbnew.FootprintSave(str(pretty), fp)
            saved.add("MountingHole")
    else:
        t = types[ref]
        fp = placeholder(ref, t, p["value"])
        if t not in saved:
            pcbnew.FootprintSave(str(pretty), fp)
            saved.add(t)
    fp.Reference().SetLayer(pcbnew.F_Fab)
    fp.Value().SetLayer(pcbnew.F_Fab)
    fp.Value().SetVisible(False)
    for tx in (fp.Reference(), fp.Value()):
        tx.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        tx.SetTextThickness(MM(0.15))
    board.Add(fp)
    fp.SetPosition(to_board(float(p["x_mm"]), float(p["y_mm"])))
    fp.SetOrientationDegrees(float(p["rot_deg"]))
    if p["side"] == "bottom":
        fp.Flip(fp.GetPosition(), False)

pcb_path = HW / f"{LIB}_placement.kicad_pcb"
pcbnew.SaveBoard(str(pcb_path), board)
for junk in (HW / f"{LIB}_placement.kicad_prl", HW / f"{LIB}_placement.kicad_pro"):
    junk.unlink(missing_ok=True)

# ---------------- native check 2: DRC on the placement board ----------------
b2 = pcbnew.LoadBoard(str(pcb_path))
drc_path = REP / "placement_native_drc.rpt"
UNITS_MM = getattr(pcbnew, "EDA_UNITS_MILLIMETRES", getattr(pcbnew, "EDA_UNITS_MM", None))
ok = pcbnew.WriteDRCReport(b2, str(drc_path), UNITS_MM, True)
rep = drc_path.read_text()
n_viol = int(re.search(r"\*\* Found (\d+) DRC violations", rep).group(1)) if re.search(r"\*\* Found (\d+) DRC violations", rep) else -1
n_unc = int(re.search(r"\*\* Found (\d+) unconnected pads", rep).group(1)) if re.search(r"\*\* Found (\d+) unconnected pads", rep) else -1
n_foot = int(re.search(r"\*\* Found (\d+) Footprint errors", rep).group(1)) if re.search(r"\*\* Found (\d+) Footprint errors", rep) else -1
summary = f"placement board native DRC (pcbnew {pcbnew.Version()}): violations={n_viol}, unconnected={n_unc}, footprint errors={n_foot}"
print(summary)
(REP / "SUMMARY.txt").write_text(
    "Native KiCad checks run by scripts/make_kicad.py\n"
    "These are NOT ERC, and NOT DRC of a routed board. See docs/VALIDATION.md.\n\n"
    + "\n".join(lines) + "\n\n" + summary + "\n")
sys.exit(0 if (netcheck_ok and n_viol == 0) else 1)
