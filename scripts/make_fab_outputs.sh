#!/usr/bin/env bash
# make_fab_outputs.sh - produce the PCB fabrication package (Gerbers, drill, placement, BOM) ONLY when the release
# gate passes. This is how the brief's rule "generate Gerbers/drills only after successful native review" is enforced.
#
# Gate (all must pass):
#   1. hardware/Nixie_RevC.kicad_pcb exists (the routed board; the *_placement board never qualifies)
#   2. it has copper tracks and no PLACEHOLDER footprints
#   3. native KiCad DRC (pcbnew) reports 0 violations and 0 unconnected items
#   4. hardware/REVIEW_SIGNOFF.md is completely filled in and ends with "Approved for fabrication: yes"
# Output: fab/Nixie_RevC_fab_<commit>.zip plus its SHA-256. Needs KiCad 7+ (kicad-cli and the pcbnew Python module).
set -euo pipefail
cd "$(dirname "$0")/.."
PCB="hardware/Nixie_RevC.kicad_pcb"
SIGN="hardware/REVIEW_SIGNOFF.md"
fail() { echo "RELEASE GATE: STOP - $1"; echo "No fabrication files were made. See docs/MANUFACTURING.md."; exit 1; }

[ -f "$PCB" ] || fail "$PCB does not exist yet (the board has not been routed; the placement-only board cannot be fabricated)"
grep -q "(segment" "$PCB" || fail "$PCB has no copper tracks"
! grep -q "PLACEHOLDER_" "$PCB" || fail "$PCB still uses PLACEHOLDER footprints"
grep -q "^Approved for fabrication: yes" "$SIGN" || fail "$SIGN is not approved"
EMPTY="$(grep -cE '^\| [^|]+ \|[[:space:]]*\|$' "$SIGN" || true)"
[ "$EMPTY" = "0" ] || fail "$SIGN has $EMPTY empty field(s)"
command -v kicad-cli >/dev/null || fail "kicad-cli not found"

mkdir -p hardware/reports
/usr/bin/python3 - "$PCB" <<'PY' || fail "native DRC did not pass (see hardware/reports/release_native_drc.rpt)"
import re, sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
units = getattr(pcbnew, "EDA_UNITS_MILLIMETRES", getattr(pcbnew, "EDA_UNITS_MM", None))
rpt = "hardware/reports/release_native_drc.rpt"
pcbnew.WriteDRCReport(b, rpt, units, True)
t = open(rpt).read()
v = int(re.search(r"Found (\d+) DRC violations", t).group(1))
u = int(re.search(r"Found (\d+) unconnected", t).group(1))
print(f"native DRC (pcbnew {pcbnew.Version()}): {v} violations, {u} unconnected")
sys.exit(0 if v == 0 and u == 0 else 1)
PY

REV="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
OUT="fab/Nixie_RevC_fab_$REV"; rm -rf "$OUT"; mkdir -p "$OUT/gerbers"
kicad-cli pcb export gerbers -o "$OUT/gerbers/" \
  -l F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts "$PCB"
kicad-cli pcb export drill -o "$OUT/gerbers/" --format excellon --excellon-units mm --generate-map --map-format pdf "$PCB"
kicad-cli pcb export pos -o "$OUT/placement_both_sides.csv" --side both --format csv --units mm "$PCB"
cp hardware/BOM.csv hardware/BOM_mechanical.csv "$SIGN" docs/MANUFACTURING.md "$OUT/"
(cd fab && zip -qr "$(basename "$OUT").zip" "$(basename "$OUT")" && sha256sum "$(basename "$OUT").zip" > "$(basename "$OUT").zip.sha256")
echo "Fabrication package: $OUT.zip (SHA-256 in $OUT.zip.sha256)"
