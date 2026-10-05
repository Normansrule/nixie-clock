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
for old in OUT.glob("*.stl"):
    old.unlink()
rods = [B.button_rod(x, y) for x, y in B.BUTTONS.values()]
views = {
    "Assembly_RevC_alarm_clock_VIEW_ONLY": [B.case_shell(), B.window_panel(), B.bottom_cover(), B.cable_clamp()] + rods + list(env.values()),
    "Chassis_RevC_case_removed_VIEW_ONLY": [B.bottom_cover(), B.cable_clamp()] + list(env.values()),
}
for name, parts in views.items():
    comp = cq.Compound.makeCompound([p.val() for p in parts])
    cq.exporters.export(cq.Workplane().add(comp), str(OUT / f"{name}.stl"), tolerance=0.08, angularTolerance=0.3)
    print(f"cad/view/{name}.stl  {(OUT / f'{name}.stl').stat().st_size / 1e6:.1f} MB")
(OUT / "README.md").write_text("# View-only assemblies\n\nOpen these `.stl` files on GitHub to rotate the whole clock in 3D. **Do not print them**: they contain the glass, PCB, switch and window envelopes in assembly coordinates. The chassis view shows the inside with the case lifted off. Printable parts are in `../stl/` and `../print/`.\n")
