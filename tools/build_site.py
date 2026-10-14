#!/usr/bin/env python3
"""Build a translated copy of the mirrored site under /<lang>/.

Each page starts from the English HTML exactly as Webflow served it. Only
text is swapped (see i18n.py), then:
  * <html lang> is set to the target language
  * links to pages that have a translation point to their /<lang>/ version
  * JSON-LD "inLanguage" and the page's own "url" are updated
  * hreflang alternates and og:locale are added to <head>
  * a language link is added to the footer's Company column, in the footer link style
  * Webflow's runtime screen-reader labels are translated after load

English pages are written alongside (unchanged apart from a language link
the other way) so the preview can switch between the two.

Usage: build_site.py MIRROR_PAGES CATALOGUE PAGES_TXT OUT_DIR LANG
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

sys.path.insert(0, str(Path(__file__).parent))
import i18n  # noqa: E402

SITE = "https://www.dints.com"
SITE_HOSTS = {"www.dints.com", "dints.com"}
HTML_LANG = re.compile(r'(<html\b[^>]*\blang=")([^"]*)(")', re.I)
HREF = re.compile(r'(\shref=")([^"]*)(")')
# Last link of the footer's final column ("Company"), which has room for one more.
FOOTER_LAST_LINK = re.compile(r'(<a [^>]*class="footer_nav-link[^"]*"[^>]*>[^<]*</a>)(</div></div></nav>)')
JSONLD = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.S)
LOCALES = {"fr": "fr_FR", "en": "en_GB"}
LABELS = {"fr": "Français", "en": "English"}
JSONLD_LANG = {"fr": "fr-FR"}

# Screen-reader labels that webflow.js writes at runtime, in English.
ARIA_SCRIPT = {
    "fr": """<script>
/* Dints FR: translate the screen-reader labels webflow.js adds at runtime */
(function () {
  var exact = {"home": "accueil", "carousel": "carrousel", "Contact Form": "Formulaire de contact",
               "Contact Form success": "Formulaire de contact : envoyé",
               "Contact Form failure": "Formulaire de contact : erreur"};
  function fix(el) {
    var v = el.getAttribute && el.getAttribute("aria-label"), m;
    if (!v) return;
    if (exact[v]) el.setAttribute("aria-label", exact[v]);
    else if ((m = v.match(/^Show slide (\\d+) of (\\d+)$/))) el.setAttribute("aria-label", "Afficher la diapositive " + m[1] + " sur " + m[2]);
    else if ((m = v.match(/^(\\d+) of (\\d+)$/))) el.setAttribute("aria-label", m[1] + " sur " + m[2]);
  }
  function scan(root) { fix(root); root.querySelectorAll && root.querySelectorAll("[aria-label]").forEach(fix); }
  new MutationObserver(function (records) {
    records.forEach(function (r) {
      if (r.type === "attributes") fix(r.target);
      else r.addedNodes.forEach(function (n) { if (n.nodeType === 1) scan(n); });
    });
  }).observe(document.documentElement, {subtree: true, childList: true, attributes: true, attributeFilter: ["aria-label"]});
  scan(document.documentElement);
})();
</script>""",
}


def lang_path(path, lang):
    """/about -> /fr/about, / -> /fr/"""
    return f"/{lang}/" if path == "/" else f"/{lang}{path}"


def norm_path(path):
    return "/" + path.strip("/") if path.strip("/") else "/"


def rewrite_links(html_text, translated, lang):
    """Point <a href> at translated pages; leave everything else alone."""
    out, pos = [], 0
    for kind, start, end, text in i18n.tokens(html_text):
        if kind != "tag" or i18n.tag_info(text)[0] not in ("a", "area"):
            continue
        m = HREF.search(text)
        if not m:
            continue
        u = urlparse(m.group(2))
        local = not u.scheme and not u.netloc and u.path.startswith("/")
        if not (local or u.hostname in SITE_HOSTS) or norm_path(u.path) not in translated:
            continue
        new_path = lang_path(norm_path(u.path), lang)
        href = urlunparse(u._replace(path=new_path)) if not local else urlunparse(("", "", new_path, u.params, u.query, u.fragment))
        out.append(html_text[pos:start + m.start(2)])
        out.append(href)
        pos = start + m.end(2)
    out.append(html_text[pos:])
    return "".join(out)


def fix_jsonld(html_text, page, lang):
    def one(m):
        body = m.group(2)
        body = re.sub(r'("inLanguage"\s*:\s*")en[^"]*(")', r"\g<1>" + JSONLD_LANG[lang] + r"\2", body)
        if page != "/":
            body = re.sub(r'("url"\s*:\s*")' + re.escape(page) + r'(")', r"\g<1>" + lang_path(page, lang) + r"\2", body)
        return m.group(1) + body + m.group(3)
    return JSONLD.sub(one, html_text)


def head_tags(page, lang, other):
    if page == "/404":
        return f'<meta property="og:locale" content="{LOCALES[lang]}"/>'
    urls = {other: SITE + page, lang: SITE + (page if lang == "en" else lang_path(page, lang))}
    if lang == "en":
        urls = {"en": SITE + page, other: SITE + lang_path(page, other)}
    tags = [f'<link rel="alternate" hreflang="{code}" href="{url}"/>' for code, url in sorted(urls.items())]
    tags.append(f'<link rel="alternate" hreflang="x-default" href="{SITE + page}"/>')
    tags.append(f'<meta property="og:locale" content="{LOCALES[lang]}"/>')
    return "".join(tags)


def add_switcher(html_text, href, target_lang):
    """Add a link to the other language at the end of the footer's Company column."""
    link = (f'<a href="{href}" hreflang="{target_lang}" lang="{target_lang}" '
            f'class="footer_nav-link">{LABELS[target_lang]}</a>')
    new, n = FOOTER_LAST_LINK.subn(lambda m: m.group(1) + link + m.group(2), html_text, count=1)
    return new, n


def build(pages_root, catalogue_path, pages_txt, out_dir, lang):
    catalogue = json.load(open(catalogue_path, encoding="utf-8"))
    pages = open(pages_txt).read().split()
    translated = set(pages)
    out = Path(out_dir)
    report = []
    for page in pages:
        rel = Path(page.strip("/")) / "index.html"
        raw = (Path(pages_root) / rel).read_text(encoding="utf-8")

        # translated page
        text, missing = i18n.translate_html(raw, catalogue, lang)
        text = HTML_LANG.sub(lambda m: m.group(1) + lang + m.group(3), text, count=1)
        text = rewrite_links(text, translated, lang)
        text = fix_jsonld(text, page, lang)
        if lang == "fr":
            text = text.replace("Quantity%3A%20", quote("Quantité : "))
        text = text.replace("</head>", head_tags(page, lang, "en") + "</head>", 1)
        text, switched = add_switcher(text, page, "en")
        text = text.replace("</body>", ARIA_SCRIPT.get(lang, "") + "</body>", 1)
        dest = out / lang / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")

        # English page with a link to the translation
        en = raw.replace("</head>", head_tags(page, "en", lang) + "</head>", 1)
        en, _ = add_switcher(en, lang_path(page, lang), lang)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(en, encoding="utf-8")
        report.append((page, len(missing), switched))
        for key in missing:
            print(f"  untranslated on {page}: {key!r}")

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for page in pages:
        if page == "/404":
            continue
        loc = SITE + lang_path(page, lang)
        sitemap += [f"  <url><loc>{loc}</loc>",
                    f'    <xhtml:link rel="alternate" hreflang="en" href="{SITE + page}"/>',
                    f'    <xhtml:link rel="alternate" hreflang="{lang}" href="{loc}"/>',
                    "  </url>"]
    sitemap.append("</urlset>")
    (out / f"sitemap-{lang}.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")
    for page, n_missing, switched in report:
        print(f"{page:45} untranslated={n_missing} switcher={'yes' if switched else 'NO'}")


if __name__ == "__main__":
    build(*sys.argv[1:6])
