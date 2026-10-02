#!/usr/bin/env bash
# run_all_checks.sh - every RECORDED check in one go. Passing means the files agree with each other.
# It is not evidence that a powered clock works: see docs/VALIDATION.md.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
echo "== equations";            "$PY" tests/check_equations.py | tail -1
echo "== design tables";        "$PY" tests/check_design.py
echo "== requirements + BOM";   "$PY" tests/check_requirements.py
echo "== fab release gate (expected to STOP until the board is routed and signed off)"; scripts/make_fab_outputs.sh | head -1 || true
echo "== firmware core (host)"; g++ -std=c++11 -Wall -Wextra -Werror -I firmware/Nixie_RevC tests/test_display_core.cpp -o .build/tdc 2>/dev/null || { mkdir -p .build && g++ -std=c++11 -Wall -Wextra -Werror -I firmware/Nixie_RevC tests/test_display_core.cpp -o .build/tdc; }; .build/tdc
if command -v avr-gcc >/dev/null && [ -d "${ARDUINO_CORE:-.build/ArduinoCore-avr}/cores" ]; then
  echo "== AVR compile";        scripts/avr_compile_check.sh "${ARDUINO_CORE:-.build/ArduinoCore-avr}" | tail -2
else echo "== AVR compile: skipped (needs avr-gcc and ArduinoCore-avr, see scripts/avr_compile_check.sh)"; fi
if "$PY" -c "import cadquery" 2>/dev/null; then echo "== CAD geometry"; "$PY" tests/check_cad.py | tail -1
else echo "== CAD geometry: skipped (pip install -r requirements-cad.txt)"; fi
if command -v kicad-cli >/dev/null && /usr/bin/python3 -c "import pcbnew" 2>/dev/null; then echo "== KiCad native netlist + placement DRC"; /usr/bin/python3 scripts/make_kicad.py | tail -2
else echo "== KiCad checks: skipped (needs KiCad 7.x with kicad-cli and the pcbnew Python module)"; fi
if command -v node >/dev/null; then echo "== desktop app syntax"; node --check app/main.js && node --check app/copy-site.js && echo "app JS: OK"; fi
