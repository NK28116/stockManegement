"""FastMCP server exposing watchlist / note / portfolio-summary tools.

Claude / ChatGPT / Gemini が共通で呼び出せる MCP ツールを登録する。
DB アクセスは ``python.web.services.watchlist_service`` に委譲しており、
将来 FastAPI を Go (Gin) に移植する場合も同仕様を再実装すれば足りる。
"""
from typing import Optional

from mcp.server.fastmcp import FastMCP

from python.db.database import get_db_session
from python.web.services import watchlist_service

mcp = FastMCP("stockManegement")


@mcp.tool()
def list_watchlist() -> list[dict]:
    """監視銘柄 (watchlist) の一覧を返す。priority 降順、追加日時の新しい順。"""
    with get_db_session() as session:
        return watchlist_service.list_watchlist(session)


@mcp.tool()
def add_to_watchlist(
    code: str, tags: Optional[str] = None, priority: int = 0
) -> dict:
    """監視銘柄を追加する。既に存在すれば tags / priority を上書きする。

    User confirmation required before invoking: this writes to the DB.
    """
    with get_db_session() as session:
        return watchlist_service.add_to_watchlist(
            session, code=code, tags=tags, priority=priority
        )


@mcp.tool()
def remove_from_watchlist(code: str) -> dict:
    """監視銘柄から code を削除する。

    User confirmation required before invoking: this writes to the DB.
    """
    with get_db_session() as session:
        removed = watchlist_service.remove_from_watchlist(session, code)
        return {"code": code, "removed": removed}


@mcp.tool()
def list_notes(code: str) -> list[dict]:
    """指定銘柄コードに紐づくメモ一覧を新しい順で返す。"""
    with get_db_session() as session:
        return watchlist_service.list_notes(session, code)


@mcp.tool()
def add_note(code: str, body: str) -> dict:
    """銘柄にメモを追加する。

    User confirmation required before invoking: this writes to the DB.
    """
    with get_db_session() as session:
        return watchlist_service.add_note(session, code=code, body=body)


@mcp.tool()
def update_note(note_id: int, body: str) -> dict:
    """既存メモの本文を更新する。

    User confirmation required before invoking: this writes to the DB.
    """
    with get_db_session() as session:
        updated = watchlist_service.update_note(session, note_id, body)
        if updated is None:
            return {"id": note_id, "updated": False, "error": "note not found"}
        return updated


@mcp.tool()
def delete_note(note_id: int) -> dict:
    """メモを削除する。

    User confirmation required before invoking: this writes to the DB.
    """
    with get_db_session() as session:
        removed = watchlist_service.delete_note(session, note_id)
        return {"id": note_id, "removed": removed}


@mcp.tool()
def get_portfolio_summary() -> dict:
    """ポートフォリオの総資産額・評価損益を返す (参照のみ)。"""
    from python.web.services.analytics import AnalyticsService

    resp = AnalyticsService().calculate_total_performance()
    if hasattr(resp, "model_dump"):
        return resp.model_dump()
    if hasattr(resp, "dict"):
        return resp.dict()
    return dict(resp)
