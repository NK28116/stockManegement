#!/usr/bin/env python3
"""APP_PASSWORD_HASH 用のハッシュを生成する (PRIDEV-481)。

使い方:
    python scripts/hash_password.py
    # プロンプトへパスワードを入力すると、.env / Secret Manager へ設定する値を出力する

パスワードは引数で渡さない (シェル履歴へ残るため)。
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from python.web.auth import hash_password  # noqa: E402


def main() -> int:
    password = getpass.getpass("パスワード: ")
    if not password:
        print("パスワードが空です", file=sys.stderr)
        return 1
    if password != getpass.getpass("パスワード (確認): "):
        print("パスワードが一致しません", file=sys.stderr)
        return 1

    print("\n以下を .env または Secret Manager へ設定してください:\n")
    print(f"APP_PASSWORD_HASH={hash_password(password)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
