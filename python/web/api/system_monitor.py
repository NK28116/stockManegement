# python/web/api/system_monitor.py
"""管理者専用 System Monitor API (PRIDEV-492)

PRIDEV-491 の SystemHealth を HTTP へ公開する。認証は PRIDEV-481 の
共通ガード (require_auth) を利用し、未認証は 401 を返す。

レスポンスへ内部例外・スタックトレース・認証情報を含めない。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from python.observability.errors import ObservabilityPermissionError
from python.observability.health import SystemHealthService
from python.observability.settings import ObservabilitySettings, get_observability_settings
from python.utils.logger import get_logger
from python.web.auth import require_auth

logger = get_logger("web", "system_monitor")

router = APIRouter(prefix="/api/system-monitor", tags=["system-monitor"])

__all__ = ["router", "get_health_service"]

_service: Optional[SystemHealthService] = None


def get_health_service() -> SystemHealthService:
    """SystemHealthService を返す (テストは dependency_overrides で差し替える)。"""
    global _service
    if _service is None:
        _service = SystemHealthService()
    return _service


def _settings() -> ObservabilitySettings:
    return get_observability_settings()


@router.get("", dependencies=[Depends(require_auth)])
async def read_system_monitor(
    request: Request,
    lookback_hours: Optional[int] = Query(
        None, ge=1, description="取得期間 (時間)。上限を超える指定は上限へ丸められる"
    ),
    limit: Optional[int] = Query(
        None, ge=1, description="取得件数。上限を超える指定は上限へ丸められる"
    ),
    service: SystemHealthService = Depends(get_health_service),
) -> Dict[str, Any]:
    """System Health を返す。

    - 未認証: 401 (共通ガード)
    - 権限不足: 403
    - Cloud API 障害: 200 + status=degraded (画面側で区別できるようにする)
    - 想定外の内部エラー: 503 (詳細はレスポンスへ含めない)
    """
    settings = _settings()
    try:
        health = service.collect(lookback_hours=lookback_hours, limit=limit)
    except ObservabilityPermissionError:
        # 集約サービスは通常 degraded で返すが、権限不足が伝播した場合は 403
        logger.warning("System Monitor: 権限不足のため 403 を返します")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="監視情報を参照する権限がありません",
        )
    except Exception as exc:  # noqa: BLE001 - 内部例外をレスポンスへ出さない
        logger.error(f"System Monitor: 想定外のエラー {type(exc).__name__}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="監視情報を取得できませんでした",
        )

    payload = health.to_dict()
    # 画面が表示件数を判断できるよう、適用された取得条件も返す
    payload["query"] = {
        "lookback_hours": settings.clamp_lookback_hours(lookback_hours),
        "limit": settings.clamp_limit(limit),
        "max_lookback_hours": settings.max_lookback_hours,
        "max_limit": settings.max_limit,
    }
    return payload
