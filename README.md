# GitBookify

GitBookify is an open-source web application that converts GitHub repositories into EPUB books for Kindle and other e-readers.

Paste a public repository URL and GitBookify downloads the repository's Markdown documentation, turns it into chapters, and returns a ready-to-read EPUB 3 file.

## How it works

1. The homepage form accepts a `https://github.com/owner/repository` URL.
2. The GitHub API resolves the repository's default branch and file tree.
3. Every `.md` / `.markdown` file is fetched, with `README` files first.
4. Each file becomes a chapter, and the EPUB is built in memory and sent as a download.

Nothing is stored on the server: the book is generated per request and returned directly to the browser.

## Project structure

```text
GitBookify/
├── app/
│   ├── main.py              # FastAPI routes and application setup
│   ├── converter.py         # GitHub fetching, Markdown rendering, EPUB building
│   └── templates/
│       └── index.html       # Jinja2 homepage template
├── tests/
│   └── test_converter.py    # Unit tests for URL parsing, rendering and EPUB structure
├── .gitignore               # Files Git should ignore
├── requirements.txt         # Python dependencies
└── README.md                # Project instructions
```

## Run the project

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the development server:

   ```bash
   uvicorn app.main:app --reload
   ```

4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Tests

```bash
python -m unittest discover -s tests
```

The tests use only the standard library and do not touch the network.

## Limits

- Only **public** repositories on `github.com` are supported.
- Only Markdown files (`.md`, `.markdown`) become chapters; images and code files are skipped.
- At most 200 files and 5 MB of Markdown per book.
- GitHub's unauthenticated API allows 60 requests per hour per IP; large repositories can hit that limit.

## Technology

- Python and FastAPI for the web server
- Jinja2 for HTML templates
- Standard library `zipfile` for EPUB assembly and `urllib` for GitHub requests
- Tailwind CSS through its CDN for styling

## Next steps

- Support private repositories through a GitHub token.
- Include images and syntax-highlighted source files as chapters.
- Let visitors choose which folders become chapters.
- Cache generated EPUB files for repeat downloads.
