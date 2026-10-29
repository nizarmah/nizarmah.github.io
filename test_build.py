import pathlib
import tempfile
import unittest

import build


class BuildTest(unittest.TestCase):
    def site(self, posts, index='<html>\n  <head>\n  </head>\n  <body>\n<!-- writings -->\n<!-- /writings -->\n  </body>\n</html>\n'):
        tmp = pathlib.Path(tempfile.mkdtemp())
        (tmp / "posts").mkdir()
        (tmp / "templates").mkdir()
        (tmp / "templates" / "post.html").write_text((build.ROOT / "templates" / "post.html").read_text())
        (tmp / "index.html").write_text(index)
        for name, text in posts.items():
            (tmp / "posts" / name).write_text(text)
        return tmp

    def test_post_becomes_word_html_and_is_listed(self):
        tmp = self.site({"grading.md": "---\ntitle: Grading\ndate: 2026-10-30\n---\n\nHello [x](https://example.com).\n"})
        posts = build.build(tmp, tmp / "_site")
        self.assertEqual([p["slug"] for p in posts], ["grading"])
        page = (tmp / "_site" / "grading.html").read_text()
        self.assertIn("Friday, October 30, 2026", page)
        self.assertIn('href="https://example.com" target="_blank" rel="noopener"', page)
        self.assertIn('href="./grading.html"', (tmp / "_site" / "index.html").read_text())
        self.assertIn("https://nizarmah.com/grading.html", (tmp / "_site" / "sitemap.xml").read_text())
        self.assertIn("<title>Grading</title>", (tmp / "_site" / "feed.xml").read_text())

    def test_post_names_are_one_word(self):
        tmp = self.site({"two-words.md": "---\ntitle: X\ndate: 2026-10-30\n---\nx\n"})
        with self.assertRaises(build.BuildError):
            build.build(tmp, tmp / "_site")

    def test_drafts_are_skipped(self):
        tmp = self.site({"later.md": "---\ntitle: Later\ndate: 2026-10-30\ndraft: true\n---\nx\n"})
        self.assertEqual(build.build(tmp, tmp / "_site"), [])
        self.assertFalse((tmp / "_site" / "later.html").exists())

    def test_bad_date_fails(self):
        tmp = self.site({"x.md": "---\ntitle: X\ndate: Oct 30\n---\nx\n"})
        with self.assertRaises(build.BuildError):
            build.build(tmp, tmp / "_site")

    def test_index_needs_markers(self):
        tmp = self.site({}, index="<html><head></head><body></body></html>")
        with self.assertRaises(build.BuildError):
            build.build(tmp, tmp / "_site")


if __name__ == "__main__":
    unittest.main()
