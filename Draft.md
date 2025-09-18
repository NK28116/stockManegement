# 修正案などの下書き

---
`README.md`

---

# 株式管理・分析システム（Stock Management System）

個人投資家向けの株式データ収集・監視・分析・レポーティングを一体化したツール群です。日次/週次/月次/年次の定期タスクや、リアルタイム監視（擬似含む）を実行できます。

- 監視（リアルタイム/開発用の擬似）: `python/watch/`
- 集計（日足化）: `python/watch/dailyAggregator.py`
- 分析（MACD, ボリンジャーバンド, 急落検知）: `python/watch/analyze.py`
- タスク実行: `main.py` と `makefile`
- 設定: `python/config.py`
- ログ: `log/` 配下（カテゴリ/モジュール/日付で自動出力）

## 必要条件

- Python 3.10+ を推奨
- pip が利用可能であること

## セットアップ

1) 仮想環境（任意）

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
```

2) 依存関係をインストール

```bash
pip install -r requirements.txt
```

注: `make install` は `requirements-dev.txt` もインストールする前提ですが、当該ファイルが無い環境では上記 `pip install -r requirements.txt` を利用してください。

3) 初期化（任意）

```bash
# DB 初期化（必要に応じて）
make init-db
```

## クイックスタート

- 擬似リアルタイム監視（開発用）

```bash
make watch-dev       # 指定日付を用いた擬似リアルタイム（watch.pyの--devを使用）
```

- リアルタイム監視（本番運用想定）

```bash
make watch-realtime  # 2分周期で監視しDBに保存・アラート
```

- 日足集計（分足→日足）

```bash
make aggregate
```

- 個別銘柄の分析

```bash
make analyze-stock CODE=7203
```

- 一括分析（監視リスト全体）

```bash
make analyze
```

## 主なコマンド（makefile）

- 監視
  - `make watch-dev`        開発モードの擬似リアルタイム監視
  - `make watch-realtime`   リアルタイム監視（2分周期）

- 分析/集計
  - `make analyze`          監視対象全銘柄の分析
  - `make analyze-stock CODE=xxxx`  指定銘柄の分析
  - `make aggregate`        分足データを日足に集計

- データベース
  - `make init-db`          DB初期化
  - `make backup-db`        DBバックアップ

- 定期実行タスク
  - `make run-daily`        日次タスク
  - `make run-weekly`       週次タスク
  - `make run-monthly`      月次タスク
  - `make run-yearly`       年次タスク
  - `make install-cron`     cron 登録（macOS/Linux）

- 開発補助
  - `make install`          依存関係インストール（dev要件ファイルが無い場合は手動インストール推奨）
  - `make test`             テスト実行（tests/想定）
  - `make lint`             Lint（flake8）
  - `make format`           整形（black/isort）
  - `make clean`            ビルドアーチファクト/キャッシュ削除

- Windows 補助
  - `make create-win-batch`  自動起動用バッチ `run_watch.bat` を生成
  - `make run-win-batch`     バッチの動作確認

## 直接実行（main.py）

`main.py` からも定期タスクを直接実行できます。

```bash
python main.py daily
python main.py weekly
python main.py monthly
python main.py yearly
```

## 設定（`python/config.py`）

- パス設定
  - DB: `python/db/my_stock.db`
  - 監視対象CSV: `data/my_stock.csv`
  - ログ: `log/`

- 監視・分析パラメータ（一部）
  - `crash_threshold`: 急落判定（%）。例: `-3.0`
  - `volatility_threshold`: ボラティリティ閾値
  - `ma_short`, `ma_long`, `volatility_period` など

- Slack 通知
  - 環境変数 `SLACK_WEBHOOK` を設定することで通知が有効化されます
  - 機密情報は環境変数で上書きすることを推奨

- 任意の外部API
  - `XXXX_API_KEY`, `XXXX_API_SECRET`, `XXXX_API_URL` を環境変数で指定
  - 未設定時は `yfinance` で価格取得（`python/watch/watch.py` の `get_stock_price()` 参照）

## データとログ

- 入出力
  - 監視対象リスト: `data/my_stock.csv`（ヘッダに `code` 列が必要）
  - 分足保存: DB テーブル `intraday`
  - 日足保存: DB テーブル `stock_data`

- ログ
  - 出力先は `log/<category>/<module>/<YYYY-MM-DD>.log`
  - ロガーは `python/utils/logger.py` の `get_logger()` を使用

## Windows での実行・自動起動

### 1) 環境準備

- Python をインストール（3.10+）
- 仮想環境（任意）

```powershell
python -m venv .\venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Make が無い環境では次節「Make なしでの実行」を参照してください。

### 2) 実行方法

- Git Bash / Make 利用時（推奨）

```bash
# 開発用の擬似リアルタイム
make watch-dev

# 本番想定のリアルタイム監視（2分周期）
make watch-realtime

# 分足→日足集計
make aggregate

# 個別分析
make analyze-stock CODE=7203
```

- Make なしでの実行（PowerShell / cmd）

```powershell
# 監視（開発モード）
python -m python.watch.watch --dev 20250115

# 監視（リアルタイム）
python -m python.watch.watch

# 日足集計
python -m python.watch.dailyAggregator

# 個別分析
python -c "from python.watch.analyze import analyze_daily_data; analyze_daily_data('7203')"
```

### 3) バックグラウンド実行（ウィンドウを出さない）

PowerShell の `Start-Process` を使うと、バックグラウンド実行が簡単です。

```powershell
# 例: リアルタイム監視をバックグラウンドで起動
$command = "python"
$args    = "-m python.watch.watch"
Start-Process -FilePath $command -ArgumentList $args -NoNewWindow -PassThru | Out-Null
```

停止はタスク マネージャー、または PowerShell からプロセスを停止してください。

```powershell
# プロセス一覧から確認（必要に応じて条件を調整）
Get-Process | Where-Object {$_.Path -like "*python*" -and $_.StartInfo.Arguments -like "*python.watch.watch*"}

# 強制停止（プロセスID指定）
Stop-Process -Id <PID>
```

### 4) 自動起動（スタートアップ）

`make create-win-batch` で `run_watch.bat` を生成できます。生成後、下記のいずれかの方法で自動起動に登録します。

1. スタートアップ フォルダにショートカットを配置
   - Win + R → `shell:startup` → フォルダが開いたら `run_watch.bat` のショートカットを配置
2. タスク スケジューラに登録（ログオン時起動）
   - 「タスクの作成」→ トリガー「ログオン時」→ 操作「プログラムの開始」
   - プログラム/スクリプト: `cmd.exe`
   - 引数: `/c "<プロジェクトのフルパス>\run_watch.bat"`

`run_watch.bat` の中身は以下のように生成されます（makefile 定義）。必要に応じて実パスに調整してください。

```bat
@echo off
cd /d C:\Users\%USERNAME%\your_project\watch
python watch.py
```

### 5) 定期実行（タスク スケジューラ）

日次/週次などを自動実行する場合はタスク スケジューラを利用します。

- プログラム/スクリプト: Python 実行ファイル（例: `C:\Python311\python.exe` または 仮想環境の `...\venv\Scripts\python.exe`）
- 引数: `-m python.watch.dailyAggregator` や `main.py` のモード（例: `main.py daily`）
- 「開始（作業ディレクトリ）」: プロジェクト ルート

PowerShell でログ監視（Linux の `tail -f` 相当）

```powershell
Get-Content -Path ".\log\watch\watch\$(Get-Date -Format 'yyyy-MM-dd').log" -Wait -Tail 50
```

### 6) 代替: WSL 利用

WSL 上にプロジェクトを置く/マウントして、Linux と同様に `make`、`screen`、`tmux` 等を利用できます。
（例）

```bash
nohup make watch-realtime > watch.log 2>&1 &
```

## macOS / Linux の定期実行

`make install-cron` で cron に以下のジョブが登録されます（時間は makefile を参照して調整可能）。

- 平日 9:00 日次タスク
- 土曜 10:00 週次タスク
- 毎月 1 日 11:00 月次タスク
- 1/1 12:00 年次タスク

## プロジェクト構成（抜粋）

```text
stockManegement/
├─ data/
├─ log/
├─ python/
│  ├─ watch/               # 監視と日足化/分析
│  ├─ analysis/            # ポートフォリオ等の分析（main.py 内から利用）
│  ├─ db/
│  ├─ utils/
│  ├─ visualization/
│  └─ config.py
├─ main.py
├─ makefile
└─ requirements.txt
```

## トラブルシューティング

- `make watch-realtime` で引数に関するエラーが出る場合
  - `python -m python.watch.watch` を直接実行してください（開発モードは `--dev YYYYMMDD`）。
- `requirements-dev.txt` が無い
  - `pip install -r requirements.txt` を利用してください。
- `data/my_stock.csv` が無い/列が不足
  - `code` 列を含む CSV を用意してください。

## ライセンス

本リポジトリのライセンスが未指定の場合は、クローズド運用を前提とします。公開・配布を行う場合はライセンスの明示を行ってください。

---
