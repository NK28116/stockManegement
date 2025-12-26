"""
シグナル生成APIのテストコード

概要:
    POST /api/signals/check エンドポイントのテストを実施する。
    正常系、異常系のテストケースを含む。

実行方法:
    pytest tests/test_signals_api.py -v
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# プロジェクトのルートディレクトリをsys.pathに追加
# tests/test_signals_api.py から見て .. がルート
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Debug: Print sys.path and project_root
print(f"DEBUG: project_root={project_root}")
print(f"DEBUG: sys.path={sys.path}")
print(f"DEBUG: ls project_root={os.listdir(project_root)}")

from python.db.database import get_db_session
from python.db.models import Base, SignalHistory
from python.web.app import app

# テスト用データベース接続（テスト環境用のDBを使用することを推奨）
TEST_DATABASE_URL = "sqlite:///./test_stock.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    テスト用データベースセッションを提供するフィクスチャ

    各テスト関数の実行前にテーブルを作成し、
    実行後にクリーンアップを行う。
    """
    # テーブル作成
    Base.metadata.create_all(bind=test_engine)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # テーブル削除（クリーンアップ）
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """
    FastAPIのTestClientを提供するフィクスチャ

    テスト用DBセッションを使用するようにアプリケーションを設定する。
    """
    from contextlib import contextmanager
    import python.db.database as db_module
    import python.web.api.signals as signals_module
    
    # Save the original get_db_session
    original_get_db_session = db_module.get_db_session
    
    # Create a replacement that yields the test session
    @contextmanager
    def override_get_db_session():
        try:
            yield db_session
        except Exception:
            db_session.rollback()
            raise
    
    # Monkey patch the function in both modules
    db_module.get_db_session = override_get_db_session
    signals_module.get_db_session = override_get_db_session
    
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        # Restore the original function
        db_module.get_db_session = original_get_db_session
        signals_module.get_db_session = original_get_db_session


# ================================================================================
# 1. 正常系テスト
# ================================================================================

def test_signal_check_success(client, db_session):
    """
    正常系テスト: 存在する銘柄コードでシグナルチェックを実行

    テストケース:
        - 存在する銘柄コード（例: "7203.T" トヨタ自動車）でAPIを呼び出す

    期待する結果:
        - HTTPステータスコード 200 OK が返ること
        - レスポンスJSONに必要なフィールドが全て含まれること
        - signal の値が 'BUY', 'SELL', 'HOLD' のいずれかであること
        - DBに1件のレコードが追加されること
    """
    # リクエストデータ
    request_data = {"stock_code": "7203.T"}

    # APIを呼び出し
    response = client.post("/api/signals/check", json=request_data)

    # ステータスコードの確認
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # セッションをリフレッシュしてコミットされたデータを取得
    db_session.expire_all()

    # レスポンスJSONの取得
    response_json = response.json()

    # 必須フィールドの存在確認
    assert "stock_code" in response_json, "stock_code is missing in response"
    assert "signal" in response_json, "signal is missing in response"
    assert "price" in response_json, "price is missing in response"
    assert "reason" in response_json, "reason is missing in response"
    assert "rule_version" in response_json, "rule_version is missing in response"
    assert "timestamp" in response_json, "timestamp is missing in response"

    # stock_code の値の確認
    assert response_json["stock_code"] == "7203.T", "stock_code mismatch"

    # signal の値が有効かどうか確認
    valid_signals = ["BUY", "SELL", "HOLD"]
    assert response_json["signal"] in valid_signals, \
        f"signal must be one of {valid_signals}, got {response_json['signal']}"

    # price が正の数値であることを確認
    assert isinstance(response_json["price"], (int, float)), "price must be a number"
    assert response_json["price"] > 0, "price must be positive"

    # DBレコードの確認
    records = db_session.query(SignalHistory).filter_by(stock_code="7203.T").all()
    assert len(records) >= 1, "Expected at least 1 record in signal_history table"

    # 最新レコードの内容確認
    latest_record = records[-1]
    assert latest_record.stock_code == "7203.T"
    assert latest_record.signal == response_json["signal"]
    assert float(latest_record.price) == response_json["price"]
    assert latest_record.reason == response_json["reason"]
    assert latest_record.rule_version == response_json["rule_version"]


def test_signal_check_multiple_stocks(client, db_session):
    """
    正常系テスト: 複数の銘柄で連続してシグナルチェックを実行

    テストケース:
        - 複数の銘柄コードで連続してAPIを呼び出す

    期待する結果:
        - すべてのリクエストが成功すること
        - DBに複数のレコードが保存されること
    """
    stock_codes = ["7203.T", "6758.T", "9984.T"]  # トヨタ、ソニー、ソフトバンク

    for stock_code in stock_codes:
        request_data = {"stock_code": stock_code}
        response = client.post("/api/signals/check", json=request_data)

        # 各リクエストが成功することを確認
        assert response.status_code == 200, \
            f"Failed for {stock_code}: status {response.status_code}"

        response_json = response.json()
        assert response_json["stock_code"] == stock_code

    # セッションをリフレッシュしてコミットされたデータを取得
    db_session.expire_all()

    # DBに3件のレコードが保存されていることを確認
    total_records = db_session.query(SignalHistory).count()
    assert total_records >= 3, f"Expected at least 3 records, got {total_records}"


# ================================================================================
# 2. 異常系テスト
# ================================================================================

def test_signal_check_invalid_stock_code(client):
    """
    異常系テスト: 存在しない銘柄コードでシグナルチェックを実行

    テストケース:
        - 存在しない銘柄コード（例: "9999.T"）でAPIを呼び出す

    期待する結果:
        - HTTPステータスコード 404 Not Found または 500 Internal Server Error が返ること
    """
    # 存在しない銘柄コード
    request_data = {"stock_code": "INVALID999.T"}

    # APIを呼び出し
    response = client.post("/api/signals/check", json=request_data)

    # ステータスコードが404または500であることを確認
    assert response.status_code in [404, 500], \
        f"Expected 404 or 500, got {response.status_code}"

    # エラーメッセージが含まれていることを確認
    response_json = response.json()
    assert "detail" in response_json, "Error response should contain 'detail' field"


def test_signal_check_missing_stock_code(client):
    """
    異常系テスト: stock_code が欠落しているリクエスト

    テストケース:
        - リクエストボディに stock_code が含まれていない

    期待する結果:
        - HTTPステータスコード 422 Unprocessable Entity が返ること
    """
    # stock_code が欠落したリクエスト
    request_data = {}

    # APIを呼び出し
    response = client.post("/api/signals/check", json=request_data)

    # バリデーションエラー（422）が返ることを確認
    assert response.status_code == 422, \
        f"Expected 422 (validation error), got {response.status_code}"

    # エラー詳細が含まれていることを確認
    response_json = response.json()
    assert "detail" in response_json, "Validation error should contain 'detail' field"


def test_signal_check_empty_stock_code(client):
    """
    異常系テスト: stock_code が空文字列のリクエスト

    テストケース:
        - stock_code に空文字列を指定する

    期待する結果:
        - HTTPステータスコード 422 Unprocessable Entity または 404/500 が返ること
    """
    # stock_code が空文字列のリクエスト
    request_data = {"stock_code": ""}

    # APIを呼び出し
    response = client.post("/api/signals/check", json=request_data)

    # エラーステータスコードが返ることを確認
    assert response.status_code in [422, 404, 500], \
        f"Expected error status code (422/404/500), got {response.status_code}"


def test_signal_check_invalid_json(client):
    """
    異常系テスト: 不正なJSON形式のリクエスト

    テストケース:
        - 不正なJSON形式でリクエストを送信する

    期待する結果:
        - HTTPステータスコード 422 Unprocessable Entity が返ること
    """
    # 不正なJSON文字列
    invalid_json = "this is not json"

    # APIを呼び出し（Content-Typeを明示的に指定）
    response = client.post(
        "/api/signals/check",
        data=invalid_json,
        headers={"Content-Type": "application/json"}
    )

    # エラーステータスコードが返ることを確認
    assert response.status_code == 422, \
        f"Expected 422 (validation error), got {response.status_code}"


# ================================================================================
# 3. エッジケーステスト
# ================================================================================

def test_signal_check_special_characters_in_code(client):
    """
    エッジケーステスト: 特殊文字を含む銘柄コード

    テストケース:
        - 特殊文字を含む銘柄コードでAPIを呼び出す

    期待する結果:
        - エラーステータスコード（404または500）が返ること
    """
    # 特殊文字を含む銘柄コード
    request_data = {"stock_code": "!@#$%^&*()"}

    # APIを呼び出し
    response = client.post("/api/signals/check", json=request_data)

    # エラーステータスコードが返ることを確認
    assert response.status_code in [404, 500, 422], \
        f"Expected error status code, got {response.status_code}"


def test_signal_check_very_long_stock_code(client):
    """
    エッジケーステスト: 非常に長い銘柄コード

    テストケース:
        - 異常に長い文字列を銘柄コードとして送信する

    期待する結果:
        - エラーステータスコード（404、500、または422）が返ること
    """
    # 非常に長い銘柄コード
    request_data = {"stock_code": "A" * 1000}

    # APIを呼び出し
    response = client.post("/api/signals/check", json=request_data)

    # エラーステータスコードが返ることを確認
    assert response.status_code in [404, 500, 422], \
        f"Expected error status code, got {response.status_code}"


# ================================================================================
# テスト実行時の追加設定
# ================================================================================

if __name__ == "__main__":
    # pytestをプログラムから実行する場合
    pytest.main([__file__, "-v", "--tb=short"])
