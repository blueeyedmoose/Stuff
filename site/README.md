# Dints.com - French build

```
site/
  fr/                 French pages (the deliverable), one folder per page
  index.html, about/  English pages copied from the live site, with a Français link
                      added to the footer so the preview can switch languages
  sitemap-fr.xml      French sitemap with hreflang alternates
```

Every French page is the live English page with only the words changed.
Classes, layout, images, fonts, scripts, animations and Webflow IDs are
untouched, so it looks and behaves exactly like the English site. Images, CSS
and JavaScript still load from Webflow's CDN, exactly as the English site does.

## Added to each French page

- `<html lang="fr">` and French structured data (`inLanguage: fr-FR`)
- `hreflang` links (en / fr / x-default) and `og:locale`
- An **English** link in the footer's Company column, using the existing footer link style
  (the header is left exactly as it is, so the menu fits at the same widths as English)
- A small script that translates the screen-reader labels Webflow adds at runtime
- Internal links point to the `/fr/` version of each translated page

## Preview locally

```
python3 -m http.server 8000 --directory site
# English: http://localhost:8000/        French: http://localhost:8000/fr/
```

On any host other than Webflow, three things only work on Webflow's servers:
contact form submission, the Google tag route (`/nvhc9u4gx...`) and the
ecommerce checkout. Everything else works.

## Going live at www.dints.com/fr

The site is hosted by Webflow, which cannot serve extra static files under
its own domain. Two routes:

1. **Webflow Localization (recommended).** Add French as a secondary locale with
   the `/fr` subdirectory. Webflow then creates `/fr/...` for every page, keeps
   forms, CMS and interactions working, and adds hreflang plus a locale switcher.
   Paste or import the French text from `dints-fr/strings.json` (each entry has the
   English source and the French). Spanish and Portuguese become extra locales later.
2. **Reverse proxy.** Put a proxy (e.g. a Cloudflare Worker) in front of
   www.dints.com that serves `/fr/*` from these files and everything else from
   Webflow. This keeps the pages byte-for-byte as built here, but the contact form
   on `/fr/contact-us` would need re-pointing, since Webflow only accepts form posts
   from pages it hosts.

## Rebuilding

```
python3 tools/mirror_site.py https://www.dints.com/ mirror      # refresh the English source
python3 tools/i18n.py extract mirror/pages dints-fr/strings.json $(cat dints-fr/pages.txt)
python3 tools/merge_translations.py dints-fr/strings.json fr dints-fr/fr/*.json
python3 tools/build_site.py mirror/pages dints-fr/strings.json dints-fr/pages.txt site fr
python3 tools/verify_site.py site mirror dints-fr/strings.json dints-fr/pages.txt fr verify-out
```

`extract` keeps existing translations and lists anything new or changed in English
as untranslated, so updates only need the new strings.
