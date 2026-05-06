import json
from datetime import datetime
from typing import Any, Iterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_api_key
from app.db import get_session
from app.models import Bookmark
from app.schemas import BookmarkIn
from app.services import upsert_bookmark

router = APIRouter(prefix="/api", tags=["io"], dependencies=[Depends(require_api_key)])


def _row_to_jsonl(b: Bookmark) -> str:
    payload: dict[str, Any] = {
        "url": b.url,
        "title": b.title,
        "description": b.description,
        "notes": b.notes,
        "source": b.source,
        "favicon_url": b.favicon_url,
        "tags": sorted(t.name for t in b.tags),
        "created_at": b.created_at.isoformat() if b.created_at else None,
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"


def _stream_export(session: Session) -> Iterator[bytes]:
    stmt = (
        select(Bookmark)
        .options(selectinload(Bookmark.tags))
        .order_by(Bookmark.created_at.asc(), Bookmark.id.asc())
        .execution_options(yield_per=500)
    )
    for bm in session.scalars(stmt).unique():
        yield _row_to_jsonl(bm).encode("utf-8")


@router.get("/export")
def export_jsonl(session: Session = Depends(get_session)) -> StreamingResponse:
    filename = f"all-my-favs-{datetime.utcnow().date().isoformat()}.jsonl"
    return StreamingResponse(
        _stream_export(session),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_jsonl(
    request: Request, session: Session = Depends(get_session)
) -> dict[str, int]:
    body = await request.body()
    if not body:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty request body")

    imported = 0
    created = 0
    errors: list[dict[str, Any]] = []
    for lineno, raw in enumerate(body.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            payload = BookmarkIn.model_validate(obj)
        except (json.JSONDecodeError, ValidationError) as exc:
            errors.append({"line": lineno, "error": str(exc)})
            continue
        _, was_new = upsert_bookmark(
            session,
            url=str(payload.url),
            title=payload.title,
            description=payload.description,
            notes=payload.notes,
            source=payload.source,
            favicon_url=str(payload.favicon_url) if payload.favicon_url else None,
            tags=payload.tags,
        )
        imported += 1
        if was_new:
            created += 1

    if errors and imported == 0:
        session.rollback()
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"errors": errors[:25], "imported": 0},
        )
    session.commit()
    return {
        "imported": imported,
        "created": created,
        "updated": imported - created,
        "errors": len(errors),
    }
