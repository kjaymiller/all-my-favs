from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Bookmark, Tag


def extract_domain(url: str) -> str | None:
    host = urlparse(url).hostname
    if not host:
        return None
    return host.lower().removeprefix("www.")


def get_or_create_tags(session: Session, names: list[str]) -> list[Tag]:
    if not names:
        return []
    existing = {
        t.name: t for t in session.scalars(select(Tag).where(Tag.name.in_(names))).all()
    }
    out: list[Tag] = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            session.add(tag)
            existing[name] = tag
        out.append(tag)
    session.flush()
    return out


def upsert_bookmark(session: Session, *, url: str, **fields) -> tuple[Bookmark, bool]:
    tags = fields.pop("tags", None)
    bm = session.scalar(
        select(Bookmark).options(selectinload(Bookmark.tags)).where(Bookmark.url == url)
    )
    created = False
    if bm is None:
        bm = Bookmark(url=url, domain=extract_domain(url))
        session.add(bm)
        created = True
    for k, v in fields.items():
        if v is not None:
            setattr(bm, k, v)
    if tags is not None:
        bm.tags = get_or_create_tags(session, tags)
    session.flush()
    return bm, created
