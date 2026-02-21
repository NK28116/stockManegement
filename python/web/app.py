import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from python.utils.logger import get_logger
from python.web.api import rules, signals, simulate
from python.web.routes import actions, analytics, charts

logger = get_logger("web", "app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite モードの場合は起動時にもテーブル存在を保証する
    if os.getenv("DB_TYPE", "").lower() == "sqlite":
        from python.db.database import init_db
        init_db()
        logger.info("lifespan: SQLite テーブル初期化完了")
    yield


app = FastAPI(title="Stock Management UI", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = exc.errors()
    logger.error(f"Validation Error at {request.url}: {error_details}")
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder({"detail": error_details}),
    )


# Mount API routes
app.include_router(rules.router)
app.include_router(signals.router)
app.include_router(charts.router)
app.include_router(simulate.router)
app.include_router(actions.router)
app.include_router(analytics.router)
# Setup templates
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Serve static files (if we had any CSS/JS files, standard pattern)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# Run instruction: uvicorn python.web.app:app --reload
