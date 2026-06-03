"""Bearer token auth middleware for the MCP HTTP transport.

環境変数 ``MCP_API_KEY`` が設定されている場合のみ有効化する。
未設定時は常にリクエストを通過させ、起動ログで警告する。
"""
import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Authorization: Bearer <MCP_API_KEY> を検証する Starlette ミドルウェア。"""

    def __init__(self, app, api_key: str):
        super().__init__(app)
        self._expected = api_key

    async def dispatch(self, request: Request, call_next):
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return JSONResponse(
                {"error": "missing Authorization: Bearer header"}, status_code=401
            )
        token = header.split(" ", 1)[1].strip()
        if token != self._expected:
            return JSONResponse({"error": "invalid api key"}, status_code=401)
        return await call_next(request)


def get_api_key() -> str | None:
    """環境変数から API キーを読む。未設定なら None。"""
    key = os.getenv("MCP_API_KEY")
    if key is None or key.strip() == "":
        return None
    return key.strip()
