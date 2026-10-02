#!/usr/bin/env python3
"""Write SHA256SUMS for every tracked deliverable (firmware, hardware, CAD outputs, docs, site).
Release signing is a separate, manual maintainer step: see docs/SECURITY.md."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".build", "__pycache__", ".github", "node_modules", ".venv", "dist", "www", "fab"}
lines = []
for p in sorted(ROOT.rglob("*")):
    rel = p.relative_to(ROOT)
    if p.is_dir() or rel.parts[0] in SKIP_DIRS or any(x in SKIP_DIRS for x in rel.parts) or rel.name == "SHA256SUMS":
        continue
    lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel.as_posix()}")
(ROOT / "SHA256SUMS").write_text("\n".join(lines) + "\n")
print(f"SHA256SUMS: {len(lines)} files")
