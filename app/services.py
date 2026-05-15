from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx
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


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title: str | None = None
        self.icon: str | None = None
        self._in_title = False
        self._title_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            content = a.get("content")
            if key and content and key not in self.meta:
                self.meta[key] = content
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if "icon" in rel.split() and a.get("href") and not self.icon:
                self.icon = a["href"]

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_chunks.append(data)

    def finish(self) -> None:
        if self._title_chunks:
            self.title = "".join(self._title_chunks).strip() or None


def fetch_url_metadata(url: str, *, timeout: float = 8.0) -> dict[str, str | None]:
    headers = {"User-Agent": "all-my-favs/0.1 (+bookmark metadata fetcher)"}
    with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
        resp = client.get(url)
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "html" not in ctype.lower():
            return {"title": None, "description": None, "favicon_url": None}
        text = resp.text[:512_000]
        final_url = str(resp.url)

    parser = _MetaParser()
    try:
        parser.feed(text)
    except Exception:
        pass
    parser.finish()

    m = parser.meta
    title = m.get("og:title") or m.get("twitter:title") or parser.title
    description = m.get("og:description") or m.get("twitter:description") or m.get("description")
    favicon = m.get("og:image") or parser.icon
    if favicon:
        favicon = urljoin(final_url, favicon)

    return {
        "title": (title or "").strip() or None,
        "description": (description or "").strip() or None,
        "favicon_url": favicon,
    }
