# python/web/startup.py
"""初回起動待ちの計測と、起動処理のバックグラウンド化 (PRIDEV-485)

初回アクセス時にバックエンドの起動処理 (DB 初期化 / CSV 同期) が完了するまで
リクエストが返らず、画面が長時間停止して見える問題への対応。

    * 起動処理をリクエスト経路から分離し、バックグラウンドで実行する
    * 起動所要時間を計測してログとステータス API から比較できるようにする
    * フロントの loading 表示遅延 / timeout はここで一元管理し、
      テンプレートへ渡す (値のハードコードを避ける)
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Optional

from python.utils.logger import get_logger

logger = get_logger("web", "startup")

__all__ = [
    "StartupMetrics",
    "StartupSettings",
    "get_startup_settings",
    "reset_startup_settings_cache",
    "metrics",
    "run_warmup",
]


# TODO(PRIDEV-485): 以下 3 つはユーザー確認待ちの暫定値。
# 確定後はここ (または同名の環境変数) の 1 箇所を変更すれば全体へ反映される。
DEFAULT_TARGET_SECONDS = 10.0  # 暫定: 起動完了の目標 10 秒以内
DEFAULT_LOADING_DELAY_SECONDS = 1.0  # 暫定: 1 秒を超えたら loading 表示を出す
DEFAULT_TIMEOUT_SECONDS = 30.0  # 暫定: 30 秒で timeout とみなし retry 導線を出す


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = float(raw)
    except ValueError:
        logger.warning(f"{name} を数値として解釈できないため既定値 {default} を使用します")
        return default
    if value < 0:
        logger.warning(f"{name} が負の値のため既定値 {default} を使用します")
        return default
    return value


@dataclass(frozen=True)
class StartupSettings:
    """起動待ち UX の外部化された設定値 (単位は秒)。"""

    target_seconds: float
    loading_delay_seconds: float
    timeout_seconds: float

    def to_client_config(self) -> Dict[str, int]:
        """フロントエンドへ渡す設定 (ミリ秒)。"""
        return {
            "targetMs": int(self.target_seconds * 1000),
            "loadingDelayMs": int(self.loading_delay_seconds * 1000),
            "timeoutMs": int(self.timeout_seconds * 1000),
        }


_settings_cache: Optional[StartupSettings] = None


def get_startup_settings() -> StartupSettings:
    global _settings_cache
    if _settings_cache is None:
        _settings_cache = StartupSettings(
            target_seconds=_env_float("STARTUP_TARGET_SECONDS", DEFAULT_TARGET_SECONDS),
            loading_delay_seconds=_env_float(
                "STARTUP_LOADING_DELAY_SECONDS", DEFAULT_LOADING_DELAY_SECONDS
            ),
            timeout_seconds=_env_float("STARTUP_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        )
    return _settings_cache


def reset_startup_settings_cache() -> None:
    """環境変数を差し替えたテストからキャッシュを破棄する。"""
    global _settings_cache
    _settings_cache = None


@dataclass
class StartupMetrics:
    """起動所要時間の計測結果。前後比較ができるよう秒で保持する。"""

    started_at: float = field(default_factory=time.monotonic)
    ready_at: Optional[float] = None
    failed: bool = False
    detail: str = ""

    @property
    def ready(self) -> bool:
        return self.ready_at is not None

    @property
    def elapsed_seconds(self) -> float:
        """起動開始からの経過秒 (完了後は所要時間で固定)。"""
        end = self.ready_at if self.ready_at is not None else time.monotonic()
        return round(end - self.started_at, 3)

    def reset(self) -> None:
        self.started_at = time.monotonic()
        self.ready_at = None
        self.failed = False
        self.detail = ""

    def mark_ready(self, detail: str = "") -> None:
        self.ready_at = time.monotonic()
        self.detail = detail

    def mark_failed(self, detail: str) -> None:
        # 失敗しても「起動待ち」を続けさせない。degraded として ready にする。
        self.ready_at = time.monotonic()
        self.failed = True
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        settings = get_startup_settings()
        payload = {
            "ready": self.ready,
            "degraded": self.failed,
            "elapsed_seconds": self.elapsed_seconds,
            "target_seconds": settings.target_seconds,
            "within_target": self.ready and self.elapsed_seconds <= settings.target_seconds,
        }
        if self.detail:
            payload["detail"] = self.detail
        return payload


# アプリ全体で共有する計測インスタンス
metrics = StartupMetrics()


def run_warmup(warmup: Callable[[], None]) -> StartupMetrics:
    """起動処理を実行し、所要時間を計測・記録する。

    例外は握りつぶして degraded として記録する。起動処理の失敗で
    アプリ全体が起動不能になる (= 画面が永久に待たされる) のを避けるため。
    """
    metrics.reset()
    try:
        warmup()
    except Exception as exc:  # noqa: BLE001 - 起動失敗でプロセスを落とさない
        metrics.mark_failed(f"{type(exc).__name__}: {exc}")
        logger.warning(
            f"起動処理に失敗しました (degraded として続行): {exc} "
            f"[elapsed={metrics.elapsed_seconds}s]"
        )
        return metrics

    metrics.mark_ready()
    settings = get_startup_settings()
    # 起動待ち時間の比較に使う測定結果を残す
    if metrics.elapsed_seconds > settings.target_seconds:
        logger.warning(
            f"起動完了 (目標超過): elapsed={metrics.elapsed_seconds}s "
            f"target={settings.target_seconds}s"
        )
    else:
        logger.info(
            f"起動完了: elapsed={metrics.elapsed_seconds}s target={settings.target_seconds}s"
        )
    return metrics


def startup_status() -> Dict[str, Any]:
    """起動状態をフロント / 運用から参照できる形で返す。"""
    return metrics.to_dict()


def settings_as_dict() -> Dict[str, Any]:
    return asdict(get_startup_settings())
