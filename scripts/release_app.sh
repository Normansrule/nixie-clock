#!/usr/bin/env bash
# release_app.sh X.Y.Z - release a new desktop app version: bump app/package.json, commit, tag app-vX.Y.Z
# and push. GitHub Actions (desktop.yml) then builds Windows, macOS and Linux files into a GitHub Release.
# Usage: scripts/release_app.sh 1.0.1
set -euo pipefail
cd "$(dirname "$0")/.."
VER="${1:?usage: scripts/release_app.sh X.Y.Z}"
[[ "$VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Version must look like 1.2.3"; exit 1; }
TAG="app-v$VER"
git rev-parse -q --verify "refs/tags/$TAG" >/dev/null && { echo "Tag $TAG already exists"; exit 1; }
python3 - "$VER" <<'PY'
import json, sys
p = "app/package.json"; d = json.load(open(p)); d["version"] = sys.argv[1]
open(p, "w").write(json.dumps(d, indent=2) + "\n")
p = "app/package-lock.json"; d = json.load(open(p)); d["version"] = sys.argv[1]; d["packages"][""]["version"] = sys.argv[1]
open(p, "w").write(json.dumps(d, indent=2) + "\n")
PY
python3 scripts/make_checksums.py >/dev/null
git add app/package.json app/package-lock.json SHA256SUMS
git commit -qm "Desktop app $VER"
git tag -a "$TAG" -m "Nixie Clock Companion $VER"
git push -q && git push -q origin "$TAG"
SLUG="$(git remote get-url origin | sed -E 's#.*github[^:/]*[:/]([^/]+/[^/.]+)(\.git)?$#\1#')"
echo "Tagged $TAG. Build progress: https://github.com/$SLUG/actions  Release: https://github.com/$SLUG/releases/tag/$TAG"
