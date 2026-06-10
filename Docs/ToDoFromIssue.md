# これからやること（Linear Issue → やるべき要件）

> Linear プロジェクト **stockManagement**（team: PrivateDev / PRIDEV）の課題から生成。
> 並び: ワークフロー状態 → マイルストーン → 優先度（🔴Urgent / 🟠High / 🟡Medium / ⚪Low / ・なし）。
> 生成日: 2026-06-10 ／ [Linear プロジェクト](https://linear.app/niwa-private-dev/project/stockmanagement-0302b2aea712/overview)
>
> 使い方: まず下の「インデックス」で全体像を把握し、着手する issue を選んだら「要件詳細」の節に末尾テンプレートを使って記入していく。

---

## インデックス（やることリスト）

### 🚧 In Progress

- [ ] **PRIDEV-28** 株式運用サポートツール（親エピック）

### 🗂 Backlog — マイルストーン別

#### 🏁 v1.0 GA — リリースブロッカー（最優先）

- [ ] 🔴 **PRIDEV-113** [Security] Git履歴の浄化 (BFG/filter-repo)
- [ ] 🟠 **PRIDEV-291** [Bug] ダッシュボードの画像が文字化け（GitHub #15）
- [ ] 🟠 **PRIDEV-283** [Chore] requirements.txt の依存バージョン固定
- [ ] 🟠 **PRIDEV-111** [Infra] IAM権限の最小化と整理
- [ ] 🟠 **PRIDEV-114** [Security] シークレットスキャンとLICENSE追加

#### 🛠 v1.1 — 運用・UX安定化

- [ ] 🟡 **PRIDEV-120** [Docs] OSS用ドキュメントの拡充（GitHub #17, #12 集約）
- [ ] 🟡 **PRIDEV-115** [UI] 全体成績（Performance Summary）の表示
- [ ] 🟡 **PRIDEV-117** [UI] Self-Documenting UI への改修（GitHub #11 集約）
- [ ] 🟡 **PRIDEV-288** [Perf] 初回起動時の遅さを修正（GitHub #14）
- [ ] 🟡 **PRIDEV-112** [Ops] Cloud Logging の有効化と異常検知
- [ ] ⚪ **PRIDEV-287** [UI] プルダウンが不足しているのを修正
- [ ] ⚪ **PRIDEV-292** [Bug] ドロップダウンのずれ（GitHub #16）
- [ ] ⚪ **PRIDEV-284** [Chore] Alembicマイグレーションの整合 (stamp head)

#### ✨ v1.5 — 機能拡張

- [ ] 🟠 **PRIDEV-122** [Feature] 通知システムの強化 (Slack/Discord)（GitHub #18）
- [ ] 🟡 **PRIDEV-289** [Feature] 次に取引する銘柄の候補検索（GitHub #22）
- [ ] 🟡 **PRIDEV-123** [Feature] 株主優待(Present)管理機能の実装

#### 💰 v2.0 — マネタイズ・横展開

- [ ] 🟠 **PRIDEV-285** [Feature/Epic] 有料SaaS化・マルチテナント化（GitHub #21 / WayToBenefit）
  - [ ] ⚪ **PRIDEV-293** [Extend] 時間経過による推移観察ツールへの汎用化（285の子）
- [ ] 🟡 **PRIDEV-282** [Feature] 仮想通貨(Coincheck)対応：価格取得の抽象化（GitHub #20）
- [ ] 🟡 **PRIDEV-290** [Feature] 外部証券会社APIとの連携（GitHub #19）

#### 🔮 Backlog — 将来構想 (Phase 8)

- [ ] ⚪ **PRIDEV-118** [UI] UI/UXのモダン化（React/Vue.js 移行検討）
- [ ] ⚪ **PRIDEV-286** [Refactor] アーキテクチャ三分割（Next.js/Go/Python）（GitHub #7）

### ✅ Done（参考）

本番化・運用(2026-06): PRIDEV-121 Cron有効化 / PRIDEV-110 app.py責務分離 / PRIDEV-116 CheckSignal・Update整合 / PRIDEV-1〜4 定例タスク
モジュール初期実装(2025-09): PRIDEV-5〜26（analysis / watch / utils / visualization / trading 各モジュール）

### 🚫 Canceled

PRIDEV-27 formula_for_analyzer.py（廃止）

---

## 要件詳細（着手するものから記入）

末尾の「要件テンプレート」をコピーして各 issue ごとに記入する。まず v1.0 GA ブロッカーから着手する想定で、把握済みの2件を記入済み。

---

### [PRIDEV-283] requirements.txt の依存バージョン固定 🟠

#### 概要

依存を固定していなかったため、本番(Render)のクリーンビルドで最新 Starlette が入り、`TemplateResponse` のシグネチャ変更で全ページ 500 になった。再発防止のため主要依存をピン留めする。

#### 機能要件

##### 1.1 目的
- ローカルとデプロイ先で同一バージョンを保証し、ビルドのたびに挙動が変わる事故を防ぐ。

##### 1.2 入力 / 対象
- `requirements.txt`（最低限 `fastapi` / `starlette` / `uvicorn` / `pydantic`、できれば全依存）。

##### 1.3 処理
- 現在の動作確認済みバージョンを `pip freeze` で取得し、`==` で固定。
- もしくは `requirements.lock` / uv / pip-tools 等の lock 機構を導入。

##### 1.4 出力
- バージョン固定済みの `requirements.txt`（or lock ファイル）。UI変化なし。

##### 1.5 エラー / リスク
- 固定が古すぎるとセキュリティ更新が滞る → 定期的な更新フローも別途検討。

##### 1.6 境界条件
- GCE(Python3.11) と Render(Dockerfile, Python3.12) で同一バージョンが解決可能か確認。

#### 非機能要件
- **可用性**: クリーンビルドでの再現性確保（本タスクの主目的）。
- **運用**: 依存更新時は CI でスモークテスト（トップページ200確認）を回す。

#### テスト観点
- クリーン環境で `pip install -r requirements.txt` → `uvicorn` 起動 → `/` が 200。
- ローカルと本番で `pip freeze` の主要差分がないこと。

#### 追記
- 関連: 本番デプロイ時の 500（TemplateResponse 新シグネチャ対応済み）。根本原因は未固定依存。

---

### [PRIDEV-284] Alembicマイグレーションの整合 (stamp head) ⚪

#### 概要

本番DB移行で不足テーブル（`signals` 等）を `create_all()` で作成したため、`alembic_version` と実スキーマがズレている。今後のスキーマ変更を Alembic で安全に行えるよう整合させる。

#### 機能要件

##### 1.1 目的
- マイグレーション履歴と実DBスキーマを一致させ、以後の変更を Alembic 経由に統一する。

##### 1.2 入力 / 対象
- GCE 上の `stock_db`（localhost:5432, user `stock_user`）。現行スキーマ。

##### 1.3 処理
- 現行スキーマが最新リビジョン相当であることを確認し、`alembic stamp head` を実行。
- 差分がある場合は、差分用リビジョンを作成してから `upgrade`。

##### 1.4 出力
- `alembic_version` が head を指す状態。UI変化なし。

##### 1.5 エラー / リスク
- 実スキーマとモデル定義に差分があると stamp 後に不整合 → 事前に `alembic revision --autogenerate` で差分確認。

##### 1.6 境界条件
- 本番DBに対して破壊的操作をしない（stamp はメタのみ更新だが、バックアップ推奨）。

#### 非機能要件
- **可用性**: 実行前に `pg_dump` でバックアップ。
- **運用**: 手順を `Docs` 化（移行ランブックに追記）。

#### テスト観点
- stamp 後に `alembic current` が head。
- ダミーのモデル変更 → `revision --autogenerate` → `upgrade` が通る。

#### 追記
- 背景: 旧ダンプはスキーマのみ・データ0件で `signals`/`watchlist`/`stock_notes` 欠落 → 新VMで create_all 済み。

---

## 要件テンプレート（コピーして使う）

```
### [PRIDEV-XXX] タイトル 優先度

#### 概要
-

#### 機能要件
##### 1.1 目的
- なぜ必要か
##### 1.2 入力
- 入力値 / 型 / 制約
##### 1.3 処理
- 何をするか
##### 1.4 出力
- 結果 / UI変化 / 保存内容
##### 1.5 エラー
- 失敗条件 / バリデーション / 通信失敗時
##### 1.6 境界条件
- null / 空文字 / 上限値 / 多重実行

#### 非機能要件
- パフォーマンス / セキュリティ / 可用性 / 拡張性 / 運用・監視

#### テスト観点
- 正常系 / 異常系 / 境界値

#### 追記
-
```
