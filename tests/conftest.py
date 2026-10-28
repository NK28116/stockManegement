"""テスト全体の共通設定。

認証は APP_ENV が未設定だと本番扱いとなり、APP_PASSWORD_HASH /
AUTH_SECRET_KEY 未設定で起動が失敗する (フェイルクローズ / PRIDEV-521)。
テストは開発環境として動かすため、テストモジュールの import より前に
APP_ENV を設定する。
"""

import os

os.environ.setdefault("APP_ENV", "test")
