from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.db import get_session
from app.models import Bookmark, Tag, bookmark_tags
from app.schemas import DayCount, DomainCount, Stats, TagCount

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(require_api_key)])


def compute_stats(session: Session, *, days: int = 30, top: int = 10) -> Stats:
    today = date.today()
    start = today - timedelta(days=days - 1)

    total = session.scalar(select(func.count(Bookmark.id))) or 0

    def added_since(d: date) -> int:
        return session.scalar(
            select(func.count(Bookmark.id)).where(func.date(Bookmark.created_at) >= d)
        ) or 0

    added_today = added_since(today)
    added_7d = added_since(today - timedelta(days=6))
    added_30d = added_since(today - timedelta(days=29))

    day_col = func.date(Bookmark.created_at).label("day")
    rows = session.execute(
        select(day_col, func.count(Bookmark.id))
        .where(func.date(Bookmark.created_at) >= start)
        .group_by(day_col)
        .order_by(day_col)
    ).all()
    by_day = {row[0].isoformat(): row[1] for row in rows}
    per_day = [
        DayCount(day=(start + timedelta(days=i)).isoformat(),
                 count=by_day.get((start + timedelta(days=i)).isoformat(), 0))
        for i in range(days)
    ]

    top_domains = [
        DomainCount(domain=row.domain, count=row.count)
        for row in session.execute(
            select(Bookmark.domain, func.count(Bookmark.id).label("count"))
            .where(Bookmark.domain.isnot(None))
            .group_by(Bookmark.domain)
            .order_by(func.count(Bookmark.id).desc())
            .limit(top)
        )
        if row.domain
    ]

    top_tags = [
        TagCount(name=row.name, count=row.count)
        for row in session.execute(
            select(Tag.name, func.count(bookmark_tags.c.bookmark_id).label("count"))
            .join(bookmark_tags, bookmark_tags.c.tag_id == Tag.id)
            .group_by(Tag.name)
            .order_by(func.count(bookmark_tags.c.bookmark_id).desc())
            .limit(top)
        )
    ]

    return Stats(
        total=total,
        added_today=added_today,
        added_last_7d=added_7d,
        added_last_30d=added_30d,
        per_day=per_day,
        top_domains=top_domains,
        top_tags=top_tags,
    )


@router.get("", response_model=Stats)
def get_stats(
    days: int = Query(default=30, ge=1, le=365),
    top: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> Stats:
    return compute_stats(session, days=days, top=top)
