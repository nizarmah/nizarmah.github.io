# nizarmah.com

This is my personal website — built by snippets from cool people on the internet.

## Writing

1. Add `posts/<word>.md`. The name is one lowercase word; it becomes `nizarmah.com/<word>.html`.
2. Start it with:

   ```
   ---
   title: Reboot
   date: 2026-09-13
   description: One line for search results and link previews.
   ---
   ```

   Add `draft: true` to keep a post off the site, and `updated: YYYY-MM-DD` when you change one.
3. Write in Markdown. One sentence per line is fine; lines in a paragraph join up.
4. Push to `main`. GitHub Actions builds the site and publishes it. The post appears in the list on the home page, in `sitemap.xml` and in `feed.xml`.

Preview locally:

```
pip install -r requirements.txt
python3 build.py
python3 -m http.server -d _site
```

The other pages (`index.html`, `about.html`, `quotes.html`) are plain HTML and copied as they are. The post list on the home page goes between `<!-- writings -->` and `<!-- /writings -->`.
