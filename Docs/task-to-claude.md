# Claudeへの実装指示書：ユーザーレビューに基づくUI・DB連帯機能の改善 (2026-02-22)

本ドキュメントは、ユーザーから寄せられた3点のフィードバックに対応し、フロントエンドの操作UXとバックエンドの構成（DB・シグナル）を改善するための指示書です。
以下の3つの要件を順次実装してください。

---

## 1. Check Signals ボタン機能の統合（安全なテーブル作成）
- **対象**: `python/web/routes/signals.py`, `python/web/templates/index.html` (紫色のCheck Signalsボタン関連)
- **課題**: 現在、バックエンドのシグナル分析（`watch.analyze()`等）が実行される際、内部で `signals` や `signal_history` といったデータベーステーブルが存在せず `no such table: signals` 等のエラーで落ちる報告がありました。
- **実装指示**:
  1. `/api/signals/analyze` のような分析エンドポイントの先頭（または `watch.analyze()` の先頭）で、`database.py` の `init_db()` または `Base.metadata.create_all(bind=engine)` を呼び出し、確実に実行時にテーブル類が初期化・存在チェックされる安全機構を導入してください。
  2. ダッシュボード上の紫色の「Check Signals」ボタンがこの機能と完全に統合され、エラーなく動作完了するように結びつけてください。

---

## 2. Sell / Delete アクションのトースト表示改善
- **対象**: `python/web/templates/index.html` 内の `sellStock()` と `deleteStock()` メソッド
- **課題**: 「sellや削除を押した時のトースト表示が消えるのが早過ぎて確認できない」というレビューがあります。`sellStock` は現状 `alert()` のままであり、また `deleteStock` は `this.fetchCharts()` の非同期UI更新時にDOM再構築等でトーストが消失している可能性があります。
- **実装指示**:
  1. `sellStock()` 完了時の `alert("Stock ... sold successfully!");` を廃止し、`deleteStock()` のように `this.toastMessage` と `this.toastType = 'success'` を使用したトースト通知に変更してください。
  2. 通知のセットを `await this.fetchCharts()` の実行が完全に終わった **直後に行う**（または `fetchCharts` の中でトースト変数をリセットするような処理があれば消す）ようにロジックの流れを調整し、トースト通知が画面上に確実に3〜7秒間安定して留まるようにVueの非同期処理や状態更新順を修正してください。

---

## 3. ローカルCSVの連動徹底 (my_stock_local.csv)
- **対象**: `python/db/database.py`, `python/config.py` および全バックエンド関連ファイル
- **課題**: 「ローカルで開発しているのに `my_stock_local.csv` と連動していない（ステージング用の `my_stock.csv` を読んでしまっている）」という指摘があります。
- **実装指示**:
  1. `DB_ENV` 環境変数に依存して切り替わるはずの `config.codes_path` が、全てのCSV I/O 処理で正しく優先・徹底されているか調査し、もし `pd.read_csv("data/my_stock.csv")` のようにハードコーディングされている箇所があれば、すべて `config.codes_path` に一元化してください。
  2. 特に `database.py` の `sync_csv_to_portfolio()` 等の起動時のデータベース同期処理が、間違ったCSVを起点にしないように修正してください。

---

## 検証手順（セルフチェック事項）
1. `DB_ENV=local` でローカルサーバーを起動する。
2. ダッシュボードを開き、任意の銘柄を「Sell(売却)」実行し、画面上に緑色のトースト通知が十分な時間表示されることを確認する。
3. 紫色の「Check Signals」ボタンをクリックし、バックエンドコンソールやフロントエンドでエラー（テーブル不在等）が発生せず、正常に実行完了することを確認する。
4. ローカル起動時、およびデータ更新時に常に `data/my_stock_local.csv` に対して Read/Write が走り、`data/my_stock.csv`（クラウド・ステージング用）が不当に変更されていないことを確認する。

以上の実装をお願いします。
