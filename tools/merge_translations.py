#!/usr/bin/env python3
"""Merge translation batch files into the string catalogue.

Batch files map a 7-character ID (sha1 of the English string) to the
translation. Two special keys map English text directly:
"__countries__" and "__by_english__".

Usage: merge_translations.py CATALOGUE.json LANG BATCH.json [BATCH.json ...]
"""
import hashlib
import json
import re
import sys

PLACEHOLDER = re.compile(r"</?\d+/?>")


def typography_fr(s):
    """French typographic conventions: curly apostrophes, ellipsis, and a
    non-breaking space before ; : ! ?"""
    s = s.replace("'", "’").replace("...", "…")
    return re.sub(r"(?<=\S)[   ]?([;:!?])(?=\s|$|<)", " \\1", s)


TYPOGRAPHY = {"fr": typography_fr}


def main(catalogue_path, lang, batches):
    catalogue = json.load(open(catalogue_path, encoding="utf-8"))
    by_id = {hashlib.sha1(k.encode()).hexdigest()[:7]: k for k in catalogue}
    fix = TYPOGRAPHY.get(lang, lambda s: s)
    unknown, problems = [], []
    for path in batches:
        for key, value in json.load(open(path, encoding="utf-8")).items():
            if key.startswith("__"):
                pairs = value.items()
            elif key in by_id:
                pairs = [(by_id[key], value)]
            else:
                unknown.append(key)
                continue
            for en, text in pairs:
                if en not in catalogue:
                    unknown.append(en)
                    continue
                text = fix(text)
                if sorted(PLACEHOLDER.findall(en)) != sorted(PLACEHOLDER.findall(text)):
                    problems.append(f"placeholder mismatch: {en!r} -> {text!r}")
                catalogue[en][lang] = text
    missing = [k for k, v in catalogue.items() if not v.get(lang)]
    json.dump(catalogue, open(catalogue_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(catalogue) - len(missing)}/{len(catalogue)} translated")
    for k in unknown:
        print("unknown id/string:", k)
    for p in problems:
        print(p)
    for k in missing:
        print("missing:", hashlib.sha1(k.encode()).hexdigest()[:7], k)
    return 1 if (unknown or problems) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3:]))
