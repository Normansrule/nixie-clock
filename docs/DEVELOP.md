# Keep building

Everyday commands for after the repository is on GitHub ([PUBLISH.md](PUBLISH.md) does the first push). Every block is meant to be pasted into an Ubuntu or WSL terminal as is. They all start with `cd ~/nixie-clock`, so you can paste them from anywhere, and they never touch your home folder's own files.

## One-time: install the full toolchain (optional)

Needed only to rerun every generator and check locally (KiCad, AVR compiler, CadQuery, the desktop app). The quick checks and `ship.sh` work without it.

```bash
cd ~/nixie-clock && scripts/setup_dev.sh
```

## After you change something: check, commit, push

Rebuilds the website, runs the quick checks, refreshes `SHA256SUMS`, commits and pushes. Pages redeploys by itself.

```bash
cd ~/nixie-clock && scripts/ship.sh "Describe what you changed"
```

## Run every recorded check

```bash
cd ~/nixie-clock && scripts/run_all_checks.sh
```

## Change the enclosure

Edit a value in `cad/DIMENSIONS.json`, then rebuild every STEP, STL, 3MF, plate, the DXF and the previews, and ship:

```bash
cd ~/nixie-clock && scripts/render_cad && scripts/ship.sh "Enclosure: describe the change"
```

## Change the BOM, requirements, drawings or labels

Edit the list at the top of the matching script, regenerate, check and ship:

```bash
cd ~/nixie-clock && python3 scripts/make_bom.py && python3 scripts/make_requirements.py && python3 scripts/make_drawings.py && python3 tests/check_requirements.py && scripts/ship.sh "BOM/requirements: describe the change"
```

`scripts/make_labels.py` regenerates `docs/labels.pdf` (needs the CairoSVG package from `scripts/setup_dev.sh`).

## Make the PCB fabrication package (only after routing and review)

Refuses until `hardware/Nixie_RevC.kicad_pcb` is routed, passes KiCad's own DRC and `hardware/REVIEW_SIGNOFF.md` is approved. See [MANUFACTURING.md](MANUFACTURING.md#3-pcb-fabrication-blocked-until-the-release-gate-passes).

```bash
cd ~/nixie-clock && scripts/make_fab_outputs.sh
```

## Change the circuit tables or KiCad files

Edit `scripts/make_design_tables.py` (the net map and placement come from it), then:

```bash
cd ~/nixie-clock && python3 scripts/make_design_tables.py && python3 tests/check_design.py && /usr/bin/python3 scripts/make_kicad.py && kicad-cli sch export pdf -o docs/Nixie_RevC_schematic.pdf hardware/Nixie_RevC.kicad_sch && scripts/ship.sh "Circuit: describe the change"
```

## Try the desktop app locally

On Windows 11 WSL the window opens through WSLg. On plain Ubuntu it opens normally.

```bash
cd ~/nixie-clock/app && npm ci --no-audit --no-fund && npm start
```

## Release a new desktop app version

Bumps the version, tags `app-vX.Y.Z` and pushes. GitHub Actions builds Windows, macOS and Linux files into a Release (about 10 minutes).

```bash
cd ~/nixie-clock && scripts/release_app.sh 1.0.1
```

## Bring in a new nixie-clock.zip (for example from Claude)

Put the new `nixie-clock.zip` in your Downloads folder (Windows Downloads works too under WSL), then:

```bash
cd ~/nixie-clock && scripts/apply_zip.sh && scripts/ship.sh "Apply new nixie-clock.zip"
```

`apply_zip.sh` replaces files, removes files the new ZIP no longer has, and leaves `.git`, `node_modules`, `.venv` and `.build` alone.

## Record a bench result

Fill in the build log in `docs/VALIDATION.md`, then ship it. Claim only what you measured.

```bash
cd ~/nixie-clock && nano docs/VALIDATION.md && scripts/ship.sh "Validation: Stage N results"
```
