# Web UI 実装ドキュメント

## 概要
既存の株式管理システムに、トレーディングルールのパラメータ調整とチャート閲覧を行うためのWebインターフェースを追加しました。
既存のトレーディングロジック（`trading_rules.py` 等）には影響を与えない独立したレイヤーとして実装しています。

## アーキテクチャ

*   **バックエンド**: Python / FastAPI
*   **フロントエンド**: HTML / Vue.js (CDN版、シングルファイル)
*   **設定管理**: JSONファイル (`data/config/trading_rules.json`)

## ファイル構成

新しく追加・変更したファイルは以下の通りです。

```text
python/
 └── web/
     ├── __init__.py
     ├── app.py              # アプリケーションエントリポイント
     ├── schemas.py          # Pydanticモデル（バリデーション用）
     ├── routes/             # APIエンドポイント
     │   ├── rules.py        # ルール設定の読み書き
     │   └── charts.py       # プロット画像の配信
     ├── services/
     │   └── rule_store.py   # JSON設定ファイルの操作ロジック
     └── templates/
         └── index.html      # フロントエンドUI
data/
 └── config/
     └── trading_rules.json  # 編集可能な設定値
```

## 機能

### 1. ダッシュボード (Dashboard)
`data/plots/` および `data/chartImg/` に保存されているチャート画像を一覧表示します。
ブラウザ上で最新の分析結果を視覚的に確認できます。

### 2. 設定 (Settings)
`data/config/trading_rules.json` の値をWebフォームから編集・保存できます。
これにより、コードを修正することなく `stop_loss_percent` などのパラメータを調整可能です。

**注意**:
現状では、このWeb UIはJSONファイルを書き換えるのみです。
トレーディングロジック側 (`python/trading/etc`) で、このJSONファイルを読み込むように改修することで、変更が実際のトレード判断に反映されるようになります。

## 実行方法

### ポート設定
デフォルトではポート **8888** で起動するように手順を定めています。

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# サーバー起動 (ポート8888指定)
uvicorn python.web.app:app --reload --port 8888
```

起動後、ブラウザで [http://localhost:8888](http://localhost:8888) にアクセスしてください。
