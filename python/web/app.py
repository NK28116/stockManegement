from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

from python.web.routes import rules, charts

app = FastAPI(title="Stock Management UI")

# Mount API routes
app.include_router(rules.router)
app.include_router(charts.router)

# Setup templates
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Serve static files (if we had any CSS/JS files, standard pattern)
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Run instruction: uvicorn python.web.app:app --reload
