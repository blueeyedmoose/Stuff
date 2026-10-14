#!/usr/bin/env python3
"""Pull translatable text out of HTML pages and put translations back in.

The original HTML is never re-serialised. Text runs and attribute values are
located by character offset and spliced, so markup, classes, Webflow IDs,
scripts and styles stay byte-for-byte identical to the English source.

A "unit" is one translatable string:
  * a run of text plus inline tags (span, strong, a, br...) between block
    boundaries; inline tags become numbered placeholders so a translation can
    move them, e.g. 'Get up to <1>$50m</1> credit' -> 'Jusqu'à <1>50 M$</1> de crédit'
  * a translatable attribute value (alt, title, placeholder, aria-label,
    submit button value, data-wait, meta description/og/twitter text)
  * the <title> element

Commands:
  extract PAGES_ROOT OUT_JSON [page ...]   write/refresh the string catalogue
  build   PAGES_ROOT IN_JSON OUT_ROOT LANG [page ...]   write translated pages
"""
import html
import json
import re
import sys
from pathlib import Path

TOKEN = re.compile(
    r"""
      (?P<comment><!--.*?-->)
    | (?P<raw><(?P<rawname>script|style|textarea|title)\b(?:[^"'>]|"[^"]*"|'[^']*')*>.*?</(?P=rawname)\s*>)
    | (?P<decl><![^>]*>)
    | (?P<tag></?[A-Za-z][^\s/>]*(?:[^"'>]|"[^"]*"|'[^']*')*>)
    | (?P<text>[^<]+|<)
    """,
    re.S | re.I | re.X,
)
TAG_NAME = re.compile(r"</?([A-Za-z][^\s/>]*)")
ATTR = re.compile(r"""\s([^\s"'>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+)))?""")
INLINE = {"a", "abbr", "b", "bdi", "bdo", "br", "cite", "code", "em", "font", "i", "mark",
          "q", "s", "small", "span", "strong", "sub", "sup", "time", "u", "wbr"}
VOID = {"br", "wbr"}
ATTRS = {"alt", "title", "placeholder", "aria-label", "data-wait", "label"}
META_KEYS = {"description", "og:title", "og:description", "twitter:title",
             "twitter:description", "og:image:alt", "twitter:image:alt"}
JSON_STRING = re.compile(r'"((?:[^"\\]|\\.)*)"(\s*:)?')
JSONLD_KEYS = {"name", "description", "headline", "alternativeHeadline", "text", "slogan",
               "serviceType", "category", "articleSection", "abstract", "knowsAbout",
               "keywords", "jobTitle", "disambiguatingDescription", "caption"}
PLACEHOLDER = re.compile(r"</?\d+/?>")
WORTH = re.compile(r"[A-Za-zÀ-ÿ]|\d[.,]\d")


def tokens(raw):
    for m in TOKEN.finditer(raw):
        kind = next(k for k in ("comment", "raw", "decl", "tag", "text") if m.group(k) is not None)
        yield kind, m.start(), m.end(), m.group(0)


def open_tag_end(text):
    """Length of the opening tag at the start of a raw element."""
    return re.match(r"""<[A-Za-z][^\s/>]*(?:[^"'>]|"[^"]*"|'[^']*')*>""", text).end()


def tag_info(text):
    name = TAG_NAME.match(text).group(1).lower()
    closing = text.startswith("</")
    void = name in VOID or text.rstrip(">").rstrip().endswith("/")
    return name, closing, void


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


class Unit:
    """One translatable span of the raw HTML."""

    def __init__(self, start, end, key, tags, kind, quote=None):
        self.start, self.end, self.key, self.tags, self.kind, self.quote = start, end, key, tags, kind, quote


def run_unit(run):
    """Turn a list of (kind, start, end, text) tokens into a Unit, or None."""
    def has_words(tok):
        return tok[0] == "text" and html.unescape(tok[3]).strip(" \t\r\n\xa0") != ""

    if not any(has_words(t) for t in run):
        return []
    run = list(run)
    changed = True
    while changed and run:
        changed = False
        # matching partners within the run, by index
        stack, partner = [], {}
        for i, t in enumerate(run):
            if t[0] != "tag":
                continue
            name, closing, void = tag_info(t[3])
            if void:
                continue
            if not closing:
                stack.append((name, i))
            else:
                for j in range(len(stack) - 1, -1, -1):
                    if stack[j][0] == name:
                        partner[i], partner[stack[j][1]] = stack[j][1], i
                        del stack[j:]
                        break
        first, last = run[0], run[-1]
        if first[0] == "text" and not has_words(first):
            run.pop(0); changed = True; continue
        if last[0] == "text" and not has_words(last):
            run.pop(); changed = True; continue
        if first[0] == "tag" and (0 not in partner or tag_info(first[3])[2]):
            run.pop(0); changed = True; continue
        if last[0] == "tag" and (len(run) - 1 not in partner or tag_info(last[3])[2]):
            run.pop(); changed = True; continue
        if first[0] == "tag" and partner.get(0) == len(run) - 1:
            run = run[1:-1]; changed = True; continue
    if not run or not any(has_words(t) for t in run):
        return []
    # leftover unbalanced tags in the middle: fall back to one unit per text token
    depth = {}
    for t in run:
        if t[0] == "tag":
            name, closing, void = tag_info(t[3])
            if not void:
                depth[name] = depth.get(name, 0) + (-1 if closing else 1)
                if depth[name] < 0:
                    break
    if any(depth.values()):
        return [u for t in run if has_words(t) for u in run_unit([t])]
    parts, tags, stack, n = [], [], [], 0
    for t in run:
        if t[0] == "text":
            parts.append(html.unescape(t[3]))
            continue
        name, closing, void = tag_info(t[3])
        if void:
            n += 1
            parts.append(f"<{n}/>")
        elif not closing:
            n += 1
            stack.append(n)
            parts.append(f"<{n}>")
        else:
            parts.append(f"</{stack.pop()}>")
        tags.append(t[3])
    key = norm("".join(parts))
    start, end = run[0][1], run[-1][2]
    if run[0][0] == "text":
        start += len(run[0][3]) - len(run[0][3].lstrip())
    if run[-1][0] == "text":
        end -= len(run[-1][3]) - len(run[-1][3].rstrip())
    if not WORTH.search(PLACEHOLDER.sub("", key)):
        return []
    return [Unit(start, end, key, tags, "text")]


def attr_units(tok_start, text):
    name, closing, _ = tag_info(text)
    if closing:
        return []
    attrs = {m.group(1).lower(): m for m in ATTR.finditer(text)}
    out = []
    for attr, m in attrs.items():
        val = next((g for g in m.groups()[1:] if g is not None), None)
        if val is None:
            continue
        ok = attr in ATTRS
        if attr == "value" and name in ("input", "button"):
            typ = attrs.get("type")
            typ = next((g for g in typ.groups()[1:] if g is not None), "") if typ else ""
            ok = typ.lower() in ("submit", "button", "reset")
        if attr == "content" and name == "meta":
            k = attrs.get("name") or attrs.get("property")
            k = next((g for g in k.groups()[1:] if g is not None), "") if k else ""
            ok = k.lower() in META_KEYS
        key = norm(html.unescape(val))
        if not ok or not WORTH.search(key):
            continue
        gi = next(i for i, g in enumerate(m.groups()[1:], start=2) if g is not None)
        quote = '"' if gi == 2 else "'" if gi == 3 else '"'
        out.append(Unit(tok_start + m.start(gi), tok_start + m.end(gi), key, [], "attr:" + attr, quote))
    return out


def jsonld_units(start, text):
    """String values under human-readable keys in a JSON-LD block."""
    body_start = open_tag_end(text)
    body = text[body_start:text.lower().rindex("</script")]
    out, key = [], None
    for m in JSON_STRING.finditer(body):
        value = json.loads('"' + m.group(1) + '"')
        if m.group(2):
            key = value
            continue
        if key in JSONLD_KEYS and WORTH.search(value):
            out.append(Unit(start + body_start + m.start(1), start + body_start + m.end(1),
                            norm(value), [], "jsonld:" + key))
    return out


def units(raw):
    found, run = [], []
    for kind, start, end, text in tokens(raw):
        if kind == "text" or (kind == "tag" and tag_info(text)[0] in INLINE):
            run.append((kind, start, end, text))
        else:
            found += run_unit(run)
            run = []
        if kind == "tag":
            found += attr_units(start, text)
        elif kind != "raw":
            continue
        elif text[:9].lower() == "<textarea":
            found += attr_units(start, text[:open_tag_end(text)])
        elif text[:7].lower() == "<script" and "application/ld+json" in text[:open_tag_end(text)]:
            found += jsonld_units(start, text)
        elif text[:6].lower() == "<title":
            inner_start = start + open_tag_end(text)
            inner_end = start + text.lower().rindex("</title")
            key = norm(html.unescape(raw[inner_start:inner_end]))
            if WORTH.search(key):
                found.append(Unit(inner_start, inner_end, key, [], "title"))
    found += run_unit(run)
    return sorted(found, key=lambda u: u.start)


def page_files(root, pages):
    root = Path(root)
    for p in pages:
        rel = Path(p.strip("/")) / "index.html"
        yield p, root / rel


def extract(root, out_json, pages):
    out = Path(out_json)
    catalogue = json.loads(out.read_text()) if out.exists() else {}
    seen = {}
    for page, path in page_files(root, pages):
        for u in units(path.read_text(encoding="utf-8")):
            entry = seen.setdefault(u.key, {"en": u.key, "kinds": [], "pages": []})
            if u.kind not in entry["kinds"]:
                entry["kinds"].append(u.kind)
            if page not in entry["pages"]:
                entry["pages"].append(page)
    merged = {}
    for key, entry in seen.items():
        old = catalogue.get(key, {})
        entry["fr"] = old.get("fr", "")
        merged[key] = entry
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=1))
    todo = sum(1 for e in merged.values() if not e["fr"])
    print(f"{len(merged)} unique strings, {todo} untranslated")


def render(translation, unit):
    """Turn a translated key back into HTML, restoring the original tags."""
    if unit.kind.startswith("jsonld:"):
        return json.dumps(translation, ensure_ascii=False)[1:-1]
    if unit.kind.startswith("attr:"):
        text = html.escape(translation, quote=False)
        return text.replace(unit.quote, "&quot;" if unit.quote == '"' else "&#39;")
    out, pos = [], 0
    order = {}
    n = 0
    stack = []
    # map placeholder number -> original tag text, in source order
    for tag in unit.tags:
        name, closing, void = tag_info(tag)
        if void:
            n += 1
            order[f"<{n}/>"] = tag
        elif not closing:
            n += 1
            stack.append(n)
            order[f"<{n}>"] = tag
        else:
            order[f"</{stack.pop()}>"] = tag
    for m in PLACEHOLDER.finditer(translation):
        out.append(html.escape(translation[pos:m.start()], quote=False))
        out.append(order[m.group(0)])
        pos = m.end()
    out.append(html.escape(translation[pos:], quote=False))
    return "".join(out)


def check(entry):
    """Problems with a translation's placeholders, or [] if it is usable."""
    want = sorted(PLACEHOLDER.findall(entry["en"]))
    got = sorted(PLACEHOLDER.findall(entry["fr"]))
    return [] if want == got else [f"placeholders {want} != {got}"]


def translate_html(raw, catalogue, lang):
    out, pos, missing = [], 0, []
    for u in units(raw):
        entry = catalogue.get(u.key)
        if not entry or not entry.get(lang) or check({"en": u.key, "fr": entry[lang]}):
            missing.append(u.key)
            continue
        out.append(raw[pos:u.start])
        out.append(render(entry[lang], u))
        pos = u.end
    out.append(raw[pos:])
    return "".join(out), missing


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "extract":
        extract(sys.argv[2], sys.argv[3], sys.argv[4:])
    else:
        sys.exit(f"unknown command {cmd}")
