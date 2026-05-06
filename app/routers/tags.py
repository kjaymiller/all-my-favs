from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import require_api_key
from app.db import get_session
from app.models import Tag, bookmark_tags
from app.schemas import TagCount

router = APIRouter(prefix="/api/tags", tags=["tags"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[TagCount])
def list_tags(session: Session = Depends(get_session)) -> list[TagCount]:
    stmt = (
        select(Tag.name, func.count(bookmark_tags.c.bookmark_id).label("count"))
        .join(bookmark_tags, bookmark_tags.c.tag_id == Tag.id, isouter=True)
        .group_by(Tag.name)
        .order_by(func.count(bookmark_tags.c.bookmark_id).desc(), Tag.name.asc())
    )
    return [TagCount(name=row.name, count=row.count) for row in session.execute(stmt)]
