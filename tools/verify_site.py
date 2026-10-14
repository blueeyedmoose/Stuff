#!/usr/bin/env python3
"""Check a built translation in a real browser.

For every translated page, at desktop and mobile widths:
  * load it from a local server and record console errors and failed requests
  * take a full-page screenshot and put it side by side with the English one
  * list visible text that is still identical to an English source string
  * check every on-site link resolves to a page in the build

Usage: verify_site.py SITE_DIR MIRROR_DIR CATALOGUE PAGES_TXT LANG OUT_DIR [executable_path]
"""
import functools
import http.server
import json
import os
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image
from playwright.sync_api import sync_playwright

SITE_DIR, MIRROR, CATALOGUE, PAGES_TXT, LANG, OUT = sys.argv[1:7]
EXE = sys.argv[7] if len(sys.argv) > 7 else None
PORT = 8800
VIEWS = {"desktop": dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1),
         "mobile": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                        is_mobile=True, has_touch=True)}
# Visible strings that are legitimately the same in both languages.
SAME_OK = {"Dints", "Dints International Ltd", "sales@dints.com", "gdem@dints.com", "Whatsapp",
           "SOLUTIONS", "solutions", "Contact", "Agriculture", "Construction", "Expansion", "FAQ",
           "Images", "Logo", "Services", "Podcasts", "Total", "Message", "Pro", "Premium",
           "Enterprise", "International", "Menu", "agriculture", "Apple Pay", "Geoffrey de Mowbray",
           "15-19 Bloomsbury Way, London WC1A 2TH, United Kingdom", "Loonis Studio", "EN", "Sourcing",
           "$ 0.00 USD"}


def slug(page):
    return page.strip("/").replace("/", "__") or "home"


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE_DIR)
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def scroll_through(page):
    y, height = 0, page.evaluate("document.body.scrollHeight")
    while y < height and y < 60000:
        y += 500
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(150)
        height = page.evaluate("document.body.scrollHeight")
    page.wait_for_timeout(800)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(800)


def side_by_side(left, right, dest, label_h=0):
    a, b = Image.open(left).convert("RGB"), Image.open(right).convert("RGB")
    scale = 700 / max(a.width, b.width)
    a = a.resize((int(a.width * scale), int(a.height * scale)))
    b = b.resize((int(b.width * scale), int(b.height * scale)))
    canvas = Image.new("RGB", (a.width + b.width + 20, max(a.height, b.height)), "white")
    canvas.paste(a, (0, 0))
    canvas.paste(b, (a.width + 20, 0))
    canvas.save(dest, quality=70)
    return a.height, b.height


def main():
    catalogue = json.load(open(CATALOGUE, encoding="utf-8"))
    english = {k for k, v in catalogue.items() if v.get(LANG) and v[LANG] != k and "<" not in k}
    pages = open(PAGES_TXT).read().split()
    out = Path(OUT)
    out.mkdir(parents=True, exist_ok=True)
    srv = serve()
    results = {}
    links_seen = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(**({"executable_path": EXE} if EXE else {}))
        for view, opts in VIEWS.items():
            ctx = browser.new_context(**opts)
            page = ctx.new_page()
            errors, failed = [], []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("requestfailed", lambda r: failed.append(r.url))
            for path in pages:
                errors.clear()
                failed.clear()
                url = f"http://127.0.0.1:{PORT}/{LANG}{path if path != '/' else '/'}"
                resp = page.goto(url, wait_until="load", timeout=90000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                scroll_through(page)
                shot = out / f"{view}-{slug(path)}.jpg"
                page.screenshot(path=str(shot), full_page=True, type="jpeg", quality=70)
                en_shot = Path(MIRROR) / "screenshots" / view / f"{slug(path)}.jpg"
                heights = side_by_side(en_shot, shot, out / f"compare-{view}-{slug(path)}.jpg") if en_shot.exists() else None
                visible = page.evaluate("document.body.innerText")
                lines = {l.strip() for l in visible.split("\n") if l.strip()}
                leftovers = sorted(l for l in lines if l in english and l not in SAME_OK)
                hrefs = page.evaluate("[...document.querySelectorAll('a[href]')].map(a => a.getAttribute('href'))")
                for h in hrefs:
                    u = urlparse(h)
                    if not u.scheme and not u.netloc and u.path.startswith("/"):
                        links_seen.setdefault(u.path, set()).add(path)
                lang_attr = page.evaluate("document.documentElement.lang")
                results.setdefault(path, {})[view] = {
                    "status": resp.status if resp else None, "lang": lang_attr,
                    "console_errors": sorted(set(errors))[:10],
                    "failed_requests": sorted(set(f for f in failed if "127.0.0.1" in f or "website-files" in f))[:10],
                    "english_leftovers": leftovers,
                    "screenshot_heights_en_vs_fr": heights,
                }
                print(f"{view:7} {path:42} status={resp.status if resp else '-'} lang={lang_attr} "
                      f"leftovers={len(leftovers)} errors={len(set(errors))}", flush=True)
            ctx.close()
        browser.close()
    broken = {}
    for path, sources in sorted(links_seen.items()):
        local = Path(SITE_DIR) / path.strip("/") / "index.html" if not Path(path).suffix else Path(SITE_DIR) / path.strip("/")
        if not local.exists():
            broken[path] = sorted(sources)[:5]
    srv.shutdown()
    report = {"pages": results, "links_checked": len(links_seen), "links_missing_from_build": broken}
    (out / "verify.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(f"\nlinks checked: {len(links_seen)}; not in build: {len(broken)}")
    for path, sources in broken.items():
        print(f"  {path}  (linked from {', '.join(sources)})")


if __name__ == "__main__":
    main()
