"""
Watchlist / Stock Note API エンドポイント

監視銘柄 (Watchlist) とメモ (StockNote) の CRUD。
ビジネスロジックは python/web/services/watchlist_service.py に委譲する。
"""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from python.db.database import get_db_session
from python.utils.logger import get_logger
from python.web.services import watchlist_service

logger = get_logger("web", "watchlist")

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    code: str
    tags: Optional[str] = None
    priority: int = 0


class NoteCreateRequest(BaseModel):
    code: str
    body: str


class NoteUpdateRequest(BaseModel):
    body: str


@router.get("")
def get_watchlist():
    with get_db_session() as session:
        return watchlist_service.list_watchlist(session)


@router.post("")
def add_watchlist(req: WatchlistAddRequest):
    with get_db_session() as session:
        return watchlist_service.add_to_watchlist(
            session, code=req.code, tags=req.tags, priority=req.priority
        )


@router.delete("/{code}")
def delete_watchlist(code: str):
    with get_db_session() as session:
        removed = watchlist_service.remove_from_watchlist(session, code)
        if not removed:
            raise HTTPException(status_code=404, detail="code not found in watchlist")
        return {"code": code, "removed": True}


@router.get("/notes/{code}")
def get_notes(code: str):
    with get_db_session() as session:
        return watchlist_service.list_notes(session, code)


@router.post("/notes")
def create_note(req: NoteCreateRequest):
    with get_db_session() as session:
        return watchlist_service.add_note(session, code=req.code, body=req.body)


@router.put("/notes/{note_id}")
def update_note(note_id: int, req: NoteUpdateRequest):
    with get_db_session() as session:
        updated = watchlist_service.update_note(session, note_id, req.body)
        if updated is None:
            raise HTTPException(status_code=404, detail="note not found")
        return updated


@router.delete("/notes/{note_id}")
def delete_note(note_id: int):
    with get_db_session() as session:
        removed = watchlist_service.delete_note(session, note_id)
        if not removed:
            raise HTTPException(status_code=404, detail="note not found")
        return {"id": note_id, "removed": True}
