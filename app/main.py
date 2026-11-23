"""The FastAPI application for GitBookify."""

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool

from app.converter import ConversionError, convert_repository

# Keep the template folder next to the application code so it is easy to find.
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="GitBookify")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Show the homepage with an empty form."""
    return templates.TemplateResponse(request, "index.html", {"message": None})


@app.post("/convert", response_class=HTMLResponse)
async def convert(request: Request, repository_url: str = Form(...)):
    """Build an EPUB from the repository's Markdown files and send it as a download."""
    try:
        filename, epub = await run_in_threadpool(convert_repository, repository_url)
    except ConversionError as error:
        return templates.TemplateResponse(
            request,
            "index.html",
            {"message": str(error), "repository_url": repository_url},
            status_code=400,
        )
    return Response(
        content=epub,
        media_type="application/epub+zip",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )
