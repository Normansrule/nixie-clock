#!/usr/bin/env python3
"""make_requirements.py - Rev C requirements with traceability, written to docs/REQUIREMENTS.md and
hardware/REQUIREMENTS.csv from one list (edit the list here, then rerun).

Verification methods: I = Inspection, A = Analysis, D = Demonstration, T = Test.
Status words:
  "recorded"  a script in this repository checks the design files (see 'evidence'); NOT a physical result
  "open"      needs real parts, a board or a measurement (see 'stage' in docs/BUILD_GUIDE.md)
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# id, category, requirement, source, satisfied by (design element), method, evidence (recorded check), stage, status
R = [
    ("SAF-01", "Safety", "The clock takes power only from an external, isolated, regulated 12 V adapter. No mains wiring inside the enclosure.", "Brief invariant 0", "J1 pigtail, adapter line in BOM_mechanical.csv", "I", "BOM_mechanical.csv", "1, 6", "recorded"),
    ("SAF-02", "Safety", "No high-voltage (HV) copper, lead or module is reachable through any enclosure opening in normal use.", "Brief invariant 0", "Fully enclosed case: glazed window, rods filling the button holes (<=0.3 mm gap), cable filling the rear hole, screwed floor", "I", "tests/check_cad.py (model only)", "6", "open"),
    ("SAF-03", "Safety", "After power is removed the HV rail falls below 10 V within 60 s, confirmed by measurement every time before access.", "Brief invariant 0", "RH1+RH2 bleeder (220 kOhm), sense divider, SAFETY.md rule 3", "A, T", "tests/check_equations.py (discharge)", "3", "open"),
    ("SAF-04", "Safety", "Removing the HV_ARM shunt physically opens the converter's 12 V input.", "Brief invariant 0", "JP1 in series with QP2 and PS1 input", "I, T", "tests/check_design.py", "2", "recorded"),
    ("SAF-05", "Safety", "The HV converter stays off whenever the Nano is in reset or unprogrammed.", "Brief invariant 0", "RGP gate pull-up on QP2, RPD5 base pull-down on QE1", "I, T", "tests/check_design.py", "2", "recorded"),
    ("SAF-06", "Safety", "All tube outputs are blanked at start-up and whenever the Nano is in reset.", "Brief invariant 0", "RD1 pull-down on BL, POL tied HIGH, two-stage RUN shifter", "I, T", "tests/check_design.py", "2", "recorded"),
    ("SAF-07", "Safety", "No Nano output connects directly to an HV5522 input.", "Brief invariant 0", "QL1-QL5 level shifters", "I", "tests/check_design.py", "-", "recorded"),
    ("SAF-08", "Safety", "At most one cathode per tube is ever latched on, and unused driver outputs are never set.", "Brief invariant 0", "frameIsSafe() in display_core.h; unsafe frame latches a fault", "A, T", "tests/test_display_core.cpp", "4", "recorded"),
    ("SAF-09", "Safety", "Each tube anode is current-limited by a 22 kOhm 1 W resistor and each lamp by 220 kOhm 1 W.", "Brief invariant 0", "RA1-RA6, RL1, RL2 (PR01)", "I, A", "tests/check_design.py, tests/check_equations.py", "4", "recorded"),
    ("SAF-10", "Safety", "HV is sensed; outside 150-190 V the firmware turns HV off and latches a fault that survives resets until a deliberate CLEARFAULT.", "Brief invariant 0 + review", "RS1-RS3 to A0; hvService(), EEPROM fault latch", "A, T", "scripts/avr_compile_check.sh", "2, 3", "open"),
    ("SAF-11", "Safety", "The 12 V input is fused and protected against reverse polarity.", "Brief power path", "F1 PTC, QP1 P-MOSFET", "I, T", "tests/check_design.py", "1", "recorded"),
    ("SAF-12", "Safety", "Every exposed neon lamp lead is sleeved with insulation rated at least 300 V (600 V preferred).", "Brief invariant 0", "Sleeving line in BOM_mechanical.csv", "I", "BOM_mechanical.csv", "4", "open"),
    ("SAF-13", "Safety", "HV-side parts meet minimum ratings: CHV >=250 V; bleeder and sense resistors >=200 V; anode and lamp resistors 1 W.", "Brief BOM", "BOM.csv safety_critical lines", "I", "tests/check_requirements.py (BOM specs)", "1", "recorded"),
    ("SAF-14", "Safety", "A hung firmware loop resets the Nano within 2 s.", "Design choice", "wdt_enable(WDTO_2S)", "A", "scripts/avr_compile_check.sh", "2", "recorded"),
    ("HON-01", "Honesty", "No Gerber or drill files are produced until a routed board passes native ERC and DRC and an experienced HV review is signed off.", "Brief invariant 1", "scripts/make_fab_outputs.sh gate, hardware/REVIEW_SIGNOFF.md", "D", "scripts/make_fab_outputs.sh (refuses today)", "-", "recorded"),
    ("HON-02", "Honesty", "Validation records keep recorded file checks separate from physical checks, and claim only what was done.", "Brief invariant 1", "docs/VALIDATION.md", "I", "docs/VALIDATION.md", "7", "recorded"),
    ("FUN-01", "Function", "Six upright IN-14 tubes show HH MM SS, with an NE-2 separator between each pair.", "Brief appearance", "NET_MAP.csv driver map; timeToDigits()", "T", "tests/test_display_core.cpp", "4", "open"),
    ("FUN-02", "Function", "12- or 24-hour display is selectable and remembered across power cycles.", "Brief firmware", "cfg.twelveHour in EEPROM", "D", "tests/test_display_core.cpp", "2, 4", "open"),
    ("FUN-03", "Function", "Time can be set with the SET, H and M buttons and over USB serial.", "Brief firmware", "handleButtons(), T command", "D", "scripts/avr_compile_check.sh", "2", "open"),
    ("FUN-04", "Function", "The DS3231 keeps time on a CR2032 primary cell while unpowered (about +/-2 ppm, 0-40 C).", "Brief firmware", "U3, J2, VBAT", "A, T", "tests/check_equations.py (drift)", "2", "open"),
    ("FUN-05", "Function", "An optional sleep window blanks the display; any button wakes it for 30 s.", "Brief firmware", "inWindow(), wantDisplay()", "D", "tests/test_display_core.cpp", "2", "open"),
    ("FUN-06", "Function", "Once an hour every cathode of every tube is lit briefly (anti-poisoning).", "Brief firmware", "exerciseDigits()", "A, D", "tests/test_display_core.cpp", "4", "recorded"),
    ("FUN-07", "Function", "The display stays off while the time is invalid (except while the user is setting it, 60 s timeout).", "Brief firmware", "wantDisplay(), SET_TIMEOUT_MS", "D", "scripts/avr_compile_check.sh", "2", "open"),
    ("FUN-08", "Function", "STATUS over serial reports time, VIN, HV, state, faults and button states.", "Brief diagnostics", "printStatus()", "D", "scripts/avr_compile_check.sh", "2", "open"),
    ("ELE-01", "Electrical", "With all digits lit the 12 V input current stays near 0.25 A (stop above 0.35 A); adapter rated >=1 A.", "Analysis", "EQUATIONS.md section 5", "A, T", "tests/check_equations.py", "4", "open"),
    ("ELE-02", "Electrical", "HV load with all six tubes and both lamps lit stays within the converter rating (model: about 35 % of 30 mA).", "Brief firmware note", "PS1 NCH8200HV", "A, T", "tests/check_equations.py", "4", "open"),
    ("ELE-03", "Electrical", "HV5522 logic supply stays within 10.8-13.2 V; firmware refuses HV outside that VIN window.", "HV5522 data sheet", "VIN sense RV1/RV2, VIN_MIN_DV/VIN_MAX_DV", "A, T", "tests/check_equations.py", "2", "open"),
    ("MEC-01", "Mechanical", "Alarm-clock case 234 x 80 x 112 mm (about 116 mm to the button caps) with rounded top edges (R16) and corners (R10).", "Builder's request (alarm-clock look)", "cad/DIMENSIONS.json, source/build_cad.py", "I", "tests/check_cad.py", "6", "recorded"),
    ("MEC-02", "Mechanical", "Only M2 fasteners, one set: 4x M2x8 (floor to case) + 7x M2x6 (PCB to floor, cable clamp).", "Brief fasteners", "DIMENSIONS.json fasteners, BOM_mechanical.csv", "I, A", "tests/check_design.py", "0, 6", "recorded"),
    ("MEC-03", "Mechanical", "The tubes are fully enclosed: no glass passes through any opening; the case is lowered over the finished chassis.", "Builder's request (fully encased)", "case_shell(), floor standoffs", "I, D", "tests/check_cad.py", "6", "recorded"),
    ("MEC-04", "Mechanical", "All six numerals are seen through one front window glazed with a 3 mm smoked (or clear) cast-acrylic panel, held by the floor and three silicone dots so it stays put when the case is lifted.", "Builder's request (alarm-clock look)", "window_panel(), slot rails, Window DXF", "I", "tests/check_cad.py", "6", "recorded"),
    ("MEC-05", "Mechanical", "Every printed part fits a 256 x 256 x 256 mm build volume (Bambu Lab P1S) and prints in PETG; only the case roof needs supports.", "Builder's printer", "cad/BUILD_REPORT.txt bounding boxes", "A, D", "tests/check_requirements.py (bed fit)", "0, 6", "recorded"),
    ("MEC-08", "Mechanical", "With the case lifted off, TP1, TP4 and the HV_ARM shunt are reachable from the top of the chassis without reaching under the board.", "Fully enclosed design", "JP1, TP1-TP4 on the PCB top side (COMPONENT_PLACEMENT.csv)", "I", "tests/check_design.py", "3", "recorded"),
    ("MEC-07", "Mechanical", "SET, H and M are pressed from the top of the case through printed rods that rest on the switches by their own weight.", "Builder's request (alarm-clock look)", "button_rod(), guides in case_shell()", "A, D", "tests/check_cad.py", "0, 6", "open"),
    ("ELE-04", "Electrical", "The sealed case stays cool enough: modelled average internal rise a few kelvin at about 2.7 W; regulator checked at Stage 5.", "Fully enclosed design", "No vents (keeps HV enclosed)", "A, T", "tests/check_equations.py (enclosure rise)", "5", "open"),
    ("MEC-06", "Mechanical", "PCB 218 x 64 x 1.6 mm, 4 layers, five M2 holes at the specified coordinates.", "Brief geometry", "Nixie_RevC_placement.kicad_pcb", "I", "scripts/make_kicad.py (native placement DRC)", "-", "recorded"),
    ("CST-01", "Cost", "Built as cheaply as is safe: generic passives where allowed, no downgrades of safety items (planning total about $390, not re-priced).", "Brief cost levers", "BOM.csv substitution column", "I", "BOM.csv", "order", "open"),
    ("SEC-01", "Supply chain", "CI actions pinned by commit hash, least-privilege permissions, SBOM, SHA-256 checksums, Dependabot and CodeQL.", "Brief security", ".github/, sbom/, SHA256SUMS", "I", ".github/workflows/checks.yml", "-", "recorded"),
    ("DOC-01", "Documentation", "Every stage of the build guide lists parts, steps, measurements and PASS / FIX / STOP, with a safety gate before HV.", "Brief build guide", "docs/BUILD_GUIDE.md", "I", "docs/BUILD_GUIDE.md", "-", "recorded"),
    ("APP-01", "Distribution", "The project is published as a GitHub repository, a GitHub Pages website (installable offline) and a desktop app.", "Builder's request", "site/, app/, workflows", "D", "app launched headless (docs/APP.md)", "-", "recorded"),
]

HEAD = ["id", "category", "requirement", "source", "satisfied_by", "method", "evidence", "stage", "status"]
with open(ROOT / "hardware" / "REQUIREMENTS.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(HEAD)
    w.writerows(R)

rec = sum(r[8] == "recorded" for r in R)
lines = [
    "# Requirements (Rev C)",
    "",
    f"{len(R)} requirements, each traced to the design element that satisfies it and to how it is verified. "
    "Generated by `scripts/make_requirements.py` (also as [`hardware/REQUIREMENTS.csv`](../hardware/REQUIREMENTS.csv)); "
    "`tests/check_requirements.py` checks that every requirement has evidence that exists.",
    "",
    "**Methods:** I = Inspection, A = Analysis, D = Demonstration, T = Test. "
    "**Status:** *recorded* means a script checks the design files, which is **not** a physical result; "
    "*open* needs real parts or a measurement at the listed build stage ([BUILD_GUIDE.md](BUILD_GUIDE.md)).",
    "",
    f"![{rec} of {len(R)} requirements have a recorded design check; {len(R) - rec} still need a physical result](img/requirements_status.svg)",
    "",
]
cat = None
for r in R:
    if r[1] != cat:
        cat = r[1]
        lines += ["", f"## {cat}", "", "| ID | Requirement | Satisfied by | Method | Evidence | Stage | Status |", "|---|---|---|---|---|---|---|"]
    status = "recorded" if r[8] == "recorded" else "**open**"
    lines.append(f"| {r[0]} | {r[2]} | {r[4]} | {r[5]} | `{r[6]}` | {r[7]} | {status} |")
(ROOT / "docs" / "REQUIREMENTS.md").write_text("\n".join(lines) + "\n")

# Status bar SVG
cats = []
for r in R:
    if r[1] not in cats:
        cats.append(r[1])
W, rowh, left = 760, 30, 150
H = 60 + rowh * len(cats) + 30
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif" font-size="13">',
       '<rect width="100%" height="100%" rx="12" fill="#14110f"/>',
       f'<text x="20" y="30" fill="#f4e9dc" font-size="16" font-weight="600">Requirements: {rec} of {len(R)} have a recorded design check, {len(R) - rec} need a physical result</text>']
scale = (W - left - 80) / max(sum(1 for r in R if r[1] == c) for c in cats)
for i, c in enumerate(cats):
    y = 50 + i * rowh
    a = sum(1 for r in R if r[1] == c and r[8] == "recorded")
    b = sum(1 for r in R if r[1] == c and r[8] != "recorded")
    svg.append(f'<text x="{left - 10}" y="{y + 17}" fill="#b9a99a" text-anchor="end">{c}</text>')
    svg.append(f'<rect x="{left}" y="{y + 4}" width="{a * scale:.1f}" height="18" rx="3" fill="#ff9a3c"/>')
    svg.append(f'<rect x="{left + a * scale:.1f}" y="{y + 4}" width="{b * scale:.1f}" height="18" rx="3" fill="none" stroke="#ff9a3c" stroke-dasharray="4 3"/>')
    svg.append(f'<text x="{left + (a + b) * scale + 8:.1f}" y="{y + 17}" fill="#f4e9dc">{a}/{a + b}</text>')
y = H - 18
svg += [f'<rect x="{left}" y="{y - 11}" width="14" height="12" rx="2" fill="#ff9a3c"/><text x="{left + 20}" y="{y}" fill="#b9a99a">recorded design check (files only)</text>',
        f'<rect x="{left + 260}" y="{y - 11}" width="14" height="12" rx="2" fill="none" stroke="#ff9a3c" stroke-dasharray="4 3"/><text x="{left + 280}" y="{y}" fill="#b9a99a">open: needs parts or a measurement</text>',
        "</svg>"]
(ROOT / "docs" / "img" / "requirements_status.svg").write_text("\n".join(svg))
print(f"REQUIREMENTS: {len(R)} ({rec} recorded, {len(R) - rec} open)")
