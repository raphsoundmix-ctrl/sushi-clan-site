#!/usr/bin/env python3
"""Pre-flight checks for the Sushi Clan landing page.

The site is one hand-written HTML file, so there is no build step to catch
mistakes. This script is the substitute: it fails when a local asset is
referenced but missing, when a shipped file blows the weight budget, or when
the head loses something the page needs (title, description, lang, viewport).

Run it locally: python3 tools/check.py
Exit code 0 means the page is safe to publish.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "index.html")

# Weight budget per shipped file, in bytes. The page itself is allowed to be
# big because it carries all the CSS and JS inline; images are not.
BUDGET = {
    "index.html": 260 * 1024,
    "*.png": 120 * 1024,
    "*.webp": 120 * 1024,
    "*.jpg": 120 * 1024,
}

SHIPPED_DIRS = {"", "docs/media"}


def read_page():
    with open(PAGE, encoding="utf-8") as f:
        return f.read()


def check_local_assets(html, errors):
    """Every src=/href= that is not a URL or an anchor must exist on disk."""
    refs = re.findall(r'(?:src|href|srcset)="([^"]+)"', html)
    for ref in sorted(set(refs)):
        if ref.startswith(("http://", "https://", "//", "#", "data:", "mailto:", "tel:")):
            continue
        path = os.path.join(ROOT, ref.split("?")[0])
        if not os.path.exists(path):
            errors.append(f"missing local asset: {ref}")


def check_head(html, errors):
    required = {
        "<title>": "page title",
        'name="description"': "meta description",
        'lang="': "html lang attribute",
        'name="viewport"': "viewport meta",
        'name="theme-color"': "theme-color meta",
    }
    for needle, label in required.items():
        if needle not in html:
            errors.append(f"head is missing the {label}")


def check_budget(errors):
    import fnmatch

    for rel_dir in sorted(SHIPPED_DIRS):
        directory = os.path.join(ROOT, rel_dir)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            size = os.path.getsize(path)
            for pattern, limit in BUDGET.items():
                if fnmatch.fnmatch(name, pattern) or name == pattern:
                    if size > limit:
                        where = os.path.join(rel_dir, name) if rel_dir else name
                        errors.append(
                            f"{where} is {size // 1024} KB, over the {limit // 1024} KB budget"
                        )
                    break


def check_no_leftovers(html, errors):
    """Things that are fine while building and embarrassing in production."""
    for pattern, label in [
        (r"console\.log\(", "console.log call"),
        (r"\bTODO\b", "TODO marker"),
        (r"localhost:\d+", "localhost URL"),
    ]:
        if re.search(pattern, html):
            errors.append(f"index.html still contains a {label}")


def main():
    if not os.path.exists(PAGE):
        print("index.html not found", file=sys.stderr)
        return 1

    html = read_page()
    errors = []
    check_local_assets(html, errors)
    check_head(html, errors)
    check_budget(errors)
    check_no_leftovers(html, errors)

    page_kb = os.path.getsize(PAGE) // 1024
    assets = [n for n in os.listdir(ROOT) if n.endswith((".png", ".webp", ".jpg"))]
    asset_kb = sum(os.path.getsize(os.path.join(ROOT, n)) for n in assets) // 1024

    print(f"index.html   {page_kb} KB")
    print(f"root images  {asset_kb} KB across {len(assets)} files")

    if errors:
        print("\nFAILED")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
