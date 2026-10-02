#!/usr/bin/env python3
"""Write sbom/toolchain.spdx.json: an SPDX 2.3 software bill of materials for the TOOLCHAIN that
produced and checks this repository (helper scripts, compilers, CAD/EDA tools, CI actions).
Versions are the ones recorded on 2026-10-02. The app's full npm dependency tree is in app/package-lock.json. The Arduino core and libraries are recorded as used
for the manual compile check; pin them for real builds only after a board has passed Stage 2."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pkgs = [
    ("cadquery", "2.8.0", "pkg:pypi/cadquery@2.8.0", "Apache-2.0"),
    ("cadquery-ocp", "7.9.3.1.1", "pkg:pypi/cadquery-ocp@7.9.3.1.1", "LGPL-2.1-only"),
    ("ezdxf", "1.4.4", "pkg:pypi/ezdxf@1.4.4", "MIT"),
    ("vtk", "9.6.2", "pkg:pypi/vtk@9.6.2", "BSD-3-Clause"),
    ("numpy", "2.4.4", "pkg:pypi/numpy@2.4.4", "BSD-3-Clause"),
    ("Markdown", "3.10.2", "pkg:pypi/markdown@3.10.2", "BSD-3-Clause"),
    ("CairoSVG", "2.9.1", "pkg:pypi/cairosvg@2.9.1", "LGPL-3.0-or-later"),
    ("ArduinoCore-avr", "1.8.6 (42fa4a1ea1b1b11d1cc0a60298e529d37f9d14bd)", "pkg:github/arduino/ArduinoCore-avr@42fa4a1ea1b1b11d1cc0a60298e529d37f9d14bd", "LGPL-2.1-or-later"),
    ("gcc-avr", "7.3.0 (Ubuntu gcc-avr 1:7.3.0+Atmel3.7.0-1)", "pkg:deb/ubuntu/gcc-avr@1:7.3.0+Atmel3.7.0-1", "GPL-3.0-or-later"),
    ("avr-libc", "2.0.0 (Ubuntu 1:2.0.0+Atmel3.7.0-1)", "pkg:deb/ubuntu/avr-libc@1:2.0.0+Atmel3.7.0-1", "BSD-3-Clause"),
    ("KiCad", "7.0.11 (Ubuntu 7.0.11+dfsg-1build4)", "pkg:deb/ubuntu/kicad@7.0.11+dfsg-1build4", "GPL-3.0-or-later"),
    ("electron", "44.5.1", "pkg:npm/electron@44.5.1", "MIT"),
    ("electron-builder", "26.15.3", "pkg:npm/electron-builder@26.15.3", "MIT"),
    ("actions/setup-node", "v7.0.0", "pkg:githubactions/actions/setup-node@820762786026740c76f36085b0efc47a31fe5020", "MIT"),
    ("actions/upload-artifact", "v7.0.1", "pkg:githubactions/actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a", "MIT"),
    ("actions/download-artifact", "v8.0.1", "pkg:githubactions/actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c", "MIT"),
    ("actions/checkout", "v7.0.1", "pkg:githubactions/actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1", "MIT"),
    ("actions/configure-pages", "v6.0.0", "pkg:githubactions/actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d", "MIT"),
    ("actions/upload-pages-artifact", "v5.0.0", "pkg:githubactions/actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9", "MIT"),
    ("actions/deploy-pages", "v5.0.1", "pkg:githubactions/actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346", "MIT"),
    ("github/codeql-action", "v4.38.2", "pkg:githubactions/github/codeql-action@2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2", "MIT"),
]
doc = {
    "spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT",
    "name": "nixie-clock-revC-toolchain", "documentNamespace": "https://github.com/nixie-clock/sbom/revC-toolchain-2026-10-02",
    "creationInfo": {"created": "2026-10-02T00:00:00Z", "creators": ["Tool: scripts/make_sbom.py"]},
    "packages": [{
        "name": n, "SPDXID": f"SPDXRef-Pkg-{i}", "versionInfo": v, "downloadLocation": "NOASSERTION",
        "licenseConcluded": "NOASSERTION", "licenseDeclared": lic, "copyrightText": "NOASSERTION",
        "externalRefs": [{"referenceCategory": "PACKAGE-MANAGER", "referenceType": "purl", "referenceLocator": purl}],
    } for i, (n, v, purl, lic) in enumerate(pkgs)],
}
out = ROOT / "sbom" / "toolchain.spdx.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(doc, indent=2) + "\n")
print(f"wrote {out.relative_to(ROOT)} ({len(pkgs)} packages)")
