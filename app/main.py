"""The FastAPI application for the GitBookify Day 1 scaffold."""

from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


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
    """Accept the form submission; EPUB conversion will be added in a later phase."""
    message = "Coming Soon: EPUB conversion is not available yet."
    return templates.TemplateResponse(
        request,
        "index.html",
        {"message": message, "repository_url": repository_url},
    )
