# python/web/routes/system_monitor.py
"""System Monitor 画面 (PRIDEV-493)

管理者が稼働状態・直近エラー・アラート状態・最終更新時刻を確認する画面。
データ取得は PRIDEV-492 の `/api/system-monitor` を利用する。

画面の表示件数はユーザー判断事項のため、テンプレートへ直書きせず
本モジュールで外部化し、サーバ側を単一の正としてテンプレートへ注入する。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from python.utils.logger import get_logger

logger = get_logger("web", "system_monitor_ui")

router = APIRouter(tags=["system-monitor"])

templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

__all__ = [
    "SystemMonitorUISettings",
    "get_ui_settings",
    "reset_ui_settings_cache",
    "router",
]


# 以下 4 つはユーザー確認済みの確定値 (PRIDEV-493)。変更する場合はここを変更する。
DEFAULT_INITIAL_ERROR_COUNT = 20  # 初期表示 20 件
DEFAULT_ENABLE_LOAD_MORE = True  # 「さらに読み込む」方式で追加読み込みあり
DEFAULT_LOAD_MORE_COUNT = 20  # 1 回あたり 20 件
DEFAULT_MAX_ERROR_COUNT = 100  # 画面で保持・表示する最大 100 件


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning(f"{name} を整数として解釈できないため既定値 {default} を使用します")
        return default
    return value if value > 0 else default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class SystemMonitorUISettings:
    """画面の表示件数設定 (すべてユーザー確認済みの確定値)。"""

    initial_error_count: int
    enable_load_more: bool
    load_more_count: int
    max_error_count: int

    def to_client_config(self) -> Dict[str, Union[int, bool]]:
        return {
            "initialErrorCount": min(self.initial_error_count, self.max_error_count),
            "enableLoadMore": self.enable_load_more,
            "loadMoreCount": self.load_more_count,
            "maxErrorCount": self.max_error_count,
        }


_settings_cache: Optional[SystemMonitorUISettings] = None


def get_ui_settings() -> SystemMonitorUISettings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = SystemMonitorUISettings(
            initial_error_count=_env_int(
                "SYSTEM_MONITOR_INITIAL_ERROR_COUNT", DEFAULT_INITIAL_ERROR_COUNT
            ),
            enable_load_more=_env_bool(
                "SYSTEM_MONITOR_ENABLE_LOAD_MORE", DEFAULT_ENABLE_LOAD_MORE
            ),
            load_more_count=_env_int("SYSTEM_MONITOR_LOAD_MORE_COUNT", DEFAULT_LOAD_MORE_COUNT),
            max_error_count=_env_int("SYSTEM_MONITOR_MAX_ERROR_COUNT", DEFAULT_MAX_ERROR_COUNT),
        )
    return _settings_cache


def reset_ui_settings_cache() -> None:
    global _settings_cache
    _settings_cache = None


@router.get("/system-monitor", response_class=HTMLResponse)
async def system_monitor_page(request: Request) -> HTMLResponse:
    """System Monitor 画面。

    未認証アクセスは app.py の middleware がログインへリダイレクトするため、
    本ルートは認証済みリクエストのみを受け取る。
    """
    return templates.TemplateResponse(
        request,
        "system_monitor.html",
        {"monitor_config": get_ui_settings().to_client_config()},
    )
