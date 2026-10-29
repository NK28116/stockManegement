"""新しく登録した銘柄のチャートを、その場で作る (ダッシュボードの「Update Stock All Data」)

全銘柄のチャートは GCE の日次バッチが作るが、それを待たずに登録した銘柄のチャートを見たい。
登録した銘柄だけを対象に、

    1. チャート (Signals / MACD・ボリンジャーバンド) を作る
    2. GCS へアップロードする (本番の一覧は GCS のチャートを表示する)
    3. 作り終えたらシグナルを更新する (Check Signals と同じ分析)

をバックグラウンドで順に行う。チャート作成 (matplotlib) は同時に動かさず、
実行中に追加された銘柄は、今の作成が終わってからまとめて作る。

環境変数 DISABLE_NEW_STOCK_CHARTS=1 で無効にできる (日次バッチを待つ)。
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Iterable, List, Optional, Set

from python.trading.buy_and_sell_stock import code_key
from python.utils.gcs_client import gcs

logger = logging.getLogger(__name__)

# チャートの期間。一覧が表示する期間 (python/web/routes/charts.py の LOCAL_CHART_PERIOD) と同じ
CHART_PERIOD = "1mo"
# 作ったチャートのアップロード先 (ローカルの出力ディレクトリ名 → GCS のプレフィックス)
_UPLOAD_TARGETS = (("chartImg", "charts/signals"), ("plots", "charts/indicators"))


def is_enabled() -> bool:
    return os.getenv("DISABLE_NEW_STOCK_CHARTS", "").lower() not in ("1", "true", "yes")


class ChartJobs:
    """チャート作成の待ち行列と状態 (プロセス内で 1 つ)。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queue: Set[str] = set()
        self._generating: Set[str] = set()
        self._failed: Set[str] = set()
        self._running = False

    # --- 状態 (GET /api/actions/status で画面へ返す) -----------------------------

    def generating(self) -> List[str]:
        with self._lock:
            return sorted(self._queue | self._generating)

    def failed(self) -> List[str]:
        with self._lock:
            return sorted(self._failed)

    # --- 実行 -------------------------------------------------------------------

    def enqueue(self, codes: Iterable[str]) -> List[str]:
        """作成待ちに積み、積んだ銘柄のキーを返す。続けて run() を呼ぶ。"""
        keys = {code_key(code) for code in codes if str(code).strip()}
        with self._lock:
            self._queue |= keys
            self._failed -= keys
        return sorted(keys)

    def run(self, after: Optional[Callable[[List[str]], None]] = None) -> None:
        """待ち行列が空になるまでチャートを作る (バックグラウンドのスレッドで呼ぶ)。

        Args:
            after: 作り終えたあとに 1 回だけ呼ぶ処理 (シグナルの更新)。
                チャートを作れた銘柄のキーを渡す。
        """
        with self._lock:
            if self._running:
                return  # 実行中の処理が、追加された分もまとめて作る
            self._running = True

        created_all: Set[str] = set()
        while True:
            with self._lock:
                batch = set(self._queue)
                self._queue.clear()
                if not batch:
                    # 待ち行列の確認と終了を同じロックの中で行い、取りこぼさない
                    self._running = False
                    break
                self._generating |= batch
            try:
                created = generate_and_upload(sorted(batch))
            except Exception as e:  # チャート作成の失敗で Web アプリを止めない
                logger.error(
                    f"チャート作成に失敗しました {sorted(batch)}: {e}", exc_info=True
                )
                created = set()
            with self._lock:
                self._generating -= batch
                self._failed |= batch - created
            created_all |= created

        if created_all and after is not None:
            try:
                after(sorted(created_all))
            except Exception as e:
                logger.error(
                    f"チャート作成後のシグナル更新に失敗しました: {e}", exc_info=True
                )


def generate_and_upload(keys: List[str]) -> Set[str]:
    """指定した銘柄のチャートを作り、GCS を使っていればアップロードする。

    Returns:
        チャートを作れた銘柄のキー。
    """
    from python.visualization.stock_chart_visualizer import StockChartVisualizer

    logger.info(f"新しく登録した銘柄のチャートを作成します: {keys}")
    visualizer = StockChartVisualizer(period=CHART_PERIOD, only_codes=keys)
    portfolio_file = "my_stock.csv" if gcs.use_gcs else "data/my_stock_local.csv"
    visualizer.visualize_all_stocks(portfolio_file)

    created: Set[str] = set()
    for local_dir_name, prefix in _UPLOAD_TARGETS:
        local_dir = (
            visualizer.data_dir
            if local_dir_name == "chartImg"
            else visualizer.plot_image_dir
        )
        if not os.path.isdir(local_dir):
            continue
        for name in os.listdir(local_dir):
            key = code_key(name.split("_")[0])
            if not name.lower().endswith(".png") or key not in keys:
                continue
            created.add(key)
            if gcs.use_gcs:
                blob = gcs.bucket.blob(f"{prefix}/{name}")
                blob.upload_from_filename(
                    os.path.join(local_dir, name), content_type="image/png"
                )
    if gcs.use_gcs and created:
        _upload_latest_indicators()
    logger.info(
        f"チャートを作成しました: {sorted(created)} (作れなかった銘柄: {sorted(set(keys) - created)})"
    )
    return created


def _upload_latest_indicators() -> None:
    """最新指標値 (画像のポップアップに出す値) を GCS の値に重ねてアップロードする。"""
    import json

    from python.config import config

    local_path = os.path.join(config.data_dir, "latest_indicators.json")
    if not os.path.exists(local_path):
        return
    with open(local_path, encoding="utf-8") as f:
        local_values = json.load(f)
    current = gcs.get_file_content("latest_indicators.json")
    merged = {
        **(json.loads(current.decode("utf-8")) if current else {}),
        **local_values,
    }
    gcs.bucket.blob("latest_indicators.json").upload_from_string(
        json.dumps(merged, ensure_ascii=False, indent=2),
        content_type="application/json",
    )


chart_jobs = ChartJobs()
