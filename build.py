#!/usr/bin/env python3
"""Build the site: posts/<word>.md become <word>.html, next to the hand-written pages.

    python3 build.py              # writes _site/
    python3 -m http.server -d _site

A post starts with front matter:

    ---
    title: Reboot
    date: 2026-09-13
    description: One line for search results and link previews.
    ---

Optional: `updated: YYYY-MM-DD`, `draft: true` (not built).
Post names are one lowercase word (reboot.md -> reboot.html).
"""

import argparse
import datetime
import email.utils
import html
import json
import pathlib
import re
import shutil
import string
import sys

import markdown

SITE_URL = "https://nizarmah.com"
SITE_NAME = "Nizar Mah"
AUTHOR = {
    "@type": "Person",
    "name": "Nizar Mahmoud",
    "alternateName": "Nizar Mah",
    "url": SITE_URL,
    "sameAs": [
        "https://github.com/nizarmah",
        "https://www.linkedin.com/in/nizarmah/",
        "https://x.com/nizarmah_",
    ],
}

ROOT = pathlib.Path(__file__).resolve().parent
SLUG = re.compile(r"^[a-z0-9]+$")
STATIC_SUFFIXES = {".html", ".ico", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf"}
WRITINGS = re.compile(r"(<!-- writings -->\n)(.*?)(\s*<!-- /writings -->)", re.S)


class BuildError(Exception):
    pass


def parse(text, name):
    """Front matter dict and Markdown body of one post."""
    if not text.startswith("---\n"):
        raise BuildError(f"{name}: must start with --- front matter")
    head, sep, body = text[4:].partition("\n---\n")
    if not sep:
        raise BuildError(f"{name}: front matter is not closed with ---")
    meta = {}
    for line in head.splitlines():
        if line.strip():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    for key in ("title", "date"):
        if not meta.get(key):
            raise BuildError(f"{name}: front matter needs {key}")
    for key in ("date", "updated"):
        if meta.get(key):
            try:
                datetime.date.fromisoformat(meta[key])
            except ValueError:
                raise BuildError(f"{name}: {key} must be YYYY-MM-DD, got {meta[key]!r}")
    meta.setdefault("description", meta["title"])
    return meta, body.strip() + "\n"


def external_links(fragment):
    """Open off-site links in a new tab, as the hand-written pages do."""
    return re.sub(r'<a href="(https?://[^"]+)">', r'<a href="\1" target="_blank" rel="noopener">', fragment)


def indent(fragment, spaces=6):
    pad = " " * spaces
    return "\n".join(pad + line if line else line for line in fragment.splitlines())


def load_posts(posts_dir):
    posts = []
    for path in sorted(posts_dir.glob("*.md")):
        slug = path.stem
        if not SLUG.match(slug):
            raise BuildError(f"{path.name}: post names are one lowercase word, like reboot.md")
        meta, body = parse(path.read_text(encoding="utf-8"), path.name)
        if meta.get("draft", "").lower() == "true":
            continue
        posts.append({"slug": slug, "meta": meta, "body": body})
    posts.sort(key=lambda p: p["meta"]["date"], reverse=True)
    return posts


def render_post(template, post):
    meta = post["meta"]
    url = f"{SITE_URL}/{post['slug']}.html"
    date = datetime.date.fromisoformat(meta["date"])
    jsonld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": meta["title"],
        "description": meta["description"],
        "datePublished": meta["date"],
        "dateModified": meta.get("updated") or meta["date"],
        "url": url,
        "mainEntityOfPage": url,
        "author": AUTHOR,
    }
    body = external_links(markdown.markdown(post["body"]))
    return template.substitute(
        title=html.escape(meta["title"]),
        description=html.escape(meta["description"], quote=True),
        url=url,
        site_url=SITE_URL,
        site_name=SITE_NAME,
        jsonld=json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/"),
        date_long=f"{date:%A, %B} {date.day}, {date.year}",
        body=indent(body),
    )


def render_index(source, posts):
    if not WRITINGS.search(source):
        raise BuildError("index.html needs <!-- writings --> and <!-- /writings --> around the post list")
    items = "\n".join(
        f'      <p><a href="./{p["slug"]}.html" rel="noopener">{html.escape(p["meta"]["title"])}</a></p>'
        for p in posts
    )
    out = WRITINGS.sub(lambda m: m.group(1) + items + m.group(3), source)
    person = {"@context": "https://schema.org", **AUTHOR}
    head_extra = (
        f'    <link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{SITE_URL}/feed.xml" />\n'
        f'    <script type="application/ld+json">{json.dumps(person)}</script>\n'
    )
    return out.replace("  </head>", head_extra + "  </head>", 1)


def sitemap(pages, posts):
    newest = posts[0]["meta"]["date"] if posts else datetime.date.today().isoformat()
    rows = [(f"{SITE_URL}/", newest)]
    rows += [(f"{SITE_URL}/{name}", None) for name in pages if name != "index.html"]
    rows += [(f"{SITE_URL}/{p['slug']}.html", p["meta"].get("updated") or p["meta"]["date"]) for p in posts]
    body = "".join(
        f"  <url><loc>{loc}</loc>" + (f"<lastmod>{mod}</lastmod>" if mod else "") + "</url>\n" for loc, mod in rows
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}</urlset>\n'


def feed(posts):
    items = []
    for p in posts:
        d = datetime.datetime.fromisoformat(p["meta"]["date"]).replace(tzinfo=datetime.timezone.utc)
        url = f"{SITE_URL}/{p['slug']}.html"
        items.append(
            "    <item>\n"
            f"      <title>{html.escape(p['meta']['title'])}</title>\n"
            f"      <link>{url}</link>\n"
            f"      <guid>{url}</guid>\n"
            f"      <pubDate>{email.utils.format_datetime(d)}</pubDate>\n"
            f"      <description>{html.escape(p['meta']['description'])}</description>\n"
            "    </item>\n"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n'
        f"    <title>{SITE_NAME}</title>\n    <link>{SITE_URL}/</link>\n"
        f"    <description>Writing by Nizar Mahmoud</description>\n{''.join(items)}  </channel>\n</rss>\n"
    )


def build(root, out):
    posts = load_posts(root / "posts")
    pages = sorted(p.name for p in root.iterdir() if p.is_file() and p.suffix == ".html")
    clash = {f"{p['slug']}.html" for p in posts} & set(pages)
    if clash:
        raise BuildError(f"a post and a page share a name: {', '.join(sorted(clash))}")
    template = string.Template((root / "templates" / "post.html").read_text(encoding="utf-8"))

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for item in root.iterdir():
        if item.is_file() and (item.suffix in STATIC_SUFFIXES or item.name in ("CNAME", "robots.txt")) and item.name != "index.html":
            shutil.copy2(item, out / item.name)
    if (root / "assets").is_dir():
        shutil.copytree(root / "assets", out / "assets")
    (out / "index.html").write_text(render_index((root / "index.html").read_text(encoding="utf-8"), posts), encoding="utf-8")
    for post in posts:
        (out / f"{post['slug']}.html").write_text(render_post(template, post), encoding="utf-8")
    (out / "sitemap.xml").write_text(sitemap(pages, posts), encoding="utf-8")
    (out / "feed.xml").write_text(feed(posts), encoding="utf-8")
    if not (root / "robots.txt").exists():
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    return posts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="_site", help="output folder (default: _site)")
    args = ap.parse_args()
    try:
        posts = build(ROOT, ROOT / args.out)
    except BuildError as e:
        sys.exit(f"build failed: {e}")
    print(f"built {len(posts)} post(s) into {args.out}/")


if __name__ == "__main__":
    main()
