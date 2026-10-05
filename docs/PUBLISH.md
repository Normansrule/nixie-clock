# Publishing the repository to GitHub

One paste puts the project on GitHub in both forms:

- **Website** on GitHub Pages (also installable as an offline web app from Chrome or Edge), and
- **Desktop app** (Windows, macOS, Linux), built by GitHub Actions from the `app-v1.0.0` tag and attached to a GitHub Release.

Paste the block below **once** into an Ubuntu terminal (Windows Subsystem for Linux, WSL, works too). It:

1. installs `git`, the GitHub command-line interface (`gh`), `unzip` and `rsync` (the only step that uses `sudo`);
2. signs `gh` in as the account in `OWNER` (**the one interactive step**, only the first time: a browser code appears). If `gh` already knows that account it just switches to it;
3. pushes over SSH when `~/.ssh/config` has a host alias for that account (for example `github-normansrule`), otherwise over HTTPS with the `gh` token and the `workflow` permission;
4. finds `nixie-clock.zip` in `~/Downloads` or, under WSL, in your Windows Downloads folder;
5. unpacks it to `~/nixie-clock` (its own folder, and it refuses to run git anywhere else, which matters if your home folder is itself a git repository). If the repository is already there, it is brought exactly in line with the ZIP: files the new version no longer has are removed, so old and new designs never mix;
6. commits, creates the public repository, pushes `main`, turns on Pages, waits for the site, tags the desktop release and prints all the links.

It is safe to run again: every step checks what already exists and only does what is missing. Everything runs inside `( ... )`, so an error stops the script without closing your terminal. Change `OWNER` on the first line if the repository should belong to a different GitHub account.

```bash
(
set -euo pipefail
# 0. Settings: the GitHub account that will own the repository
OWNER="Normansrule"; REPO="nixie-clock"; DEST="$HOME/$REPO"
# 1. Install git, GitHub CLI, unzip and rsync (the only sudo step)
sudo apt-get update -qq
sudo apt-get install -y -qq git gh unzip rsync python3
# 2. Sign the GitHub CLI in as $OWNER (interactive only the first time)
gh auth status -h github.com >/dev/null 2>&1 || gh auth login -h github.com -p https -w -s workflow
if [ "$(gh api user --jq .login)" != "$OWNER" ]; then gh auth switch -h github.com -u "$OWNER" >/dev/null 2>&1 || gh auth login -h github.com -p https -w -s workflow; fi
[ "$(gh api user --jq .login)" = "$OWNER" ] || { echo "GitHub CLI is signed in as $(gh api user --jq .login), not $OWNER: run gh auth login and choose $OWNER"; false; }
# 3. Choose how to push: SSH host alias for $OWNER if ~/.ssh/config has one, else HTTPS with the gh token
ALIAS="$(awk -v o="$(printf %s "$OWNER" | tr '[:upper:]' '[:lower:]')" 'tolower($1)=="host" && index(tolower($2),o){print $2; exit}' "$HOME/.ssh/config" 2>/dev/null || true)"
if [ -n "$ALIAS" ]; then URL="git@$ALIAS:$OWNER/$REPO.git"; else
  SCOPES="$(gh api -i user 2>/dev/null | tr -d '\r' | grep -i '^x-oauth-scopes:' || true)"
  case "$SCOPES" in *workflow*) ;; *) gh auth refresh -h github.com -s workflow ;; esac
  gh auth setup-git -h github.com; URL="https://github.com/$OWNER/$REPO.git"; fi
echo "Pushing to $URL"
# 4. Find the ZIP: ~/Downloads first, then the Windows Downloads folder when running under WSL
ZIP="$HOME/Downloads/$REPO.zip"
[ -f "$ZIP" ] || ZIP="$(ls -t /mnt/c/Users/*/Downloads/$REPO*.zip 2>/dev/null | head -n1 || true)"
[ -f "$ZIP" ] || { echo "Could not find $REPO.zip in ~/Downloads or /mnt/c/Users/*/Downloads"; false; }
# 5. Unpack to ~/nixie-clock: a fresh folder, or an existing repository brought exactly in line with the ZIP
#    (files the new ZIP no longer has are removed; .git and local build folders are kept)
TMP="$(mktemp -d)"; unzip -q "$ZIP" -d "$TMP"
[ -f "$TMP/$REPO/docs/SAFETY.md" ] || { echo "$ZIP does not contain the $REPO folder"; false; }
mkdir -p "$DEST"
rsync -a --delete --exclude '.git/' --exclude 'node_modules/' --exclude '.venv/' --exclude '.build/' --exclude 'app/www/' --exclude 'app/dist/' --exclude 'fab/' "$TMP/$REPO/" "$DEST/"
rm -rf "$TMP"
cd "$DEST"
[ "$PWD" = "$DEST" ] && [ -f docs/SAFETY.md ] && [ -f app/package.json ] || { echo "Not in the unpacked repository: stopping"; false; }
# 6. Start the repository on branch main and make sure git is using this folder, not a parent repository
[ -d .git ] || git init -q -b main
[ "$(git rev-parse --show-toplevel)" = "$DEST" ] || { echo "git is not rooted at $DEST: stopping"; false; }
git config user.name >/dev/null || git config user.name "$OWNER"
git config user.email >/dev/null || git config user.email "$(gh api user --jq .id)+$OWNER@users.noreply.github.com"
# 7. Commit everything (skipped if nothing changed)
git add -A
git diff --cached --quiet || git commit -qm "Six-Tube Nixie Clock Rev C: alarm-clock case, build guide, KiCad, CAD, firmware, website and desktop app"
# 8. Create the public GitHub repository if it does not exist, and point origin at it
gh repo view "$OWNER/$REPO" >/dev/null 2>&1 || gh repo create "$OWNER/$REPO" --public -d "Six-tube IN-14 Nixie clock: build guide, KiCad, CadQuery, firmware, website and desktop app (Rev C, unvalidated)" --homepage "https://$(printf %s "$OWNER" | tr '[:upper:]' '[:lower:]').github.io/$REPO/"
git remote add origin "$URL" 2>/dev/null || git remote set-url origin "$URL"
gh api -X POST "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null 2>&1 || true
# 9. Push main, then make sure GitHub Pages is on (published by the repository's pages workflow)
git push -q -u origin main
gh api -X POST "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null 2>&1 || gh api -X PUT "repos/$OWNER/$REPO/pages" -f build_type=workflow >/dev/null
# 10. Start a fresh Pages deployment and wait for that run (not an older one) to finish
OLD="$(gh run list -R "$OWNER/$REPO" -w pages.yml -e workflow_dispatch -L 1 --json databaseId --jq '.[0].databaseId // ""' 2>/dev/null || true)"
for _ in 1 2 3 4 5 6; do gh workflow run pages.yml -R "$OWNER/$REPO" >/dev/null 2>&1 && break; sleep 5; done
RUN=""; for _ in $(seq 1 24); do RUN="$(gh run list -R "$OWNER/$REPO" -w pages.yml -e workflow_dispatch -L 1 --json databaseId --jq '.[0].databaseId // ""' 2>/dev/null || true)"; [ -n "$RUN" ] && [ "$RUN" != "$OLD" ] && break; sleep 5; done
if [ -n "$RUN" ] && [ "$RUN" != "$OLD" ]; then gh run watch "$RUN" -R "$OWNER/$REPO" --exit-status >/dev/null || echo "Pages run did not finish cleanly: gh run view $RUN -R $OWNER/$REPO --log-failed"; else echo "Pages run not found yet: check the Actions tab"; fi
# 11. Release the desktop app: tag app-v<version> once; GitHub Actions builds Windows, macOS and Linux files
VER="$(python3 -c 'import json; print(json.load(open("app/package.json"))["version"])')"
git rev-parse -q --verify "refs/tags/app-v$VER" >/dev/null || git tag -a "app-v$VER" -m "Nixie Clock Companion $VER"
[ -n "$(git ls-remote --tags origin "refs/tags/app-v$VER")" ] || git push -q origin "app-v$VER"
# 12. Print the links
echo "Website:      $(gh api "repos/$OWNER/$REPO/pages" --jq .html_url 2>/dev/null || echo "https://$OWNER.github.io/$REPO/")"
echo "Repository:   https://github.com/$OWNER/$REPO"
echo "Desktop app:  https://github.com/$OWNER/$REPO/releases/tag/app-v$VER  (ready in about 10 minutes)"
echo "Keep building: cd ~/nixie-clock, then see docs/DEVELOP.md"
)
```

## After that

Everyday commands (check, commit and push; release a new app version; bring in a new ZIP) are in [DEVELOP.md](DEVELOP.md).

## If something goes wrong

- **`refusing to allow an OAuth App to create or update workflow`**: you pushed over HTTPS without the `workflow` permission. Run `gh auth refresh -h github.com -s workflow`, then paste the block again.
- **`Permission denied (publickey)`**: the SSH alias in `~/.ssh/config` does not have a key GitHub accepts for `OWNER`. Test with `ssh -T git@<alias>`, or move the alias out of the way to fall back to HTTPS.
- **Signed in as the wrong account**: `gh auth login -h github.com` and choose the right one, then paste the block again.
- **Pages is not enabled, or the first deploy fails**: open the repository's *Settings → Pages*, set *Source* to *GitHub Actions*, then run `gh workflow run pages.yml -R <owner>/nixie-clock`.
- **The desktop release is missing files**: open the *Actions* tab, choose the *desktop* run, and read the failed job's log. Rerun it with `gh run rerun <run id> --failed -R <owner>/nixie-clock`.
- **The site shows old content**: the site is prebuilt. Run `scripts/ship.sh "Rebuild site"` from `~/nixie-clock`.
