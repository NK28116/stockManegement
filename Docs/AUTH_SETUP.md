# 単一パスワード認証のセットアップ (PRIDEV-481)

管理画面 / 管理API を未認証アクセスから保護するための設定手順。

## 1. パスワードハッシュを生成する

```bash
python scripts/hash_password.py
```

プロンプトへパスワードを入力すると `APP_PASSWORD_HASH=pbkdf2_sha256$...` が出力される。
パスワードはコマンドライン引数で渡さない (シェル履歴へ残るため)。

## 2. 環境変数を設定する

| 環境変数 | 必須 | 既定値 | 説明 |
| --- | --- | --- | --- |
| `APP_PASSWORD_HASH` | ○ | (なし) | 手順 1 で生成したハッシュ。**未設定の場合、認証は無効になる** |
| `APP_PASSWORD` | - | (なし) | 開発用の平文フォールバック。起動時にハッシュ化されるが本番では使わない |
| `AUTH_SECRET_KEY` | ○ | 起動ごとのランダム値 | セッション Cookie の署名鍵。未設定だと再起動でログアウトされる |
| `AUTH_SESSION_MAX_AGE_SECONDS` | - | `43200` (12 時間) | セッション有効期限。**ユーザー確認待ちの暫定値** |
| `AUTH_MAX_LOGIN_ATTEMPTS` | - | `5` | ロックアウトまでの連続失敗回数。**ユーザー確認待ちの暫定値** |
| `AUTH_LOCKOUT_SECONDS` | - | `900` (15 分) | ロックアウト時間。**ユーザー確認待ちの暫定値** |
| `AUTH_PROTECTED_PATH_PREFIXES` | - | `/system-monitor,/api/system-monitor` | 認証必須とするパスの前方一致リスト (カンマ区切り) |
| `AUTH_COOKIE_SECURE` | - | `APP_ENV=local` 以外で `true` | Cookie の Secure 属性 |

`AUTH_SECRET_KEY` は次のように生成できる。

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

本番 (GCP) では `APP_PASSWORD_HASH` と `AUTH_SECRET_KEY` を Secret Manager へ登録し、
環境変数として注入すること。

## 3. 動作確認

| 操作 | 期待結果 |
| --- | --- |
| 未認証で保護対象 API へアクセス | `401` |
| 未認証で保護対象画面へアクセス | `/auth/login` へリダイレクト |
| `/auth/login` へ正しいパスワードを POST | `303` + セッション Cookie 発行 |
| 誤ったパスワードを POST | `401` (Cookie は発行されない) |
| `AUTH_MAX_LOGIN_ATTEMPTS` 回失敗後 | `429` (`AUTH_LOCKOUT_SECONDS` 経過まで) |
| `/auth/logout` を POST | Cookie 破棄。再び `401` |

自動テスト:

```bash
PYTHONPATH=. pytest tests/test_auth.py -v
```

## 4. 認証必須ルートの追加方法

```python
from fastapi import Depends
from python.web.auth import require_auth

@router.get("/api/system-monitor", dependencies=[Depends(require_auth)])
async def system_monitor():
    ...
```

パス前方一致で画面ごと保護したい場合は `AUTH_PROTECTED_PATH_PREFIXES` へ追加する。

## セキュリティ上の注意

- パスワード・Cookie 値・ハッシュはログへ出力しない実装になっている (`tests/test_auth.py` で検証)。
- セッション Cookie は `HttpOnly` / `SameSite=Lax` / (本番では) `Secure` 付きで発行される。
- 複数ユーザー管理・OAuth/OIDC・ロール権限は本チケットの対象外。
