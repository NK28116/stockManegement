"""
Watchlist Service

監視銘柄 (Watchlist) と銘柄メモ (StockNote) のドメインロジック。
FastAPI ルートと MCP サーバーの両方から呼び出される純粋関数群。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from python.db.models import StockNote, Watchlist


def _watchlist_to_dict(row: Watchlist) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "tags": row.tags,
        "priority": row.priority,
        "added_at": row.added_at.isoformat() if row.added_at else None,
    }


def _note_to_dict(row: StockNote) -> dict:
    return {
        "id": row.id,
        "code": row.code,
        "body": row.body,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_watchlist(session: Session) -> list[dict]:
    rows = (
        session.query(Watchlist)
        .order_by(Watchlist.priority.desc(), Watchlist.added_at.desc())
        .all()
    )
    return [_watchlist_to_dict(r) for r in rows]


def add_to_watchlist(
    session: Session,
    code: str,
    tags: Optional[str] = None,
    priority: int = 0,
) -> dict:
    existing = session.query(Watchlist).filter(Watchlist.code == code).one_or_none()
    if existing is not None:
        existing.tags = tags if tags is not None else existing.tags
        existing.priority = priority
        session.commit()
        session.refresh(existing)
        return _watchlist_to_dict(existing)

    row = Watchlist(code=code, tags=tags, priority=priority)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _watchlist_to_dict(row)


def remove_from_watchlist(session: Session, code: str) -> bool:
    row = session.query(Watchlist).filter(Watchlist.code == code).one_or_none()
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def list_notes(session: Session, code: str) -> list[dict]:
    rows = (
        session.query(StockNote)
        .filter(StockNote.code == code)
        .order_by(StockNote.created_at.desc())
        .all()
    )
    return [_note_to_dict(r) for r in rows]


def add_note(session: Session, code: str, body: str) -> dict:
    row = StockNote(code=code, body=body)
    session.add(row)
    session.commit()
    session.refresh(row)
    return _note_to_dict(row)


def update_note(session: Session, note_id: int, body: str) -> Optional[dict]:
    row = session.query(StockNote).filter(StockNote.id == note_id).one_or_none()
    if row is None:
        return None
    row.body = body
    row.updated_at = datetime.now()
    session.commit()
    session.refresh(row)
    return _note_to_dict(row)


def delete_note(session: Session, note_id: int) -> bool:
    row = session.query(StockNote).filter(StockNote.id == note_id).one_or_none()
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True
