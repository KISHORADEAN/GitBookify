"""Unit tests for the GitHub-to-EPUB converter (no network access)."""

import unittest
import zipfile
from io import BytesIO
from unittest.mock import patch

from app.converter import (
    ConversionError,
    build_epub,
    fetch_markdown,
    markdown_to_xhtml,
    parse_repo_url,
)


class ParseRepoUrlTests(unittest.TestCase):
    def test_accepts_common_forms(self):
        for url in (
            "https://github.com/owner/repo",
            "https://github.com/owner/repo/",
            "https://github.com/owner/repo.git",
            "http://www.github.com/owner/repo",
        ):
            self.assertEqual(parse_repo_url(url), ("owner", "repo"), url)

    def test_rejects_other_hosts_and_shapes(self):
        for url in (
            "",
            "not a url",
            "https://gitlab.com/owner/repo",
            "https://github.com/owner",
            "https://github.com/owner/repo/tree/main",
            "https://github.com/owner/repo with space",
        ):
            with self.assertRaises(ConversionError, msg=url):
                parse_repo_url(url)


class MarkdownTests(unittest.TestCase):
    def test_renders_headings_paragraphs_and_lists(self):
        html = markdown_to_xhtml("# Title\n\nSome text.\n\n- one\n- two\n\n1. first\n2. second")
        self.assertIn("<h1>Title</h1>", html)
        self.assertIn("<p>Some text.</p>", html)
        self.assertIn("<ul><li>one</li><li>two</li></ul>", html)
        self.assertIn("<ol><li>first</li><li>second</li></ol>", html)

    def test_escapes_html_and_keeps_code_fences(self):
        html = markdown_to_xhtml("Use <script>alert(1)</script>\n\n```python\nif a < b:\n    pass\n```")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn('<pre><code class="language-python">if a &lt; b:', html)

    def test_renders_inline_markup(self):
        html = markdown_to_xhtml("Run `npm test` and **read** the *docs*.")
        self.assertIn("<code>npm test</code>", html)
        self.assertIn("<strong>read</strong>", html)
        self.assertIn("<em>docs</em>", html)


class BuildEpubTests(unittest.TestCase):
    def test_builds_a_valid_container_and_chapters(self):
        epub = build_epub("Demo", [("README.md", "# Hello"), ("docs/guide.md", "## Guide")])

        with zipfile.ZipFile(BytesIO(epub)) as book:
            self.assertEqual(book.namelist()[0], "mimetype")
            self.assertEqual(book.getinfo("mimetype").compress_type, zipfile.ZIP_STORED)
            self.assertEqual(book.read("mimetype"), b"application/epub+zip")
            self.assertIn("OEBPS/content.opf", book.namelist())
            self.assertIn("OEBPS/nav.xhtml", book.namelist())

            container = book.read("META-INF/container.xml").decode()
            self.assertIn('full-path="OEBPS/content.opf"', container)

            package = book.read("OEBPS/content.opf").decode()
            self.assertIn("<dc:title>Demo</dc:title>", package)
            self.assertIn('href="chapter2.xhtml"', package)

            first_chapter = book.read("OEBPS/chapter1.xhtml").decode()
            self.assertIn("<h1>Hello</h1>", first_chapter)

            nav = book.read("OEBPS/nav.xhtml").decode()
            self.assertIn("README", nav)
            self.assertIn("guide", nav)

    def test_rejects_empty_book(self):
        with self.assertRaises(ConversionError):
            build_epub("Empty", [])


class FetchMarkdownTests(unittest.TestCase):
    def test_puts_readme_first_and_skips_non_markdown(self):
        metadata = b'{"default_branch": "main", "name": "demo"}'
        tree = (
            b'{"tree": ['
            b'{"path": "docs/guide.md", "type": "blob"},'
            b'{"path": "src/app.py", "type": "blob"},'
            b'{"path": "README.md", "type": "blob"}'
            b"]}"
        )

        def fake_request(url, accept):
            if url.endswith("/repos/owner/demo"):
                return metadata
            if "/git/trees/" in url:
                return tree
            return ("# " + url.rsplit("/", 1)[-1]).encode()

        with patch("app.converter._request", side_effect=fake_request):
            name, chapters = fetch_markdown("owner", "demo")

        self.assertEqual(name, "demo")
        self.assertEqual([path for path, _ in chapters], ["README.md", "docs/guide.md"])

    def test_reports_repositories_without_markdown(self):
        metadata = b'{"default_branch": "main", "name": "demo"}'
        tree = b'{"tree": [{"path": "main.py", "type": "blob"}]}'

        def fake_request(url, accept):
            return metadata if url.endswith("/repos/owner/demo") else tree

        with patch("app.converter._request", side_effect=fake_request):
            with self.assertRaises(ConversionError):
                fetch_markdown("owner", "demo")


if __name__ == "__main__":
    unittest.main()
