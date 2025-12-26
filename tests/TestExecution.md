# シグナル生成API テスト実行手順書

## 📋 目次
1. [はじめに](#はじめに)
2. [事前準備](#事前準備)
3. [テスト実行手順](#テスト実行手順)
4. [期待される結果](#期待される結果)
5. [トラブルシューティング](#トラブルシューティング)
6. [補足情報](#補足情報)

---

## はじめに

この手順書では、シグナル生成API（`POST /api/signals/check`）のテスト実行方法を説明します。

**対象者**: 新人エンジニア
**所要時間**: 約15〜20分
**難易度**: ★☆☆（初級）

---

## 事前準備

### 1. プロジェクトディレクトリへの移動

ターミナル（コマンドプロンプト）を開き、プロジェクトのルートディレクトリに移動します。

```bash
cd /path/to/stockManegement
```

**💡 ヒント**: `pwd`（Macの場合）または `cd`（Windowsの場合）コマンドで現在のディレクトリを確認できます。

---

### 2. Pythonの仮想環境を有効化

プロジェクト専用のPython環境を有効化します。

#### Macの場合:
```bash
source venv/bin/activate
```

#### Windowsの場合:
```bash
venv\Scripts\activate
```

**✅ 確認方法**:
コマンドプロンプトの先頭に `(venv)` という表示が追加されていればOKです。

```bash
(venv) user@MacBook stockManegement %
```

---

### 3. 必要なライブラリのインストール確認

テストに必要なライブラリがインストールされているか確認します。

```bash
pip list | grep pytest
```

**期待される出力例**:
```
pytest                  7.4.3
pytest-asyncio          0.21.1
```

もし `pytest` が表示されない場合は、以下のコマンドでインストールしてください。

```bash
pip install pytest pytest-asyncio httpx
```

---

### 4. データベースのマイグレーション実行

`SignalHistory` テーブルが作成されていることを確認します。

```bash
python -m python.db.migrate_signal_history
```

**期待される出力**:
```
✅ SignalHistoryテーブルが正常に作成されました
```

**❌ エラーが発生した場合**:
データベースの接続情報を確認してください（`python/config.py` ファイル）。

---

## テスト実行手順

### 【手順1】テストファイルの存在確認

テストファイルが正しい場所に存在するか確認します。

```bash
ls tests/test_signals_api.py
```

**期待される出力**:
```
tests/test_signals_api.py
```

もしファイルが見つからない場合は、実装者に確認してください。

---

### 【手順2】全テストを実行

以下のコマンドで、すべてのテストを実行します。

```bash
pytest tests/test_signals_api.py -v
```

**コマンドの説明**:
- `pytest`: pytestテストフレームワークを実行
- `tests/test_signals_api.py`: テストファイルのパス
- `-v`: 詳細な出力（verboseモード）

---

### 【手順3】特定のテストだけを実行する（オプション）

特定のテスト関数だけを実行したい場合は、以下のように指定します。

#### 正常系テストのみ実行:
```bash
pytest tests/test_signals_api.py::test_signal_check_success -v
```

#### 異常系テストのみ実行:
```bash
pytest tests/test_signals_api.py::test_signal_check_invalid_stock_code -v
```

---

## 期待される結果

### ✅ 成功時の出力例

すべてのテストが成功すると、以下のような出力が表示されます。

```
================================ test session starts =================================
platform darwin -- Python 3.13.0, pytest-7.4.3, pluggy-1.3.0
collected 9 items

tests/test_signals_api.py::test_signal_check_success PASSED                    [ 11%]
tests/test_signals_api.py::test_signal_check_multiple_stocks PASSED            [ 22%]
tests/test_signals_api.py::test_signal_check_invalid_stock_code PASSED         [ 33%]
tests/test_signals_api.py::test_signal_check_missing_stock_code PASSED         [ 44%]
tests/test_signals_api.py::test_signal_check_empty_stock_code PASSED           [ 55%]
tests/test_signals_api.py::test_signal_check_invalid_json PASSED               [ 66%]
tests/test_signals_api.py::test_signal_check_special_characters_in_code PASSED [ 77%]
tests/test_signals_api.py::test_signal_check_very_long_stock_code PASSED       [ 88%]

================================ 9 passed in 12.34s ==================================
```

**✅ チェックポイント**:
- すべてのテストに `PASSED` が表示されている
- `FAILED` や `ERROR` が1つも表示されていない

---

### ❌ 失敗時の出力例

テストが失敗すると、以下のような出力が表示されます。

```
tests/test_signals_api.py::test_signal_check_success FAILED                    [ 11%]

================================== FAILURES ==========================================
_________________________ test_signal_check_success _________________________________

    def test_signal_check_success(client, db_session):
        request_data = {"stock_code": "7203.T"}
        response = client.post("/api/signals/check", json=request_data)
>       assert response.status_code == 200
E       AssertionError: assert 500 == 200
E        +  where 500 = <Response [500]>.status_code

tests/test_signals_api.py:89: AssertionError
================================ 1 failed, 8 passed in 10.23s ========================
```

**❌ 失敗した場合の対応**:
1. エラーメッセージを読む（どのテストが失敗したか確認）
2. 失敗の原因を特定する（例: データベース接続エラー、API実装のバグ）
3. 開発者に報告する（エラーメッセージのスクリーンショットを添付）

---

## テスト項目と期待結果の詳細

### 1. 正常系テスト

#### 1-1. `test_signal_check_success`
**テスト内容**: 存在する銘柄コード（例: "7203.T"）でAPIを呼び出す

**期待される結果**:
- ✅ HTTPステータスコード `200 OK` が返る
- ✅ レスポンスJSONに以下のフィールドが含まれる:
  - `stock_code`: 銘柄コード
  - `signal`: 'BUY', 'SELL', 'HOLD' のいずれか
  - `price`: 株価（正の数値）
  - `reason`: シグナル生成理由
  - `rule_version`: ルールバージョン
  - `timestamp`: シグナル生成日時
- ✅ `signal_history` テーブルに1件のレコードが追加される

#### 1-2. `test_signal_check_multiple_stocks`
**テスト内容**: 複数の銘柄で連続してAPIを呼び出す

**期待される結果**:
- ✅ すべてのリクエストが成功する（`200 OK`）
- ✅ データベースに複数のレコードが保存される

---

### 2. 異常系テスト

#### 2-1. `test_signal_check_invalid_stock_code`
**テスト内容**: 存在しない銘柄コード（例: "INVALID999.T"）でAPIを呼び出す

**期待される結果**:
- ✅ HTTPステータスコード `404 Not Found` または `500 Internal Server Error` が返る
- ✅ レスポンスに `detail` フィールド（エラーメッセージ）が含まれる

#### 2-2. `test_signal_check_missing_stock_code`
**テスト内容**: `stock_code` が欠落しているリクエストを送信

**期待される結果**:
- ✅ HTTPステータスコード `422 Unprocessable Entity` が返る
- ✅ バリデーションエラーの詳細が返る

#### 2-3. `test_signal_check_empty_stock_code`
**テスト内容**: `stock_code` に空文字列を指定

**期待される結果**:
- ✅ HTTPステータスコード `422` または `404/500` が返る

#### 2-4. `test_signal_check_invalid_json`
**テスト内容**: 不正なJSON形式でリクエストを送信

**期待される結果**:
- ✅ HTTPステータスコード `422 Unprocessable Entity` が返る

---

### 3. エッジケーステスト

#### 3-1. `test_signal_check_special_characters_in_code`
**テスト内容**: 特殊文字を含む銘柄コードでAPIを呼び出す

**期待される結果**:
- ✅ エラーステータスコード（`404`、`500`、または `422`）が返る

#### 3-2. `test_signal_check_very_long_stock_code`
**テスト内容**: 非常に長い文字列を銘柄コードとして送信

**期待される結果**:
- ✅ エラーステータスコード（`404`、`500`、または `422`）が返る

---

## パフォーマンステスト（手動実行）

### 【手順】

1. **FastAPIサーバーを起動**

別のターミナルウィンドウを開き、以下のコマンドでサーバーを起動します。

```bash
cd /path/to/stockManegement
source venv/bin/activate  # 仮想環境を有効化
uvicorn python.web.app:app --reload
```

**期待される出力**:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

---

2. **curlコマンドでAPIを連続実行**

以下のコマンドを5回実行し、レスポンスタイムを計測します。

```bash
time curl -X POST "http://localhost:8000/api/signals/check" \
  -H "Content-Type: application/json" \
  -d '{"stock_code": "7203.T"}'
```

**期待される結果**:
- ✅ レスポンスタイムが **2秒以内** に収まる
- ✅ HTTPステータスコード `200 OK` が返る

**出力例**:
```json
{
  "stock_code": "7203.T",
  "signal": "BUY",
  "price": 2500.00,
  "reason": "パターン（++）エントリー",
  "rule_version": "0",
  "timestamp": "2025-12-26T08:30:00.000Z"
}

real    0m1.234s
user    0m0.045s
sys     0m0.023s
```

**⚠️ 注意**:
- もしレスポンスタイムが2秒を超える場合は、開発者に報告してください。
- 非同期化やキャッシュ機構の導入が必要かもしれません。

---

## トラブルシューティング

### ❓ テストが実行できない

**症状**: `pytest: command not found`

**対処法**:
```bash
pip install pytest pytest-asyncio httpx
```

---

### ❓ データベースエラーが発生する

**症状**: `sqlalchemy.exc.OperationalError: could not connect to server`

**対処法**:
1. データベースが起動しているか確認
2. `python/config.py` の接続情報を確認
3. マイグレーションが実行済みか確認

---

### ❓ 一部のテストだけ失敗する

**対処法**:
1. 失敗したテストのエラーメッセージを確認
2. 該当するテスト関数のコメントを読み、期待される動作を理解する
3. 開発者に失敗の詳細を報告する

---

## 補足情報

### テストファイルの構成

```
tests/
├── test_signals_api.py       # シグナルAPIのテストコード
├── test_analyze.py            # 分析機能のテストコード
├── test_data_collector.py     # データ収集のテストコード
└── test_portfolio_analyzer.py # ポートフォリオ分析のテストコード
```

---

### テスト実行時のオプション

| オプション | 説明 | 使用例 |
|----------|------|--------|
| `-v` | 詳細な出力を表示 | `pytest -v` |
| `-s` | print文の出力を表示 | `pytest -s` |
| `-x` | 最初の失敗で停止 | `pytest -x` |
| `--tb=short` | トレースバックを短く表示 | `pytest --tb=short` |
| `-k <keyword>` | キーワードに一致するテストのみ実行 | `pytest -k "success"` |

---

### よくある質問（FAQ）

#### Q1. テストの実行に時間がかかる場合は？
**A1**: yfinanceがリアルタイムでデータを取得するため、ネットワーク環境によっては時間がかかる場合があります。これは正常な動作です。

#### Q2. テスト用のデータベースは自動的にクリーンアップされますか？
**A2**: はい。各テスト実行後に自動的にテーブルが削除されます（`@pytest.fixture` のクリーンアップ処理）。

#### Q3. 本番データベースに影響はありますか？
**A3**: いいえ。テストでは `test_stock.db` という別のデータベースを使用するため、本番データには影響しません。

---

## まとめ

このテストを実行することで、以下が確認できます:

✅ シグナル生成APIが正常に動作すること
✅ 異常なリクエストに対して適切にエラーを返すこと
✅ データベースに正しくレコードが保存されること
✅ パフォーマンス要件を満たしていること

テスト結果は必ずレポートとして保存し、開発チームに共有してください。

---

**📧 質問・問題報告先**:
開発チームリーダー / プロジェクトマネージャー

**📅 作成日**: 2025年12月26日
**📝 バージョン**: 1.0
