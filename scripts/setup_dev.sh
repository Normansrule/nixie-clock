#!/usr/bin/env bash
# setup_dev.sh - one-time setup of everything the generators and checks use, on Ubuntu or WSL.
# Safe to re-run. Uses sudo only for apt. Python packages go into .venv (not system-wide).
#   apt:   python3-venv, g++, gcc-avr + avr-libc (firmware compile check), kicad (native netlist + DRC),
#          nodejs + npm (desktop app), rsync, unzip
#   .venv: requirements-docs.txt and requirements-cad.txt (CadQuery needs a Python version with
#          published wheels; if that install fails, everything else still works)
#   .build/ArduinoCore-avr: Arduino AVR core 1.8.6 for scripts/avr_compile_check.sh
set -euo pipefail
cd "$(dirname "$0")/.."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip g++ gcc-avr avr-libc nodejs npm rsync unzip git
sudo apt-get install -y -qq --no-install-recommends kicad || echo "KiCad not installed: the native KiCad checks will be skipped"
[ -d .venv ] || python3 -m venv --system-site-packages .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-docs.txt
.venv/bin/pip install -q -r requirements-cad.txt || echo "CadQuery/VTK did not install for $(python3 --version): CAD rebuilds are skipped. Use a Python 3.11-3.12 environment for them (for example: conda create -n nixie python=3.12)."
mkdir -p .build
[ -d .build/ArduinoCore-avr/cores ] || git clone -q --depth 1 --branch 1.8.6 https://github.com/arduino/ArduinoCore-avr.git .build/ArduinoCore-avr
(cd app && npm ci --no-audit --no-fund)
echo "Done. Run all checks with: scripts/run_all_checks.sh   Start the desktop app with: (cd app && npm start)"
