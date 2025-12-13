import os
import threading
import time
from datetime import datetime, timedelta

import pandas as pd  # detect_sharp_declineで必要
import psutil
import yfinance as yf

from python.analysis.portfolio_analyzer import PortfolioAnalyzer  # ポートフォリオ分析用
from python.config import config
from python.utils.alert import send_alert
from python.utils.indicators import detect_sharp_decline  # 急落アラート用
from python.utils.logger import get_logger
from python.utils.monitor import api_call_count, get_db_size

logger = get_logger("report", category="report")

# PortfolioAnalyzerのインスタンスを生成
analyzer = PortfolioAnalyzer()

__all__ = [
    "send_daily_morning_report",
    "send_daily_evening_report",
    "send_weekly_report",
    "send_monthly_report",
    "send_startup_report",
]

MONITOR_INTERVAL = 60  # 秒


def log_system_resources(interval=MONITOR_INTERVAL):
    """CPU/メモリ/DBサイズ/APIコール数を定期ログ"""
    process = psutil.Process(os.getpid())
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_usage = process.memory_info().rss / (1024 * 1024)  # MB
        db_size = get_db_size()
        logger.info(
            "リソース使用状況 | CPU: %.1f%% | MEM: %.1fMB | DB: %.2fMB | API Calls: %d",
            cpu_percent,
            memory_usage,
            db_size,
            api_call_count,
        )
        time.sleep(interval)


# --- レポート送信と並行してモニタリングを開始 ---
def start_monitoring():
    """別スレッドでリソースモニタリングを開始"""
    thread = threading.Thread(target=log_system_resources, daemon=True)
    thread.start()


def _get_latest_report_file(report_type: str) -> str | None:
    """指定された種類の最新レポートファイルパスを取得する"""
    # レポートタイプに応じてサブディレクトリを決定
    if report_type == "summary":
        report_dir = config.root_dir / "data" / "report" / "daily" / report_type
    elif report_type == "detailed":
        report_dir = config.root_dir / "data" / "report" / "daily" / report_type
    elif report_type == "weekly_summary":  # 週次サマリーレポート用
        report_dir = config.root_dir / "data" / "report" / "weekly" / "summary"
    elif report_type == "weekly_detailed":  # 週次詳細レポート用
        report_dir = config.root_dir / "data" / "report" / "weekly" / "detailed"
    elif report_type == "monthly_detailed":  # 月次詳細レポート用
        report_dir = config.root_dir / "data" / "report" / "monthly" / "detailed"
    elif report_type == "trading_rules":  # トレーディングルール見直しレポート用
        report_dir = config.root_dir / "data" / "report" / "monthly" / "trading_rules"
    else:
        report_dir = config.root_dir / "data" / "report" / report_type

    if not report_dir.exists():
        os.makedirs(report_dir, exist_ok=True)  # ディレクトリが存在しない場合は作成
        return None

    # ファイル名パターン: summary_report_YYYYMMDD_HHMMSS.txt または detailed_report_YYYYMMDD_HHMMSS.txt
    files = sorted(report_dir.glob(f"{report_type}_report_*.txt"), reverse=True)
    return str(files[0]) if files else None


# TODO:以下のチェックリストを作成
# 市場動向を効率よく把握・解釈できるように、日次チェックリスト（テンプレート）。

# 市場動向チェックリスト
# 1. 全体の方向感
# 	•日経平均：📈 / 📉 （前日比 ○○円、△%）
# 	•TOPIX：📈 / 📉 （前日比 ○○ポイント、△%）
# 	•（参考）米国市場（ダウ / S&P500 / NASDAQ の動き）
# 市場全体が上げているのか / 一部だけ動いているのかを確認

# 2. 売買エネルギー
# 	•	出来高（東証プライム）：○○億株（前日比 +△% / -△%）
# 	•	売買代金：○兆円（活況 or 薄商い）
# 出来高を伴った上昇/下落かどうかで本気度を判断

# 3. セクター別動向
# 	•	強い業種：例）半導体、銀行、不動産
# 	•	弱い業種：例）輸送用機器、食品
# テーマ性のある動きが出ているかチェック

# 4. 指数間比較
# 	•	日経平均 vs TOPIX
# 	•	日経だけ↑ → 一部の大型株主導（ファストリ、ソフトバンクGなど）
# 	•	TOPIXも↑ → 市場全体に買いが広がっている
# 	•	NASDAQ vs S&P500
# 	•	NASDAQ↑↑ → ハイテク中心
# 	•	S&P500安定 → 米国市場全体は堅調

# 5. テクニカル視点（日足ベース）
# 	•	25日移動平均線より上 / 下？
# 	•	RSI（相対力指数）：買われすぎ（70超） / 売られすぎ（30割れ）
# 	•	急落アラート：前日比 -3%以上の下げ銘柄が多いか

# 6. 注目ニュース
# 	•	国内ニュース（金融政策、為替、企業決算）
# 	•	海外ニュース（米国金利、FRB発言、地政学リスク、中国経済）
# 数字の動きとニュースをセットで確認することが大事

# #7. まとめコメント
# 	•	「市場全体が堅調/軟調」
# 	•	「一部の大型株主導 / 広範囲に買いが広がった」
# 	•	「米国市場の影響を強く受けた / 国内材料主導」


def _get_market_news_for_period(period: str) -> str:
    # 各指数データ取得
    nikkei = yf.Ticker("^N225").history(period=period)
    topix = yf.Ticker("998405.T").history(period=period)
    nasdaq = yf.Ticker("^IXIC").history(period=period)
    sp500 = yf.Ticker("^GSPC").history(period=period)

    def summarize_index(df, name):
        if df.empty:
            return f"{name}のデータは取得できませんでした。"
        start = df["Close"].iloc[0]
        end = df["Close"].iloc[-1]
        change = end - start
        pct_change = (change / start) * 100
        direction = "上昇" if change > 0 else "下落" if change < 0 else "横ばい"
        return f"{name}は{direction}しました（前日比 {change:.2f}円 / {pct_change:.2f}%）。"

    # 各指数の要約作成
    summary = [
        summarize_index(nikkei, "日経平均"),
        summarize_index(topix, "TOPIX"),
        summarize_index(nasdaq, "NASDAQ"),
        summarize_index(sp500, "S&P500"),
    ]

    # 市場全体のコメントをまとめる
    overall_comment = f"{period}の市場の動きです:\n" + "\n".join(summary)
    return overall_comment


# 平日の09:00(市場開場前)に前日のレポートを生成し、Slackに送信する
def send_daily_morning_report(is_test_mode: bool = False):
    """前日の日次レポートをSlackに送信する"""
    logger.info("前日の日次レポートを生成し、Slackに送信します。")

    # 前日の日付を取得
    yesterday = datetime.now() - timedelta(days=1)
    report_date = yesterday.strftime("%Y-%m-%d")
    message = f"【日次レポート】 {report_date} (前日)\n\n"

    # every_stock_buy_and_sell_timing.py が生成する最新のサマリーレポートを読み込む
    # ここでは最新のレポートファイルを取得し、その内容から前日の情報を抽出することを想定
    # _get_latest_report_file関数が日付フィルタリングをサポートしていないため、
    # レポート内容から日付を判断する必要がある。
    # もし_get_latest_report_fileが特定日付のレポートを取得できるなら、そのように変更する。
    summary_report_path = _get_latest_report_file("summary")
    if summary_report_path and os.path.exists(summary_report_path):
        with open(summary_report_path, "r", encoding="utf-8") as f:
            summary_content = f.read()
            # レポート内容に日付が含まれているか確認し、前日の情報であることを確認
            if report_date in summary_content:
                # 「前日の各銘柄ステータス」セクションを抽出
                status_section_start = summary_content.find(
                    "【前日の各銘柄ステータス】"
                )
                if status_section_start != -1:
                    status_section = summary_content[status_section_start:]
                    # 次のセクションの開始（例: 空行や別の見出し）までを抽出
                    next_section_start = status_section.find(
                        "\n\n", len("【前日の各銘柄ステータス】")
                    )
                    if next_section_start != -1:
                        status_section = status_section[:next_section_start]
                    message += status_section.strip() + "\n\n"
                else:
                    message += "前日の銘柄ステータスが見つかりませんでした。\n\n"
            else:
                message += (
                    f"日付 {report_date} のサマリーレポートが見つかりませんでした。\n\n"
                )
    else:
        message += (
            "全銘柄売買タイミング分析サマリーレポートが見つかりませんでした。\n\n"
        )

    # 日足での急落アラート
    # ポートフォリオ内の全銘柄の株価データを取得し、急落を検出
    portfolio_df = analyzer.get_portfolio()
    sharp_declines_messages = []
    for _, holding in portfolio_df.iterrows():
        ticker = holding["code"]
        price_df = analyzer.fetch_stock_data(ticker, period="5d")  # 過去数日間のデータ
        if not price_df.empty:
            # インデックスを日付型に変換
            price_df.index = pd.to_datetime(price_df.index)
            # 前日のデータのみを対象
            yesterday_prices = price_df[price_df.index.date == yesterday.date()][
                "Close"
            ]
            if not yesterday_prices.empty:
                # detect_sharp_declineはSeriesを期待
                sharp_declines = detect_sharp_decline(
                    yesterday_prices, decline_threshold=0.05
                )
                if not sharp_declines.empty:
                    for _, row in sharp_declines.iterrows():
                        sharp_declines_messages.append(
                            f"・{holding['name']} ({ticker}): {row['DeclineRate']} の急落 ({row['Date']})"
                        )

    if sharp_declines_messages:
        message += (
            "【前日の日足急落アラート】\n" + "\n".join(sharp_declines_messages) + "\n\n"
        )
    else:
        message += "【前日の日足急落アラート】\n該当する銘柄はありませんでした。\n\n"
    send_alert(message, level="INFO")
    logger.info("前日の日次レポートのSlack送信が完了しました。")


# 平日の17:00にその日のレポートを生成し、Slackに送信する
def send_daily_evening_report(is_test_mode: bool = False):
    """その日の日次レポートをSlackに送信する"""
    logger.info("その日の日次レポートを生成し、Slackに送信します。")

    # 今日の日付を取得
    today = datetime.now()
    report_date = today.strftime("%Y-%m-%d")
    message = f"【日次レポート】 {report_date} (本日)\n\n"

    # every_stock_buy_and_sell_timing.py が生成する最新のサマリーレポートを読み込む
    summary_report_path = _get_latest_report_file("summary")
    if summary_report_path and os.path.exists(summary_report_path):
        with open(summary_report_path, "r", encoding="utf-8") as f:
            summary_content = f.read()
            # レポート内容に日付が含まれているか確認し、その日の情報であることを確認
            if report_date in summary_content:
                # 「前日の各銘柄ステータス」セクションを抽出 (ここでは「今日の各銘柄ステータス」を想定)
                # 現在の実装では「前日の各銘柄ステータス」を抽出しているため、
                # レポート生成ロジックに合わせてここも調整が必要
                status_section_start = summary_content.find(
                    "【前日の各銘柄ステータス】"
                )  # ここは「今日の各銘柄ステータス」に変わるべき
                if status_section_start != -1:
                    status_section = summary_content[status_section_start:]
                    # 次のセクションの開始（例: 空行や別の見出し）までを抽出
                    next_section_start = status_section.find(
                        "\n\n", len("【前日の各銘柄ステータス】")
                    )
                    if next_section_start != -1:
                        status_section = status_section[:next_section_start]
                    message += status_section.strip() + "\n\n"
                else:
                    message += "今日の銘柄ステータスが見つかりませんでした。\n\n"
            else:
                message += (
                    f"日付 {report_date} のサマリーレポートが見つかりませんでした。\n\n"
                )
    else:
        message += (
            "全銘柄売買タイミング分析サマリーレポートが見つかりませんでした。\n\n"
        )

    # 日足での急落アラート (当日)
    portfolio_df = analyzer.get_portfolio()
    sharp_declines_messages = []
    for _, holding in portfolio_df.iterrows():
        ticker = holding["code"]
        price_df = analyzer.fetch_stock_data(ticker, period="5d")  # 過去数日間のデータ
        if not price_df.empty:
            price_df.index = pd.to_datetime(price_df.index)
            today_prices = price_df[price_df.index.date == today.date()]["Close"]
            if not today_prices.empty:
                sharp_declines = detect_sharp_decline(
                    today_prices, decline_threshold=0.05
                )
                if not sharp_declines.empty:
                    for _, row in sharp_declines.iterrows():
                        sharp_declines_messages.append(
                            f"・{holding['name']} ({ticker}): {row['DeclineRate']} の急落 ({row['Date']})"
                        )

    if sharp_declines_messages:
        message += (
            "【今日の日足急落アラート】\n" + "\n".join(sharp_declines_messages) + "\n\n"
        )
    else:
        message += "【今日の日足急落アラート】\n該当する銘柄はありませんでした。\n\n"

    # ポートフォリオ全体の当日の損益
    daily_pnl = analyzer.get_portfolio_pnl(
        today - timedelta(days=1), today
    )  # 前日終値から当日終値までの損益
    message += "【ポートフォリオ日次損益】\n"
    message += f"・総損益: {daily_pnl['total_pnl']:.2f}円\n"
    message += f"・実現損益: {daily_pnl['realized_pnl']:.2f}円\n"
    message += f"・評価損益: {daily_pnl['unrealized_pnl']:.2f}円\n\n"

    message += "【今日の市場の動き】\n"
    message += _get_market_news_for_period("1d") + "\n\n"
    message += (
        "詳細な日足分析結果はログまたは別途生成される詳細レポートをご確認ください。\n"
    )

    send_alert(message, level="INFO")
    logger.info("その日の日次レポートのSlack送信が完了しました。")


# 土曜日の13：00に週次レポートを生成し、Slackに送信する
def send_weekly_report(is_test_mode: bool = False):
    """週次レポートをSlackに送信する"""
    logger.info("週次レポートを生成し、Slackに送信します。")

    message = f"【週次レポート】 {datetime.now().strftime('%Y-%m-%d')} 週次分析\n\n"

    # ポートフォリオ分析サマリーレポートの取得
    summary_report_path = _get_latest_report_file("summary")
    # ポートフォリオ分析サマリーレポートの取得と送信
    summary_report_path = _get_latest_report_file("summary")
    if summary_report_path and os.path.exists(summary_report_path):
        with open(summary_report_path, "r", encoding="utf-8") as f:
            summary_content = f.read()
            # サマリーレポートの主要部分を抽出してメッセージに含める
            message += "【ポートフォリオサマリー】\n"
            # 例: 総投資額、総リターン、年率リターンなどを抽出
            for line in summary_content.splitlines():
                if (
                    "総投資額" in line
                    or "総リターン" in line
                    or "年率リターン" in line
                    or "シャープレシオ" in line
                ):
                    message += f"{line}\n"
            message += "\n"
        send_alert("週次サマリーレポート", level="INFO")
    else:
        message += "ポートフォリオサマリーレポートが見つかりませんでした。\n"

    # グラフ画像の取得と送信 (plotsディレクトリ)
    plot_dir = config.root_dir / "data" / "plots"
    if plot_dir.exists():
        plot_image_files = sorted(plot_dir.glob("*.png"), reverse=True)
        if plot_image_files:
            message += "\n【最新のプロット画像】\n"
            for img_file in plot_image_files[:3]:  # 最新の3枚を例として
                message += f"- {os.path.basename(img_file)}\n"
                send_alert(f"プロット画像: {os.path.basename(img_file)}", level="INFO")
        else:
            message += "最新のプロット画像が見つかりませんでした。\n"

    # グラフ画像の取得と送信 (chartImgディレクトリ)
    chart_img_dir = config.root_dir / "data" / "chartImg"
    if chart_img_dir.exists():
        chart_image_files = sorted(chart_img_dir.glob("*.png"), reverse=True)
        if chart_image_files:
            message += "\n【最新のチャート画像】\n"
            for img_file in chart_image_files[:3]:  # 最新の3枚を例として
                message += f"- {os.path.basename(img_file)}\n"
                send_alert(f"チャート画像: {os.path.basename(img_file)}", level="INFO")
        else:
            message += "最新のチャート画像が見つかりませんでした。\n"

    # 週間のポートフォリオ損益
    last_week = datetime.now() - timedelta(weeks=1)
    weekly_pnl = analyzer.get_portfolio_pnl(last_week, datetime.now())
    message += "【ポートフォリオ週次損益】\n"
    message += f"・総損益: {weekly_pnl['total_pnl']:.2f}円\n"
    message += f"・実現損益: {weekly_pnl['realized_pnl']:.2f}円\n"
    message += f"・評価損益: {weekly_pnl['unrealized_pnl']:.2f}円\n\n"

    # 資産配分
    asset_allocation = analyzer.get_portfolio_asset_allocation()
    message += "【ポートフォリオ資産配分】\n"
    message += "・セクター別:\n"
    if asset_allocation["sector_allocation"]:
        for sector, percentage in asset_allocation["sector_allocation"].items():
            message += f"  - {sector}: {percentage:.2f}%\n"
    else:
        message += "  - データなし\n"
    message += "・銘柄別:\n"
    if asset_allocation["stock_allocation"]:
        for stock, percentage in asset_allocation["stock_allocation"].items():
            message += f"  - {stock}: {percentage:.2f}%\n"
    else:
        message += "  - データなし\n"
    message += "\n"

    message += "【週間の市場トレンドと注目銘柄】\n"
    message += _get_market_news_for_period("7d") + "\n"
    message += "週間での市場全体のトレンドやセクターごとの動向、特にパフォーマンスが良かった/悪かった銘柄のハイライトなどをここに含めます。\n"

    send_alert(message, level="INFO")
    logger.info("週次レポートのSlack送信が完了しました。")


# 月末の17:00に月次レポートを生成し、Slackに送信する
def send_monthly_report(is_test_mode: bool = False):
    """月次レポートをSlackに送信する"""
    logger.info("月次レポートを生成し、Slackに送信します。")

    message = f"【月次レポート】 {datetime.now().strftime('%Y-%m-%d')} 月次評価\n\n"

    # 詳細レポートの取得と送信
    detailed_report_path = _get_latest_report_file("detailed")
    if detailed_report_path and os.path.exists(detailed_report_path):
        message += "【詳細レポート】\n"
        message += f"{os.path.basename(detailed_report_path)}\n"
        send_alert("月次詳細レポート", level="INFO")
    else:
        message += "詳細レポートが見つかりませんでした。\n"

    # 月間のポートフォリオパフォーマンス
    last_month_start = datetime.now().replace(day=1)
    monthly_performance = analyzer.get_portfolio_monthly_performance(datetime.now())
    message += "【月間のポートフォリオパフォーマンス】\n"
    message += f"・総投資額: {monthly_performance['total_investment']:.2f}円\n"
    message += f"・総リターン: {monthly_performance['total_return']:.2f}円\n"
    message += f"・年率リターン: {monthly_performance['annualized_return']:.2%}\n"
    message += f"・シャープレシオ: {monthly_performance['sharpe_ratio']:.2f}\n"
    message += f"・月間損益: {monthly_performance['monthly_pnl']:.2f}円\n"
    message += (
        f"・月間資産配分変化: {monthly_performance['asset_allocation_change']:.2%}\n\n"
    )

    # ポートフォリオの再構築検討事項
    rebalancing_suggestions = analyzer.get_portfolio_rebalancing_suggestions()
    message += "【ポートフォリオの再構築検討事項】\n"
    message += rebalancing_suggestions + "\n\n"

    message += "【市場の長期トレンド分析と経済指標の影響】\n"
    message += _get_market_news_for_period("1m") + "\n"
    message += "月間を通じた市場全体の長期的なトレンド分析、主要な経済指標やイベントがポートフォリオに与えた影響の分析をここに含めます。\n"

    # 個別銘柄の月間パフォーマンス (ポートフォリオ内の全銘柄)
    portfolio_df = analyzer.get_portfolio()
    if not portfolio_df.empty:
        message += "【個別銘柄の月間パフォーマンス】\n"
        for _, holding in portfolio_df.iterrows():
            code = holding["code"]
            individual_performance = analyzer.get_individual_stock_performance(
                code, last_month_start, datetime.now()
            )
            if "error" not in individual_performance:
                message += f"・{individual_performance['name']} ({individual_performance['code']}):\n"
                message += f"  - 月間損益: {individual_performance['pnl']:.2f}円\n"
                message += (
                    f"  - 最新価格: {individual_performance['latest_price']:.2f}円\n"
                )
                message += f"  - 今後の見通し: {individual_performance['outlook']}\n"
                if individual_performance["transactions"]:
                    message += "  - 最近の取引:\n"
                    for tx in individual_performance["transactions"]:
                        message += f"    - {tx['trade_date'].strftime('%Y-%m-%d')} \
                                            {tx['trade_type']} \
                                            {tx['quantity']}株 \
                                            @ {tx['price']}円\n"
                message += "\n"
            else:
                message += f"・{code}: パフォーマンスデータの取得に失敗しました ({individual_performance['error']})\n"
    else:
        message += (
            "【個別銘柄の月間パフォーマンス】\nポートフォリオに銘柄がありません。\n\n"
        )

    send_alert(message, level="INFO")
    logger.info("月次レポートのSlack送信が完了しました。")


# %%
def send_startup_report(is_test_mode: bool = False):
    """起動確認レポートをSlackに送信する"""
    logger.info("起動確認レポートを生成し、Slackに送信します。")
    message = (
        f"【システム起動通知】 Stock Management Always Task が起動しました。\n"
        f"起動時刻: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"バックグラウンドタスク (watch, monitor, analyze) が開始されました。\n"
    )
    send_alert(message, level="INFO", is_test_mode=is_test_mode)
    logger.info("起動確認レポートのSlack送信が完了しました。")


# %%

if __name__ == "__main__":
    start_monitoring()
    # テスト実行
    print("--- 起動確認レポートテスト ---")
    send_startup_report()
    print("--- 日次モニターレポート(前日) ---")
    send_daily_morning_report()
    print("\n--- 日次イブニングレポート(当日) ---")
    send_daily_evening_report()
    print("\n--- 週次レポートテスト ---")
    send_weekly_report()
    print("\n--- 月次レポートテスト ---")
    send_monthly_report()
