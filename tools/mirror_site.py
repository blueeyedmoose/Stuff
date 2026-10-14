#!/usr/bin/env python3
"""Mirror a website for offline reference: every HTML page, every file the
pages load, and desktop and mobile screenshots of each page.

Usage: python tools/mirror_site.py https://www.dints.com/ mirror

Output, all under OUT:
  pages/<path>/index.html      HTML exactly as the server sent it
  rendered/<path>/index.html   DOM after JavaScript ran (desktop browser)
  assets/<host>/<path>         CSS, JS, images, fonts, video, documents
  screenshots/<view>/<slug>.jpg  full-page screenshots, desktop and mobile
  manifest.json                pages, asset map, per-page requests, forms, failures
  REPORT.md                    human-readable summary
"""
import hashlib
import html as htmllib
import json
import os
import re
import sys
import time
from collections import Counter, deque
from urllib.parse import unquote, urldefrag, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

START = sys.argv[1]
OUT = sys.argv[2]
SITE_HOSTS = {urlparse(START).hostname, urlparse(START).hostname.removeprefix("www.")}
SITE_HOSTS |= {"www." + h for h in list(SITE_HOSTS) if not h.startswith("www.")}
MAX_PAGES = 500
MAX_BYTES = 95 * 1024 * 1024  # GitHub rejects files over 100 MB
DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
ASSET_EXT = re.compile(
    r"\.(css|js|mjs|json|png|jpe?g|gif|webp|avif|svg|ico|bmp|tiff?|woff2?|ttf|otf|eot|"
    r"mp4|webm|mov|m4v|ogv|ogg|mp3|wav|pdf|docx?|xlsx?|pptx?|zip|txt|webmanifest|lottie)$",
    re.I,
)
CSS_URL = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)|@import\s+(['"])([^'"]+)\3""", re.I)
ABS_URL = re.compile(r"""https?://[^\s'"<>()\\,]+""")
LINK_RELS = {"stylesheet", "icon", "shortcut", "apple-touch-icon", "apple-touch-icon-precomposed",
             "mask-icon", "manifest", "preload", "modulepreload", "prefetch", "image_src"}
PLATFORM_HINTS = {
    "Webflow": ("data-wf-site", "website-files.com", "webflow.js"),
    "WordPress": ("wp-content", "wp-includes"),
    "Wix": ("static.wixstatic.com", "wix.com"),
    "Squarespace": ("squarespace", "sqspcdn"),
    "Shopify": ("cdn.shopify.com",),
    "Framer": ("framerusercontent.com", "framer.com"),
}

session = requests.Session()
session.headers["User-Agent"] = DESKTOP_UA

manifest = {"start": START, "pages": {}, "assets": {}, "failures": {},
            "page_requests": {}, "forms": {}, "embeds": {}, "external_links": {}}


def clean(url):
    return urldefrag(url.strip())[0]


def is_http(url):
    return urlparse(url).scheme in ("http", "https")


def is_site(url):
    return urlparse(url).hostname in SITE_HOSTS


def is_asset_url(url):
    return bool(ASSET_EXT.search(urlparse(url).path))


def qhash(query):
    return hashlib.sha1(query.encode()).hexdigest()[:10]


def page_key(url):
    u = urlparse(url)
    path = "/" + u.path.strip("/")
    return path + ("?" + u.query if u.query else "")


def page_file(url, root="pages"):
    u = urlparse(url)
    path = unquote(u.path).strip("/")
    name = f"index__q{qhash(u.query)}.html" if u.query else "index.html"
    return os.path.join(root, path, name)


def slug(key):
    u = urlparse(key)
    s = u.path.strip("/").replace("/", "__") or "home"
    return s + (f"__q{qhash(u.query)}" if u.query else "")


def asset_file(url):
    u = urlparse(url)
    path = unquote(u.path).lstrip("/")
    if not path or path.endswith("/"):
        path += "index"
    if u.query:
        root, ext = os.path.splitext(path)
        path = f"{root}__q{qhash(u.query)}{ext}"
    return os.path.join("assets", u.hostname or "unknown-host", path)


def safe(rel):
    parts = []
    for part in rel.split("/"):
        if len(part.encode()) > 180:
            root, ext = os.path.splitext(part)
            part = root[:80] + "__" + hashlib.sha1(part.encode()).hexdigest()[:10] + ext[:20]
        parts.append(part)
    return "/".join(parts)


def write(rel, data):
    rel = safe(rel)
    path = os.path.join(OUT, rel)
    if os.path.isdir(path):  # a file and a folder share a name
        rel += "__file"
        path += "__file"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return rel


def fetch(url):
    """Return (response, error). Network errors and oversized files give an error."""
    err = None
    for attempt in range(3):
        try:
            r = session.get(url, timeout=90, stream=True)
            if int(r.headers.get("content-length") or 0) > MAX_BYTES:
                r.close()
                return None, "too large for git"
            data = r.content
            if len(data) > MAX_BYTES:
                return None, "too large for git"
            return r, None
        except requests.RequestException as e:
            err = str(e)
            time.sleep(2 * (attempt + 1))
    return None, err


def srcset(value):
    return [p.strip().split()[0] for p in value.split(",") if p.strip()]


def css_refs(text, base):
    out = set()
    for m in CSS_URL.finditer(text):
        ref = (m.group(2) or m.group(4) or "").strip()
        if ref and not ref.startswith(("data:", "#", "about:")):
            out.add(urljoin(base, ref))
    return {u for u in out if is_http(u)}


def html_refs(raw, base):
    """Links, asset URLs, forms and embeds referenced by an HTML document."""
    soup = BeautifulSoup(raw, "html.parser")
    tag = soup.find("base", href=True)
    if tag:
        base = urljoin(base, tag["href"])
    links, assets, forms, embeds = set(), set(), [], []
    for el in soup.find_all(True):
        if el.name == "form":
            forms.append({"id": el.get("id"), "name": el.get("name") or el.get("data-name"),
                          "action": el.get("action"), "method": el.get("method")})
        if el.name in ("iframe", "embed", "object"):
            embeds.append(el.get("src") or el.get("data"))
            continue
        for attr, val in el.attrs.items():
            if isinstance(val, list):
                val = " ".join(val)
            if not isinstance(val, str) or not val.strip():
                continue
            val = val.strip()
            if attr == "href":
                u = urljoin(base, val)
                if el.name in ("a", "area"):
                    links.add(u)
                elif el.name == "link" and (set(el.get("rel") or []) & LINK_RELS or is_asset_url(u)):
                    assets.add(u)
            elif attr in ("srcset", "data-srcset", "imagesrcset"):
                assets.update(urljoin(base, u) for u in srcset(val))
            elif attr == "style":
                assets.update(css_refs(val, base))
            elif attr in ("src", "poster") or attr.startswith("data-") or attr == "content":
                for part in val.split(","):
                    u = urljoin(base, part.strip())
                    if attr in ("src", "poster") or is_asset_url(u):
                        assets.add(u)
    for st in soup.find_all("style"):
        assets.update(css_refs(st.get_text(), base))
    text = htmllib.unescape(raw.replace("\\/", "/"))
    for m in ABS_URL.finditer(text):
        u = m.group(0).rstrip(".;:!?")
        if is_asset_url(u):
            assets.add(u)
    title = soup.title.get_text(strip=True) if soup.title else ""
    lang = soup.html.get("lang") if soup.html else None
    return ({clean(u) for u in links if is_http(u)}, {clean(u) for u in assets if is_http(u)},
            forms, [e for e in embeds if e], title, lang)


def sitemap_urls():
    out, todo, done = [], deque([urljoin(START, "/sitemap.xml")]), set()
    while todo:
        sm = todo.popleft()
        if sm in done:
            continue
        done.add(sm)
        r, err = fetch(sm)
        if r is None or r.status_code >= 400:
            continue
        write(asset_file(sm), r.content)
        for loc in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text):
            (todo if loc.endswith(".xml") else out).append(htmllib.unescape(loc))
    return out


def save_asset(url, r, via):
    rel = write(asset_file(url), r.content if via == "http" else r)
    return rel


def crawl():
    queue = deque([clean(START), urljoin(START, "/404")] + sitemap_urls())
    seen, asset_urls = set(), set()
    for extra in ("/robots.txt",):
        r, err = fetch(urljoin(START, extra))
        if r is not None and r.status_code < 400:
            write(asset_file(urljoin(START, extra)), r.content)
    while queue and len(manifest["pages"]) < MAX_PAGES:
        url = clean(queue.popleft())
        key = page_key(url)
        if key in seen:
            continue
        seen.add(key)
        r, err = fetch(url)
        if r is None:
            manifest["failures"][url] = err
            continue
        final = clean(r.url)
        ctype = r.headers.get("content-type", "")
        if r.status_code >= 400 and key != "/404":
            manifest["failures"][url] = f"HTTP {r.status_code}"
            continue
        if "html" not in ctype:
            asset_urls.add(url)
            continue
        if not is_site(final):
            manifest["failures"][url] = f"redirected off-site to {final}"
            continue
        fkey = page_key(final)
        if fkey != key:
            if fkey in manifest["pages"]:
                continue
            seen.add(fkey)
        rel = write(page_file(final), r.content)
        raw = r.content.decode("utf-8", errors="replace")
        links, assets, forms, embeds, title, lang = html_refs(raw, final)
        manifest["pages"][fkey] = {"url": final, "requested": url, "file": rel,
                                   "status": r.status_code, "title": title, "lang": lang}
        if forms:
            manifest["forms"][fkey] = forms
        if embeds:
            manifest["embeds"][fkey] = embeds
        asset_urls |= assets
        for link in links:
            if is_site(link):
                if is_asset_url(link) and not link.lower().endswith((".html", ".htm")):
                    asset_urls.add(link)
                elif page_key(link) not in seen:
                    queue.append(link)
            else:
                manifest["external_links"].setdefault(link, []).append(fkey)
        print(f"page {len(manifest['pages']):>3} {fkey}", flush=True)
        time.sleep(0.2)
    return asset_urls


def download_assets(urls):
    queue = deque(sorted(urls))
    while queue:
        url = queue.popleft()
        if url in manifest["assets"] or url in manifest["failures"]:
            continue
        r, err = fetch(url)
        if r is None or r.status_code >= 400:
            manifest["failures"][url] = err or f"HTTP {r.status_code}"
            continue
        try:
            rel = write(asset_file(url), r.content)
        except OSError as e:
            manifest["failures"][url] = f"write failed: {e}"
            continue
        ctype = r.headers.get("content-type", "")
        manifest["assets"][url] = {"file": rel, "type": ctype, "bytes": len(r.content), "via": "http"}
        if "css" in ctype or urlparse(url).path.endswith(".css"):
            queue.extend(css_refs(r.content.decode("utf-8", errors="replace"), clean(r.url)))
    print(f"assets: {len(manifest['assets'])}", flush=True)


def scroll_through(page):
    y, height = 0, page.evaluate("document.body.scrollHeight")
    while y < height and y < 60000:
        y += 500
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(200)
        height = page.evaluate("document.body.scrollHeight")
    page.wait_for_timeout(1000)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)


def render():
    from playwright.sync_api import sync_playwright
    views = (("desktop", {"width": 1440, "height": 900}, 1, False, DESKTOP_UA),
             ("mobile", {"width": 390, "height": 844}, 2, True, MOBILE_UA))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, viewport, scale, mobile, ua in views:
            ctx = browser.new_context(viewport=viewport, device_scale_factor=scale,
                                      is_mobile=mobile, has_touch=mobile, user_agent=ua)
            page = ctx.new_page()
            responses = []
            page.on("response", lambda resp: responses.append(resp))
            for key, info in manifest["pages"].items():
                responses.clear()
                try:
                    page.goto(info["url"], wait_until="load", timeout=90000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    scroll_through(page)
                    shot = os.path.join(OUT, "screenshots", name, slug(key) + ".jpg")
                    os.makedirs(os.path.dirname(shot), exist_ok=True)
                    page.screenshot(path=shot, full_page=True, type="jpeg", quality=70)
                    if name == "desktop":
                        write(page_file(info["url"], "rendered"), page.content().encode())
                except Exception as e:
                    manifest["failures"][f"render:{name}:{key}"] = str(e)[:300]
                    continue
                urls = set()
                for resp in list(responses):
                    url = clean(resp.url)
                    if not is_http(url):
                        continue
                    urls.add(url)
                    req = resp.request
                    if (resp.status != 200 or req.method != "GET" or req.resource_type == "document"
                            or url in manifest["assets"]):
                        continue
                    try:
                        body = resp.body()
                    except Exception:
                        continue
                    if len(body) > MAX_BYTES:
                        continue
                    try:
                        rel = write(asset_file(url), body)
                    except OSError:
                        continue
                    manifest["assets"][url] = {"file": rel, "type": resp.headers.get("content-type", ""),
                                               "bytes": len(body), "via": f"browser-{name}"}
                manifest["page_requests"].setdefault(key, {})[name] = sorted(urls)
                print(f"render {name} {key}", flush=True)
            ctx.close()
        browser.close()


def report():
    home = os.path.join(OUT, manifest["pages"].get("/", {}).get("file", "pages/index.html"))
    home_html = open(home, encoding="utf-8", errors="replace").read() if os.path.exists(home) else ""
    platforms = [n for n, marks in PLATFORM_HINTS.items() if any(m in home_html for m in marks)]
    hosts = Counter(urlparse(u).hostname for u in manifest["assets"])
    size = sum(a["bytes"] for a in manifest["assets"].values())
    lines = [f"# Mirror of {START}", "",
             f"- Pages: {len(manifest['pages'])}",
             f"- Assets: {len(manifest['assets'])} ({size / 1e6:.1f} MB)",
             f"- Platform hints: {', '.join(platforms) or 'none detected'}",
             f"- Failures: {len(manifest['failures'])}", "",
             "## Pages", "", "| Path | Title | lang |", "|---|---|---|"]
    lines += [f"| `{k}` | {v['title']} | {v['lang']} |" for k, v in sorted(manifest["pages"].items())]
    lines += ["", "## Asset hosts", "", "| Host | Files |", "|---|---|"]
    lines += [f"| {h} | {n} |" for h, n in hosts.most_common()]
    lines += ["", "## Forms", ""]
    lines += [f"- `{k}`: {f}" for k, fs in sorted(manifest["forms"].items()) for f in fs] or ["- none"]
    lines += ["", "## Embeds", ""]
    lines += [f"- `{k}`: {e}" for k, es in sorted(manifest["embeds"].items()) for e in es] or ["- none"]
    lines += ["", "## Failures", ""]
    lines += [f"- {u}: {e}" for u, e in sorted(manifest["failures"].items())] or ["- none"]
    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(OUT, exist_ok=True)
    asset_urls = crawl()
    download_assets(asset_urls)
    try:
        render()
    except Exception as e:
        manifest["failures"]["render"] = str(e)[:500]
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
    report()
    print(open(os.path.join(OUT, "REPORT.md")).read())


if __name__ == "__main__":
    main()
