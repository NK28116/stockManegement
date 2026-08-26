import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from python.utils.logger import get_logger
from python.web import startup
from python.web.api import rules, signals, simulate, watchlist
from python.web.routes import actions, analytics, charts

logger = get_logger("web", "app")


def _warmup() -> None:
    """DB 初期化 / CSV 同期。起動経路から分離して呼ばれる (PRIDEV-485)。"""
    db_type = os.getenv("DB_TYPE", "postgresql").lower()
    if db_type == "sqlite":
        # SQLite モードの場合は起動時にもテーブル存在を保証する
        from python.db.database import init_db

        init_db()
        logger.info("warmup: SQLite テーブル初期化完了")
    else:
        # PostgreSQL モードの場合は CSV → portfolio テーブルへ自動同期する
        from python.db.database import sync_csv_to_portfolio

        sync_csv_to_portfolio()
        logger.info("warmup: portfolio テーブルを CSV から同期完了")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動処理をイベントループの外へ逃がし、最初のリクエストをブロックしない。
    # 所要時間は startup.metrics へ記録され、/api/startup/status から参照できる。
    startup.metrics.reset()
    warmup_task = asyncio.create_task(asyncio.to_thread(startup.run_warmup, _warmup))
    try:
        yield
    finally:
        if not warmup_task.done():
            warmup_task.cancel()


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
app.include_router(watchlist.router)
# Setup templates
templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Serve static files (if we had any CSS/JS files, standard pattern)
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/api/startup/status")
async def startup_status():
    """起動待ちの計測結果を返す (PRIDEV-485)。

    バックエンドが応答できている時点で ready だが、warmup 完了までは
    ready=False となり、フロントは起動待ちであることを表示できる。
    """
    return startup.startup_status()


@app.get("/")
async def read_root(request: Request):
    # 起動待ちの表示遅延 / timeout はサーバ側の設定値を単一の正とする
    return templates.TemplateResponse(
        request,
        "index.html",
        {"startup_config": startup.get_startup_settings().to_client_config()},
    )


# Run instruction: uvicorn python.web.app:app --reload
