# GitBookify

GitBookify is an open-source web application that will convert GitHub repositories into EPUB books for Kindle and other e-readers.

This is the Day 1 project scaffold. It includes a homepage and a repository URL form. Conversion is intentionally not implemented yet; submitting the form shows a **Coming Soon** message.

## Project structure

```text
GitBookify/
├── app/
│   ├── main.py              # FastAPI routes and application setup
│   └── templates/
│       └── index.html       # Jinja2 homepage template
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

## Technology

- Python and FastAPI for the web server
- Jinja2 for HTML templates
- Tailwind CSS through its CDN for styling

## Next steps

Future work can validate GitHub URLs, fetch repository content, assemble chapters, and create EPUB files.
