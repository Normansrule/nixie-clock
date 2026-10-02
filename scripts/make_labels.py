#!/usr/bin/env python3
"""make_labels.py - printable HV warning and rating labels for the bottom cover (1:1, millimetres).
Writes docs/img/labels.svg and docs/labels.pdf. Print at 100 % (no "fit to page") on vinyl sticker paper.
"""
from pathlib import Path

import cairosvg

ROOT = Path(__file__).resolve().parents[1]


def tri(x, y, s):
    """Yellow warning triangle with a lightning bolt (generic electrical-hazard symbol)."""
    h = s * 0.866
    bolt = (f"M{x + s*0.53:.2f},{y + h*0.30:.2f} L{x + s*0.40:.2f},{y + h*0.62:.2f} L{x + s*0.50:.2f},{y + h*0.62:.2f} "
            f"L{x + s*0.44:.2f},{y + h*0.90:.2f} L{x + s*0.62:.2f},{y + h*0.52:.2f} L{x + s*0.52:.2f},{y + h*0.52:.2f} Z")
    return (f'<path d="M{x + s/2:.2f},{y:.2f} L{x + s:.2f},{y + h:.2f} L{x:.2f},{y + h:.2f} Z" fill="#ffd400" stroke="#111" stroke-width="1.2" stroke-linejoin="round"/>'
            f'<path d="{bolt}" fill="#111"/>')


W, H = 200, 120
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" font-family="DejaVu Sans, Arial, sans-serif">
<rect width="{W}" height="{H}" fill="#fff"/>
<text x="6" y="7" font-size="3" fill="#555">Six-Tube Nixie Clock Rev C labels. Print at 100 %, check the 50 mm bar, cut on the grey lines.</text>
<rect x="6" y="9" width="50" height="1.2" fill="#000"/><text x="58" y="10.6" font-size="2.6" fill="#555">50 mm</text>
<!-- Label 1: HV warning, 90 x 44 mm -->
<rect x="6" y="14" width="90" height="44" rx="3" fill="#ffd400" stroke="#999" stroke-width="0.3"/>
<rect x="8" y="16" width="86" height="40" rx="2" fill="none" stroke="#111" stroke-width="1"/>
{tri(11, 19, 22)}
<text x="37" y="26" font-size="6.2" font-weight="700" fill="#111">DANGER</text>
<text x="37" y="33" font-size="4.2" font-weight="700" fill="#111">HIGH VOLTAGE INSIDE</text>
<text x="37" y="38.5" font-size="3.6" fill="#111">about 170 V DC</text>
<text x="11" y="45.5" font-size="3" fill="#111">Unplug, wait 60 s, then MEASURE TP4 below 10 V</text>
<text x="11" y="50" font-size="3" fill="#111">before opening. Dark tubes do not mean safe.</text>
<!-- Label 2: rating plate, 90 x 44 mm -->
<rect x="104" y="14" width="90" height="44" rx="3" fill="#fff" stroke="#999" stroke-width="0.3"/>
<text x="108" y="22" font-size="4.6" font-weight="700" fill="#111">Six-Tube Nixie Clock</text>
<text x="108" y="27.5" font-size="3.2" fill="#111">Rev C · UNVALIDATED PROTOTYPE</text>
<line x1="108" y1="30" x2="190" y2="30" stroke="#111" stroke-width="0.3"/>
<text x="108" y="35.5" font-size="3.2" fill="#111">Input: 12 V DC, 1 A, centre positive</text>
<text x="108" y="40.5" font-size="3.0" fill="#111">5.5 x 2.1 mm plug · isolated regulated adapter only</text>
<text x="108" y="45.5" font-size="3.2" fill="#111">High voltage inside · read docs/SAFETY.md</text>
<text x="108" y="52.5" font-size="3.2" fill="#111">Serial: ______________  Built: ___________</text>
<!-- Label 3: small HV marker for inside the case, near PS1 and TP4, 40 x 16 mm (two copies) -->
<g>
<rect x="6" y="66" width="44" height="18" rx="2" fill="#ffd400" stroke="#999" stroke-width="0.3"/>{tri(8, 68, 15)}
<text x="25" y="74" font-size="3.6" font-weight="700" fill="#111">170 V DC</text><text x="25" y="79" font-size="2.6" fill="#111">measure TP4 first</text>
<rect x="56" y="66" width="44" height="18" rx="2" fill="#ffd400" stroke="#999" stroke-width="0.3"/>{tri(58, 68, 15)}
<text x="75" y="74" font-size="3.6" font-weight="700" fill="#111">170 V DC</text><text x="75" y="79" font-size="2.6" fill="#111">measure TP4 first</text>
</g>
<!-- Label 4: HV_ARM shunt tag -->
<rect x="106" y="66" width="60" height="18" rx="2" fill="#fff" stroke="#999" stroke-width="0.3"/>
<text x="110" y="73" font-size="3.4" font-weight="700" fill="#111">JP1 HV_ARM</text>
<text x="110" y="78" font-size="2.6" fill="#111">Removing the shunt does NOT discharge</text>
<text x="110" y="81.5" font-size="2.6" fill="#111">the HV rail. Measure TP4 first.</text>
<text x="6" y="96" font-size="2.8" fill="#555">These labels are reminders, not a safety certification. The build is an unvalidated engineering prototype.</text>
</svg>'''
(ROOT / "docs" / "img" / "labels.svg").write_text(svg)
cairosvg.svg2pdf(bytestring=svg.encode(), write_to=str(ROOT / "docs" / "labels.pdf"))
cairosvg.svg2png(bytestring=svg.encode(), write_to=str(ROOT / "docs" / "img" / "labels.png"), output_width=1400)
print("wrote docs/labels.pdf, docs/img/labels.svg, docs/img/labels.png")
