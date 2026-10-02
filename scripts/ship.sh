#!/usr/bin/env bash
# ship.sh "message" - the everyday loop: pull, regenerate the site and checksums, run the quick checks,
# commit everything and push. GitHub Pages redeploys on its own when site/ changes.
# Usage: scripts/ship.sh "Describe what you changed"
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
[ -d .git ] && [ "$(git rev-parse --show-toplevel)" = "$ROOT" ] || { echo "Run this inside the nixie-clock repository"; exit 1; }
MSG="${1:-Update}"
git pull --rebase --autostash -q
PY=python3; [ -x .venv/bin/python ] && PY=.venv/bin/python
"$PY" -c "import markdown" 2>/dev/null && "$PY" scripts/build_site.py || echo "site not rebuilt: run scripts/setup_dev.sh once (needs the markdown package)"
"$PY" tests/check_equations.py >/dev/null && echo "equations: OK"
"$PY" tests/check_design.py
"$PY" tests/check_requirements.py
mkdir -p .build && g++ -std=c++11 -Wall -Wextra -Werror -I firmware/Nixie_RevC tests/test_display_core.cpp -o .build/tdc && .build/tdc
"$PY" scripts/make_checksums.py
git add -A
if git diff --cached --quiet; then echo "Nothing to commit."; else git commit -qm "$MSG"; echo "Committed: $MSG"; fi
git push -q
echo "Pushed. Pages will update in a minute or two."
