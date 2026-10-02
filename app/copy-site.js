// copy-site.js - copy the prebuilt GitHub Pages site (../site) into www/ for the desktop app,
// and record which GitHub repository the app's "view on GitHub" links should open.
// The repository comes from GITHUB_REPOSITORY (set in GitHub Actions) or NIXIE_REPO, else the git remote.
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const src = path.join(__dirname, '..', 'site');
const dst = path.join(__dirname, 'www');
if (!fs.existsSync(path.join(src, 'index.html'))) {
  console.error('site/ is missing: run python3 scripts/build_site.py first');
  process.exit(1);
}
fs.rmSync(dst, { recursive: true, force: true });
fs.cpSync(src, dst, { recursive: true });

let repo = process.env.GITHUB_REPOSITORY || process.env.NIXIE_REPO || '';
if (!repo) {
  try {
    const url = execSync('git remote get-url origin', { cwd: __dirname, stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
    const m = url.match(/github[^:/]*[:/]([^/]+\/[^/.]+)(\.git)?$/);
    if (m) repo = m[1];
  } catch (e) { /* no git remote yet */ }
}
let n = 0;
for (const f of fs.readdirSync(dst).filter((f) => f.endsWith('.html'))) {
  const p = path.join(dst, f);
  const html = fs.readFileSync(p, 'utf8').replace('<meta name="nixie-repo" content="">', `<meta name="nixie-repo" content="${repo}">`);
  fs.writeFileSync(p, html);
  n++;
}
console.log(`copied site/ -> app/www (${n} pages), repo links -> ${repo || '(none: links open locally)'}`);
