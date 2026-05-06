from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_api_key
from app.db import get_session
from app.models import Bookmark, Tag
from app.schemas import BookmarkIn, BookmarkOut, BookmarkUpdate
from app.services import upsert_bookmark

router = APIRouter(prefix="/api/bookmarks", tags=["bookmarks"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[BookmarkOut])
def list_bookmarks(
    q: str | None = Query(default=None, description="full-text search"),
    tag: list[str] | None = Query(default=None),
    domain: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> list[Bookmark]:
    stmt = select(Bookmark).options(selectinload(Bookmark.tags))
    if q:
        stmt = stmt.where(Bookmark.search_vector.op("@@")(func.websearch_to_tsquery("english", q)))
        stmt = stmt.order_by(
            func.ts_rank(Bookmark.search_vector, func.websearch_to_tsquery("english", q)).desc()
        )
    else:
        stmt = stmt.order_by(Bookmark.created_at.desc())
    if domain:
        stmt = stmt.where(Bookmark.domain == domain.lower())
    if tag:
        for t in tag:
            stmt = stmt.where(Bookmark.tags.any(Tag.name == t.lower()))
    stmt = stmt.limit(limit).offset(offset)
    return list(session.scalars(stmt).unique().all())


@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
def create_bookmark(payload: BookmarkIn, session: Session = Depends(get_session)) -> Bookmark:
    bm, _ = upsert_bookmark(
        session,
        url=str(payload.url),
        title=payload.title,
        description=payload.description,
        notes=payload.notes,
        source=payload.source,
        favicon_url=str(payload.favicon_url) if payload.favicon_url else None,
        tags=payload.tags,
    )
    session.commit()
    session.refresh(bm)
    return bm


@router.get("/{bookmark_id}", response_model=BookmarkOut)
def get_bookmark(bookmark_id: int, session: Session = Depends(get_session)) -> Bookmark:
    bm = session.get(Bookmark, bookmark_id)
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")
    return bm


@router.patch("/{bookmark_id}", response_model=BookmarkOut)
def update_bookmark(
    bookmark_id: int,
    payload: BookmarkUpdate,
    session: Session = Depends(get_session),
) -> Bookmark:
    bm = session.get(Bookmark, bookmark_id)
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")
    bm, _ = upsert_bookmark(
        session,
        url=bm.url,
        title=payload.title,
        description=payload.description,
        notes=payload.notes,
        source=payload.source,
        favicon_url=str(payload.favicon_url) if payload.favicon_url else None,
        tags=payload.tags,
    )
    session.commit()
    session.refresh(bm)
    return bm


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bookmark(bookmark_id: int, session: Session = Depends(get_session)) -> None:
    bm = session.get(Bookmark, bookmark_id)
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")
    session.delete(bm)
    session.commit()
