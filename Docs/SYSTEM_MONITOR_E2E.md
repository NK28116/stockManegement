# System Monitor の E2E テスト (PRIDEV-494)

System Monitor の認証境界と異常時表示を、公開前の回帰として固定する。

## 実行方法

```bash
PYTHONPATH=. pytest tests/test_system_monitor_e2e.py -v
```

追加の依存やブラウザは不要。CI (`make test`) でもそのまま実行される。

## テストが通す経路

実際に **uvicorn を起動**し、`httpx` から本物のソケット経由でアクセスする。
ログイン → セッション Cookie 保持 → 保護画面 → API までを、
middleware・認証ガード・テンプレート描画・API を含めて通しで検証する。

差し替えるのは **GCP との境界 (`SystemHealthService`) だけ**で、
それ以外は本番と同じ経路を通る。

```
httpx (Cookie 保持)
  └─ uvicorn (127.0.0.1:<ephemeral>)
       └─ FastAPI app  ← 本番と同じ middleware / ルーター
            ├─ auth middleware  (PRIDEV-481)
            ├─ /system-monitor  (PRIDEV-493)
            └─ /api/system-monitor (PRIDEV-492)
                 └─ SystemHealthService  ← ここだけスタブ
```

## ブラウザを使わない理由

- CI にブラウザが無い
- テンプレートが Tailwind / Vue を CDN から読み込むため、オフライン環境では
  DOM を評価できない

そのため検証対象は「サーバが返す HTML / JSON」であり、
DOM 描画後の見た目の検証は本テストの対象外とする。

## 検証項目

| 分類 | 内容 |
| --- | --- |
| 未認証経路 | 画面はログインへリダイレクト / API は 401 |
| 未認証経路 | 誤ったパスワードではアクセスできない |
| 未認証経路 | 署名を偽造した Cookie は拒否される |
| 認証済み経路 | ログイン後に画面と API を参照できる |
| 認証済み経路 | ログアウトで再び拒否される |
| 異常系 | 権限不足は 403。内部の権限詳細 (ロール名) を返さない |
| 異常系 | Cloud API 障害は 200 + `degraded` で安全に表示できる |
| 異常系 | 想定外エラーは 503。例外メッセージ・型名・Traceback を返さない |
| 秘密値 | ログ本文・ラベルへ仕込んだ API キー / Bearer トークン / パスワードが API レスポンスへ現れない |
| 秘密値 | 画面へパスワード・署名鍵・環境変数名が現れない |
| 秘密値 | セッション Cookie が HttpOnly で発行される |
