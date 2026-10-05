#!/usr/bin/env bash
# apply_zip.sh [path/to/nixie-clock.zip] - bring a new nixie-clock.zip (for example a new version from Claude)
# into this repository: files are replaced, files that the new ZIP no longer has are removed, and .git,
# node_modules, .venv and .build are left alone. It then shows what changed; commit with scripts/ship.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
[ -d .git ] && [ "$(git rev-parse --show-toplevel)" = "$ROOT" ] || { echo "Run this inside the nixie-clock repository"; exit 1; }
ZIP="${1:-}"
[ -n "$ZIP" ] || ZIP="$HOME/Downloads/nixie-clock.zip"
[ -f "$ZIP" ] || ZIP="$(ls -t /mnt/c/Users/*/Downloads/nixie-clock*.zip 2>/dev/null | head -n1 || true)"
[ -f "$ZIP" ] || { echo "No nixie-clock.zip found. Pass its path: scripts/apply_zip.sh /path/to/nixie-clock.zip"; exit 1; }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
unzip -q "$ZIP" -d "$TMP"
[ -f "$TMP/nixie-clock/docs/SAFETY.md" ] || { echo "$ZIP does not look like nixie-clock.zip"; exit 1; }
OLDVER="$(python3 -c 'import json; print(json.load(open("app/package.json"))["version"])' 2>/dev/null || echo 0.0.0)"
rsync -a --delete --exclude '.git/' --exclude 'node_modules/' --exclude '.venv/' --exclude '.build/' \
  --exclude 'app/www/' --exclude 'app/dist/' --exclude 'fab/' "$TMP/nixie-clock/" "$ROOT/"
# Never move the desktop app version backwards (a ZIP may predate your last release).
python3 - "$OLDVER" <<'PY'
import json, sys
old = sys.argv[1]
key = lambda v: tuple(int(x) for x in v.split("."))
d = json.load(open("app/package.json"))
if key(old) > key(d["version"]):
    for p in ("app/package.json", "app/package-lock.json"):
        j = json.load(open(p)); j["version"] = old
        if "packages" in j: j["packages"][""]["version"] = old
        open(p, "w").write(json.dumps(j, indent=2) + "\n")
    print(f"Kept desktop app version {old} (the ZIP had {d['version']})")
PY
git add -A && git status --short | head -40
echo "Applied $ZIP. Review the changes above, then: scripts/ship.sh \"Apply new ZIP\""
