#!/usr/bin/env python3
"""make_view_stl.py - single-file assembly meshes for VIEWING ONLY (GitHub shows .stl files in an
interactive 3D viewer). Never print these: they include glass, PCB and switch envelopes in assembly
coordinates. Printable parts are in cad/stl/ and cad/print/.
"""
import sys
from pathlib import Path

import cadquery as cq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
import build_cad as B  # noqa: E402

OUT = ROOT / "cad" / "view"
OUT.mkdir(parents=True, exist_ok=True)
env = B.pcb_mechanical()
common = [B.bottom_cover(), B.cable_clamp()] + list(env.values())
for name, parts in (("Assembly_RevC_clear_top_VIEW_ONLY", [B.acrylic_frame(), B.top_plate()]),
                    ("Assembly_RevC_all_printed_VIEW_ONLY", [B.printed_hood()])):
    comp = cq.Compound.makeCompound([p.val() for p in common + parts])
    cq.exporters.export(cq.Workplane().add(comp), str(OUT / f"{name}.stl"), tolerance=0.08, angularTolerance=0.3)
    print(f"cad/view/{name}.stl  {(OUT / f'{name}.stl').stat().st_size / 1e6:.1f} MB")
(OUT / "README.md").write_text("# View-only assemblies\n\nOpen these `.stl` files on GitHub to rotate the whole clock in 3D. **Do not print them**: they contain the glass, PCB and switch envelopes in assembly coordinates. Printable parts are in `../stl/` and `../print/`.\n")
