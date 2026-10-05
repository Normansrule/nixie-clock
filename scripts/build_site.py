#!/usr/bin/env python3
"""build_site.py - build the GitHub Pages site in site/ from README.md, docs/*.md and CREDITS.md.

The output is committed, so the Pages workflow only uploads files (no build step in CI).
Needs: pip install -r requirements-docs.txt
Links to repository files that are not part of the site (hardware/, firmware/, cad/ ...) are written
as "repo:<path>" and turned into GitHub links in the browser, so the site works under any owner.
"""
import html
import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PAGES = [  # (source, output, nav label)
    ("README.md", "index.html", "Overview"),
    ("docs/SAFETY.md", "SAFETY.html", "Safety"),
    ("docs/BUILD_GUIDE.md", "BUILD_GUIDE.html", "Build guide"),
    ("docs/MANUFACTURING.md", "MANUFACTURING.html", "Make it"),
    ("docs/BOM.md", "BOM.html", "Parts"),
    ("docs/WIRING.md", "WIRING.html", "Wiring"),
    ("docs/EQUATIONS.md", "EQUATIONS.html", "Equations"),
    ("docs/PRINTING.md", "PRINTING.html", "Printing"),
    ("docs/tools.html", "TOOLS.html", "Tools"),
    ("docs/APP.md", "APP.html", "App"),
    ("docs/REQUIREMENTS.md", "REQUIREMENTS.html", "Requirements"),
    ("docs/VALIDATION.md", "VALIDATION.html", "Validation"),
    ("docs/SECURITY.md", "SECURITY.html", "Security"),
    ("docs/PUBLISH.md", "PUBLISH.html", "Publish"),
    ("docs/DEVELOP.md", "DEVELOP.html", "Develop"),
    ("CREDITS.md", "CREDITS.html", "Credits"),
]
DOWNLOADS = ["cad/Window_panel_3mm_1to1.dxf", "cad/print/plate_0_fit_coupons.3mf", "cad/print/plate_A_case_shell.3mf",
             "cad/print/plate_B_floor_clamp_rods.3mf",
             "docs/Nixie_RevC_schematic.pdf", "hardware/NET_MAP.csv", "hardware/BOM.csv", "hardware/BOM_mechanical.csv",
             "hardware/REQUIREMENTS.csv", "hardware/TEST_RECORD.csv", "docs/labels.pdf"]


def slugify(value, separator="-"):
    """GitHub-style heading anchors, so links written for GitHub also work on the site."""
    v = re.sub(r"<[^>]+>", "", value).strip().lower()
    v = re.sub(r"[^\w\- ]", "", v, flags=re.UNICODE)
    return v.replace(" ", separator)


ALERTS = {"CAUTION": "Caution", "WARNING": "Warning", "IMPORTANT": "Important", "NOTE": "Note", "TIP": "Tip"}


def convert_alerts(md):
    """GitHub '> [!CAUTION]' alert blocks -> a blockquote with a bold label (python-markdown has no alerts)."""
    return re.sub(r"^> \[!(CAUTION|WARNING|IMPORTANT|NOTE|TIP)\]\s*\n> ", lambda m: f"> **{ALERTS[m.group(1)]}:** ", md, flags=re.M)


def rewrite_links(md, src):
    in_docs = src.startswith("docs/")
    site_md = {Path(s).name: o for s, o, _ in PAGES}
    dl = {d: "downloads/" + Path(d).name for d in DOWNLOADS}

    def fix(target):
        if re.match(r"^(https?:|mailto:|#)", target):
            return target
        path, _, frag = target.partition("#")
        # normalise to a repository-relative path
        rel = (Path(src).parent / path).as_posix() if path else src
        rel = re.sub(r"(^|/)\./", r"\1", rel)
        while "/../" in "/" + rel:
            rel = re.sub(r"[^/]+/\.\./", "", rel, count=1)
        rel = rel.lstrip("/")
        if path.endswith("/") and not rel.endswith("/"):
            rel += "/"  # keep directory links as directories (GitHub "tree" view)
        frag = ("#" + frag) if frag else ""
        if Path(rel).name in site_md and rel.endswith(".md") and (rel.startswith("docs/") or "/" not in rel):
            return site_md[Path(rel).name] + frag
        if rel == "docs/tools.html":
            return "TOOLS.html" + frag
        if rel.startswith("docs/img/"):
            return rel[len("docs/"):]
        if rel in dl:
            return dl[rel]
        return "repo:" + rel + frag

    md = re.sub(r"(\]\()([^)\s]+)(\))", lambda m: m.group(1) + fix(m.group(2)) + m.group(3), md)
    return md


CSS = r"""
:root{--bg:#120e0b;--panel:#1c1612;--ink:#f3e8dc;--mute:#b6a594;--line:#3a2f27;--glow:#ff8a1f;--glow2:#ffb45e;--hv:#ff5a3c;--link:#ffb45e;--code:#241c16}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;background:var(--bg)}
body{margin:0;background:radial-gradient(1200px 500px at 70% -10%,#2a1a0e 0%,var(--bg) 60%) fixed;color:var(--ink);font:16px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--link);text-underline-offset:2px}a:hover{color:#fff}
header{position:sticky;top:0;z-index:5;background:rgba(18,14,11,.88);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.bar{max-width:1080px;margin:0 auto;padding:10px 16px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.brand{font-weight:700;letter-spacing:.02em;color:var(--ink);text-decoration:none;display:flex;gap:8px;align-items:center}
.brand b{color:var(--glow);text-shadow:0 0 12px rgba(255,138,31,.8),0 0 2px #ffcf99;font-family:ui-monospace,Menlo,monospace;font-size:20px}
nav{display:flex;gap:4px;flex-wrap:wrap}nav a{color:var(--mute);text-decoration:none;padding:4px 9px;border-radius:999px;font-size:14px}
nav a.on,nav a:hover{color:var(--bg);background:var(--glow)}
.warn{background:linear-gradient(90deg,#3a130b,#2a1209);border-bottom:1px solid #7a2a17;color:#ffd9c9;font-size:14px}
.warn div{max-width:1080px;margin:0 auto;padding:7px 16px}.warn strong{color:#fff}
main{max-width:1080px;margin:0 auto;padding:28px 16px 64px}
h1,h2,h3{line-height:1.25;scroll-margin-top:90px}h1{font-size:2.1rem;margin:.2em 0 .6em}
h2{margin-top:2.2em;padding-top:.6em;border-top:1px solid var(--line)}h3{color:var(--glow2)}
img{max-width:100%;height:auto;border-radius:12px;border:1px solid var(--line);background:#14110f}
table{border-collapse:collapse;width:100%;margin:1em 0;font-size:14.5px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}th{background:#241b15;color:var(--glow2)}
tr:nth-child(even) td{background:rgba(255,255,255,.015)}
code{background:var(--code);padding:.1em .35em;border-radius:5px;font-size:.9em}
pre{background:var(--code);border:1px solid var(--line);border-radius:10px;padding:14px;overflow-x:auto;position:relative}pre code{background:none;padding:0}
.copy{position:absolute;top:8px;right:8px;background:var(--glow);color:var(--bg);border:0;border-radius:6px;padding:4px 10px;font-weight:600;cursor:pointer}
blockquote{margin:1.2em 0;padding:10px 18px;border-left:4px solid var(--hv);background:#241310;border-radius:0 10px 10px 0}
blockquote h2{border:0;margin:.3em 0;padding:0;color:#ffcbb8}
.hero{position:relative;margin:-8px 0 28px;border-radius:16px;overflow:hidden;border:1px solid var(--line)}
.hero img{display:block;border:0;border-radius:0}
.hero .cap{position:absolute;left:18px;bottom:14px;right:18px;font-size:13px;color:var(--mute)}
.tubes{font-family:ui-monospace,Menlo,monospace;font-size:clamp(34px,8vw,64px);letter-spacing:.12em;color:var(--glow);text-shadow:0 0 18px rgba(255,138,31,.9),0 0 3px #ffd9ad;margin:6px 0 2px}
.tubes i{font-style:normal;font-size:.5em;vertical-align:middle;color:#ff6a1a;margin:0 .15em}
footer{border-top:1px solid var(--line);color:var(--mute);font-size:13px}footer div{max-width:1080px;margin:0 auto;padding:18px 16px}
@media (max-width:640px){body{font-size:15px}h1{font-size:1.6rem}.bar{gap:8px}}
"""

JS = r"""
(function(){
  // Repository for "repo:" links: a slug baked in by the desktop app, else derived from *.github.io, else local files.
  var meta=document.querySelector('meta[name="nixie-repo"]'), slug=meta&&meta.content?meta.content:'';
  var host=location.hostname;
  if(!slug&&host.endsWith('.github.io')) slug=host.split('.')[0]+'/'+(location.pathname.split('/')[1]||'nixie-clock');
  document.querySelectorAll('a[href^="repo:"]').forEach(function(a){
    var p=a.getAttribute('href').slice(5), dir=/\/$/.test(p.split('#')[0]);
    a.href=slug?('https://github.com/'+slug+'/'+(dir?'tree':'blob')+'/main/'+p):('../'+p);
  });
  // Installable, offline web app (not inside the desktop app, which already works offline).
  if('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('sw.js').catch(function(){});
  document.querySelectorAll('pre:not(.log)').forEach(function(pre){
    var b=document.createElement('button');b.className='copy';b.textContent='Copy';
    b.onclick=function(){navigator.clipboard.writeText(pre.innerText.replace(/\nCopy$/,'')).then(function(){b.textContent='Copied';setTimeout(function(){b.textContent='Copy'},1500)})};
    pre.appendChild(b);
  });
  var t=document.getElementById('clock');
  if(t){var f=function(){var d=new Date(),z=function(n){return('0'+n).slice(-2)};t.innerHTML=z(d.getHours())+z(d.getMinutes()).replace(/^/,'<i>&#9679;</i>')+z(d.getSeconds()).replace(/^/,'<i>&#9679;</i>')};f();setInterval(f,1000)}
})();
"""


def page(title, body, active, is_index):
    nav = "".join(f'<a href="{o}"{" class=on" if o == active else ""}>{html.escape(lbl)}</a>' for _, o, lbl in PAGES)
    hero = ""
    if is_index:
        hero = '<div class="tubes" id="clock" aria-label="current time, styled like the clock">12<i>&#9679;</i>34<i>&#9679;</i>56</div>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · Six-Tube Nixie Clock Rev C</title>
<meta name="description" content="Open-source six-tube IN-14 Nixie clock: build guide, wiring, KiCad, CadQuery, firmware. Rev C, unvalidated prototype.">
<meta name="nixie-repo" content="">
<meta name="theme-color" content="#120e0b">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" type="image/svg+xml" href="img/icon.svg">
<link rel="apple-touch-icon" href="img/icon-192.png">
<style>{CSS}</style></head><body>
<header><div class="bar"><a class="brand" href="index.html"><b>IN-14</b> Nixie Clock · Rev C</a><nav>{nav}</nav></div></header>
<div class="warn"><div><strong>High voltage (about 170 V DC).</strong> Unvalidated prototype. Read <a href="SAFETY.html">Safety</a> before building. Off is not safe until you have measured it.</div></div>
<main>{hero}{body}</main>
<footer><div>Six-Tube Nixie Clock, Rev C · UNVALIDATED ENGINEERING PROTOTYPE · no Gerbers shipped · MIT license · generated from the repository by scripts/build_site.py</div></footer>
<script>{JS}</script></body></html>
"""


def write_pwa():
    """Web app manifest + a small service worker so the site installs as an app and works offline."""
    import hashlib
    import json
    manifest = {
        "name": "Nixie Clock Companion", "short_name": "Nixie Clock",
        "description": "Build guide, calculators and USB serial companion for the Six-Tube Nixie Clock (Rev C).",
        "start_url": "./index.html", "scope": "./", "display": "standalone",
        "background_color": "#120e0b", "theme_color": "#120e0b",
        "icons": [{"src": "img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "img/icon-512.png", "sizes": "512x512", "type": "image/png"},
                  {"src": "img/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
    }
    (SITE / "manifest.webmanifest").write_text(json.dumps(manifest, indent=2) + "\n")
    files = sorted(p.relative_to(SITE).as_posix() for p in SITE.rglob("*")
                   if p.is_file() and not p.name.startswith(".") and p.suffix != ".3mf" and p.stat().st_size < 2_000_000)
    files = ["./"] + files
    version = hashlib.sha256("".join(files).encode() + b"".join((SITE / f).read_bytes() for f in files if f != "./")).hexdigest()[:12]
    sw = f"""// sw.js - offline cache for the Nixie Clock site (generated by scripts/build_site.py).
const CACHE = 'nixie-{version}';
const FILES = {json.dumps(files)};
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {{
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request).then(r => {{ const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; }})
    .catch(() => caches.match(e.request, {{ ignoreSearch: true }})));
}});
"""
    (SITE / "sw.js").write_text(sw)


def main():
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "img").mkdir(parents=True)
    (SITE / "downloads").mkdir()
    for f in (ROOT / "docs" / "img").iterdir():
        shutil.copy2(f, SITE / "img" / f.name)
    for d in DOWNLOADS:
        shutil.copy2(ROOT / d, SITE / "downloads" / Path(d).name)
    for src, out, label in PAGES:
        if src.endswith(".html"):  # hand-written fragment (Tools page)
            body = (ROOT / src).read_text()
            title = label
        else:
            md_text = rewrite_links(convert_alerts((ROOT / src).read_text()), src)
            body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "toc", "sane_lists"],
                                     extension_configs={"toc": {"slugify": slugify}}, output_format="html5")
            title = re.search(r"^# (.+)$", md_text, re.M).group(1) if re.search(r"^# (.+)$", md_text, re.M) else label
        (SITE / out).write_text(page(title, body, out, out == "index.html"))
    (SITE / ".nojekyll").write_text("")
    write_pwa()
    print(f"site/: {len(PAGES)} pages, {len(DOWNLOADS)} downloads")


if __name__ == "__main__":
    main()
