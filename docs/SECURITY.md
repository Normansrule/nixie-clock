# Security and supply chain

This project ships files that people will build and power: firmware, board data and printed parts. A tampered file here could hurt someone, so the repository treats its own supply chain seriously. The approach follows OWASP Top 10:2025 **A03 Software Supply Chain Failures** (OWASP = Open Worldwide Application Security Project).

## Reporting a problem

- **Safety issue** (anything that could expose high voltage, defeat blanking or the HV-off defaults, or overheat a part): open a GitHub issue titled `SAFETY:` and stop building until it is answered.
- **Security issue** in the repository or its automation: use GitHub's *Report a vulnerability* (private advisory) on the repository's Security tab rather than a public issue.

## What is in place

| Control | Where |
|---|---|
| **Actions pinned by full commit hash**, version in a comment | `.github/workflows/*.yml` |
| **Least privilege**: workflows default to no permissions (`permissions: {}` or `contents: read`); only the Pages job gets `pages: write` + `id-token: write`, only CodeQL gets `security-events: write`, only the desktop release job gets `contents: write`; checkout never persists credentials | same |
| **No third-party packages in CI** for checks and Pages: the checks use the runner's own Python, g++ and Node; the Pages job uploads a prebuilt folder | `checks.yml`, `pages.yml` |
| **Desktop app**: dependencies locked by `app/package-lock.json` and installed with `npm ci`; builds unsigned on GitHub-hosted runners; the release job alone gets `contents: write` and publishes SHA-256 checksums; pages run sandboxed with no Node.js access and web links open in the system browser | `app/`, `.github/workflows/desktop.yml` |
| **Dependabot** for GitHub Actions, the pinned Python requirements and the app's npm packages | `.github/dependabot.yml` |
| **CodeQL** on the Python helper scripts, the C++ firmware core and the app and site JavaScript | `.github/workflows/codeql.yml` |
| **Pinned helper toolchain** | `requirements-cad.txt`, `requirements-docs.txt` |
| **Toolchain SBOM** (software bill of materials, SPDX 2.3) | `sbom/toolchain.spdx.json` from `scripts/make_sbom.py` |
| **SHA-256 checksums** of every deliverable, verified in CI | `SHA256SUMS` from `scripts/make_checksums.py` |

## Arduino core and libraries

The firmware uses only `Wire` and `EEPROM`, both bundled with the Arduino AVR core. The recorded compile check used ArduinoCore-avr **1.8.6** (commit `42fa4a1e`) with avr-gcc 7.3.0. **Pin the Arduino core and library versions in this file once a real build passes Stage 2** of the build guide, and record the IDE version with them:

| Item | Pinned version | Recorded by / date |
|---|---|---|
| Arduino IDE / arduino-cli | *not yet pinned* | |
| Arduino AVR Boards core | *not yet pinned* (compile check used 1.8.6) | |
| Wire, EEPROM | bundled with the core | |

Install libraries only from the Arduino core itself. Rev C needs no third-party library.

## Signed releases

A release is a tag plus a ZIP of the repository, its `SHA256SUMS`, and a detached signature by the maintainer.

```bash
# maintainer, on a clean checkout of the tag
python3 scripts/make_checksums.py && git diff --exit-code SHA256SUMS
git tag -s rev-c-proto-1 -m "Rev C prototype files (UNVALIDATED)"
git archive --format=zip -o nixie-clock-rev-c-proto-1.zip rev-c-proto-1
sha256sum nixie-clock-rev-c-proto-1.zip > nixie-clock-rev-c-proto-1.zip.sha256
gpg --armor --detach-sign SHA256SUMS
gh release create rev-c-proto-1 nixie-clock-rev-c-proto-1.zip nixie-clock-rev-c-proto-1.zip.sha256 SHA256SUMS SHA256SUMS.asc --notes "UNVALIDATED ENGINEERING PROTOTYPE. No Gerbers."
```

To verify: `gpg --verify SHA256SUMS.asc SHA256SUMS`, then `sha256sum -c SHA256SUMS` inside the unpacked tree. A release is never called a "fabrication release" until [VALIDATION.md](VALIDATION.md) says the physical checks passed.

## Sourcing parts

Counterfeit and re-marked parts are common for Nixie tubes, HV5522 drivers and DS3231 clocks. Buy ICs from authorised distributors, tubes from sellers who test them, and compare markings with the data sheets in [CREDITS.md](../CREDITS.md). Never substitute a lower-rated part on the safety list in [BOM.md](BOM.md#safety-critical-parts-first).
