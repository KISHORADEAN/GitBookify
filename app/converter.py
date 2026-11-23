"""Convert a public GitHub repository's Markdown files into an EPUB 3 book."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from typing import List, Tuple
from urllib.parse import quote, urlparse

GITHUB_API = "https://api.github.com"
RAW_CONTENT = "https://raw.githubusercontent.com"
TIMEOUT_SECONDS = 20
MAX_FILES = 200
MAX_TOTAL_BYTES = 5 * 1024 * 1024
MARKDOWN_SUFFIXES = (".md", ".markdown")
USER_AGENT = "GitBookify/0.2 (+https://github.com/KISHORADEAN/GitBookify)"


class ConversionError(Exception):
    """A problem the visitor can fix, such as a bad URL or a private repository."""


def parse_repo_url(value: str) -> Tuple[str, str]:
    """Return (owner, repository) for a github.com repository URL."""
    parsed = urlparse((value or "").strip())
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ConversionError("Only github.com repository URLs are supported.")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 2:
        raise ConversionError("Use a repository URL such as https://github.com/owner/repository.")
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[: -len(".git")]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repository):
        raise ConversionError("The owner or repository name contains unsupported characters.")
    return owner, repository


def _request(url: str, accept: str) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise ConversionError("Repository not found. Make sure it is public and the URL is correct.") from error
        if error.code in (403, 429):
            raise ConversionError("GitHub rate limit reached. Please try again in a few minutes.") from error
        raise ConversionError("GitHub returned HTTP %s." % error.code) from error
    except urllib.error.URLError as error:
        raise ConversionError("Could not reach GitHub. Check the connection and try again.") from error


def _chapter_order(path: str) -> Tuple[int, int, str]:
    lowered = path.lower()
    filename = lowered.rsplit("/", 1)[-1]
    readme_first = 0 if filename.startswith("readme") else 1
    return (readme_first, lowered.count("/"), lowered)


def fetch_markdown(owner: str, repository: str) -> Tuple[str, List[Tuple[str, str]]]:
    """Return the repository name and its Markdown files, README first."""
    metadata = json.loads(_request("%s/repos/%s/%s" % (GITHUB_API, owner, repository), "application/vnd.github+json"))
    branch = metadata["default_branch"]
    tree = json.loads(
        _request(
            "%s/repos/%s/%s/git/trees/%s?recursive=1" % (GITHUB_API, owner, repository, quote(branch, safe="")),
            "application/vnd.github+json",
        )
    )

    # GitHub marks huge trees as truncated; we convert the files it did return.
    paths = [
        item["path"]
        for item in tree.get("tree", [])
        if item.get("type") == "blob" and item["path"].lower().endswith(MARKDOWN_SUFFIXES)
    ]
    if not paths:
        raise ConversionError("This repository has no Markdown files to turn into a book.")
    paths.sort(key=_chapter_order)
    paths = paths[:MAX_FILES]

    chapters = []
    total_bytes = 0
    for path in paths:
        url = "%s/%s/%s/%s/%s" % (RAW_CONTENT, owner, repository, quote(branch, safe=""), quote(path))
        content = _request(url, "text/plain")
        total_bytes += len(content)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ConversionError("This repository's Markdown is larger than the 5 MB limit.")
        chapters.append((path, content.decode("utf-8", "replace")))
    return metadata.get("name", repository), chapters


_SAFE_LINK = re.compile(r"^(https?://|mailto:|#|/|\.{0,2}/)")


def _link(match: re.Match) -> str:
    label, target = match.group(1), match.group(2)
    if not _SAFE_LINK.match(target):
        return label
    return '<a href="%s">%s</a>' % (target, label)


def _inline(text: str) -> str:
    rendered = escape(text)
    rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
    # Images are not embedded in the EPUB, so keep their alt text instead of
    # leaving a stray "!" and a link to a file that is not in the book.
    rendered = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)", r"\1", rendered)
    rendered = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", _link, rendered)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", rendered)
    return rendered


_BLOCK_START = re.compile(r"^(#{1,6}\s|```|\s*[-*+]\s|\s*\d+[.)]\s)")


def markdown_to_xhtml(markdown: str) -> str:
    """Render the Markdown subset that matters for documentation chapters."""
    lines = markdown.splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        line = lines[index]

        if line.strip().startswith("```"):
            language = line.strip()[3:].strip()
            index += 1
            code = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            index += 1
            attribute = ' class="language-%s"' % escape(language) if language else ""
            blocks.append("<pre><code%s>%s</code></pre>" % (attribute, escape("\n".join(code))))
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            blocks.append("<h%d>%s</h%d>" % (level, _inline(heading.group(2)), level))
            index += 1
            continue

        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while index < len(lines) and re.match(r"^\s*[-*+]\s+", lines[index]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[index]))
                index += 1
            blocks.append("<ul>%s</ul>" % "".join("<li>%s</li>" % _inline(item) for item in items))
            continue

        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            while index < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[index]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[index]))
                index += 1
            blocks.append("<ol>%s</ol>" % "".join("<li>%s</li>" % _inline(item) for item in items))
            continue

        if not line.strip():
            index += 1
            continue

        paragraph = []
        while index < len(lines) and lines[index].strip() and not _BLOCK_START.match(lines[index]):
            paragraph.append(lines[index].strip())
            index += 1
        blocks.append("<p>%s</p>" % _inline(" ".join(paragraph)))

    return "\n".join(blocks)


_XHTML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    "<!DOCTYPE html>\n"
    '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">\n'
    "<head><title>%s</title></head>\n"
    "<body>\n%s\n</body>\n</html>\n"
)

_CONTAINER = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _chapter_label(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    for suffix in MARKDOWN_SUFFIXES:
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    return name.replace("-", " ").replace("_", " ").strip() or path


def build_epub(title: str, chapters: List[Tuple[str, str]]) -> bytes:
    """Build a minimal, valid EPUB 3 file from (path, markdown) chapters."""
    if not chapters:
        raise ConversionError("There are no chapters to put in the book.")

    identifier = "urn:uuid:%s" % uuid.uuid4()
    modified = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>']
    spine = []
    nav_items = []

    for position, (path, markdown) in enumerate(chapters, start=1):
        filename = "chapter%d.xhtml" % position
        manifest.append('<item id="chapter%d" href="%s" media-type="application/xhtml+xml"/>' % (position, filename))
        spine.append('<itemref idref="chapter%d"/>' % position)
        nav_items.append('<li><a href="%s">%s</a></li>' % (filename, escape(_chapter_label(path))))

    package = """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">%s</dc:identifier>
    <dc:title>%s</dc:title>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">%s</meta>
  </metadata>
  <manifest>
    %s
  </manifest>
  <spine>
    %s
  </spine>
</package>
""" % (
        identifier,
        escape(title),
        modified,
        "\n    ".join(manifest),
        "\n    ".join(spine),
    )

    nav = _XHTML % (
        "Contents",
        '<nav epub:type="toc"><h1>Contents</h1><ol>%s</ol></nav>' % "".join(nav_items),
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as book:
        book.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        book.writestr("META-INF/container.xml", _CONTAINER)
        book.writestr("OEBPS/content.opf", package)
        book.writestr("OEBPS/nav.xhtml", nav)
        for position, (path, markdown) in enumerate(chapters, start=1):
            body = markdown_to_xhtml(markdown)
            book.writestr("OEBPS/chapter%d.xhtml" % position, _XHTML % (escape(_chapter_label(path)), body))
    return buffer.getvalue()


def convert_repository(url: str) -> Tuple[str, bytes]:
    """Turn a repository URL into (download filename, EPUB bytes)."""
    owner, repository = parse_repo_url(url)
    name, chapters = fetch_markdown(owner, repository)
    return "%s.epub" % repository, build_epub(name, chapters)
