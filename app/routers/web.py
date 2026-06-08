from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.auth import require_api_key
from app.config import settings
from app.db import get_session
from app.models import Bookmark, Tag
from app.routers.stats import compute_stats
from app.services import (
    extract_domain,
    fetch_url_metadata,
    get_or_create_tags,
    upsert_bookmark,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
try:
    templates.env.globals["app_version"] = _pkg_version("all-my-favs")
except PackageNotFoundError:
    templates.env.globals["app_version"] = "dev"
templates.env.globals["source_url"] = "https://github.com/kjaymiller/all-my-favs"

router = APIRouter(tags=["web"])


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/") -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html", {"next": next, "error": None})


@router.post("/login")
def login_submit(
    request: Request, api_key: str = Form(...), next: str = Form("/")
) -> Response:
    import hmac

    if not hmac.compare_digest(api_key, settings.api_key):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"next": next, "error": "Invalid key"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    resp = RedirectResponse(url=next or "/", status_code=status.HTTP_303_SEE_OTHER)
    resp.set_cookie(
        settings.cookie_name,
        api_key,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )
    return resp


@router.post("/logout")
def logout() -> Response:
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(settings.cookie_name, path="/")
    return resp


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_api_key)])
def dashboard(
    request: Request,
    added: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    stats = compute_stats(session, days=30, top=10)
    recent = list(
        session.scalars(
            select(Bookmark)
            .options(selectinload(Bookmark.tags))
            .order_by(Bookmark.created_at.desc())
            .limit(10)
        ).all()
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"stats": stats, "recent": recent, "added": added, "error": error},
    )


@router.post("/bookmarks/quick-add", dependencies=[Depends(require_api_key)])
def quick_add(
    url: str = Form(...),
    tags: str = Form(default=""),
    session: Session = Depends(get_session),
) -> Response:
    url = url.strip()
    if not url:
        return RedirectResponse(url="/?error=missing+url", status_code=status.HTTP_303_SEE_OTHER)

    meta: dict[str, str | None] = {"title": None, "description": None, "favicon_url": None}
    try:
        meta = fetch_url_metadata(url)
    except (httpx.HTTPError, ValueError):
        pass

    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
    upsert_bookmark(
        session,
        url=url,
        title=meta.get("title"),
        description=meta.get("description"),
        favicon_url=meta.get("favicon_url"),
        source="web-quick",
        tags=tag_list or None,
    )
    session.commit()
    return RedirectResponse(url="/?added=1", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/bookmarks", response_class=HTMLResponse, dependencies=[Depends(require_api_key)])
def bookmarks_page(
    request: Request,
    q: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    page_size = 25
    stmt = select(Bookmark).options(selectinload(Bookmark.tags))
    if q:
        stmt = stmt.where(Bookmark.search_vector.op("@@")(func.websearch_to_tsquery("english", q)))
        stmt = stmt.order_by(
            func.ts_rank(Bookmark.search_vector, func.websearch_to_tsquery("english", q)).desc()
        )
    else:
        stmt = stmt.order_by(Bookmark.created_at.desc())
    if tag:
        stmt = stmt.where(Bookmark.tags.any(Tag.name == tag.lower()))
    if domain:
        stmt = stmt.where(Bookmark.domain == domain.lower())
    items = list(
        session.scalars(stmt.limit(page_size).offset((page - 1) * page_size)).unique().all()
    )
    total = session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    return templates.TemplateResponse(
        request,
        "bookmarks.html",
        {
            "items": items,
            "q": q or "",
            "tag": tag or "",
            "domain": domain or "",
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": page * page_size < total,
        },
    )


@router.post("/bookmarks/new", dependencies=[Depends(require_api_key)])
def create_via_form(
    url: str = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    tags: str = Form(default=""),
    session: Session = Depends(get_session),
) -> Response:
    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
    upsert_bookmark(
        session,
        url=url,
        title=title or None,
        description=description or None,
        notes=notes or None,
        source="web",
        tags=tag_list,
    )
    session.commit()
    return RedirectResponse(url="/bookmarks", status_code=status.HTTP_303_SEE_OTHER)


def _edit_context(
    bm: Bookmark,
    *,
    form: dict[str, str] | None = None,
    error: str | None = None,
    notice: str | None = None,
    overwrite: bool = False,
) -> dict[str, object]:
    values = {
        "url": bm.url,
        "title": bm.title or "",
        "description": bm.description or "",
        "notes": bm.notes or "",
        "tags": ", ".join(t.name for t in bm.tags),
        "favicon_url": bm.favicon_url or "",
    }
    if form is not None:
        values.update(form)
    return {"b": bm, "form": values, "error": error, "notice": notice, "overwrite": overwrite}


@router.get(
    "/bookmarks/{bookmark_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(require_api_key)],
)
def edit_form(
    request: Request,
    bookmark_id: int,
    error: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    bm = session.scalar(
        select(Bookmark).options(selectinload(Bookmark.tags)).where(Bookmark.id == bookmark_id)
    )
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")
    return templates.TemplateResponse(request, "edit.html", _edit_context(bm, error=error))


@router.post(
    "/bookmarks/{bookmark_id}/refresh",
    response_class=HTMLResponse,
    dependencies=[Depends(require_api_key)],
)
def refresh_metadata(
    request: Request,
    bookmark_id: int,
    url: str = Form(...),
    title: str = Form(default=""),
    description: str = Form(default=""),
    notes: str = Form(default=""),
    tags: str = Form(default=""),
    favicon_url: str = Form(default=""),
    overwrite: bool = Form(default=False),
    session: Session = Depends(get_session),
) -> HTMLResponse:
    bm = session.scalar(
        select(Bookmark).options(selectinload(Bookmark.tags)).where(Bookmark.id == bookmark_id)
    )
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")

    form = {
        "url": url,
        "title": title,
        "description": description,
        "notes": notes,
        "tags": tags,
        "favicon_url": favicon_url,
    }
    try:
        meta = fetch_url_metadata(url.strip())
    except (httpx.HTTPError, ValueError):
        return templates.TemplateResponse(
            request,
            "edit.html",
            _edit_context(
                bm, form=form, overwrite=overwrite, error="Could not fetch metadata from that URL."
            ),
        )

    def merge(field: str, current: str) -> str:
        fetched = (meta.get(field) or "").strip()
        if fetched and (overwrite or not current.strip()):
            return fetched
        return current

    changed = []
    for field, current in (("title", title), ("description", description), ("favicon_url", favicon_url)):
        merged = merge(field, current)
        form[field] = merged
        if merged != current:
            changed.append(field)
    notice = (
        f"Pulled metadata — updated {', '.join(changed)}." if changed else "No new metadata found."
    )
    return templates.TemplateResponse(
        request,
        "edit.html",
        _edit_context(bm, form=form, overwrite=overwrite, notice=notice),
    )


@router.post("/bookmarks/{bookmark_id}/edit", dependencies=[Depends(require_api_key)])
def edit_via_form(
    bookmark_id: int,
    url: str = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    notes: str | None = Form(default=None),
    tags: str = Form(default=""),
    favicon_url: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> Response:
    bm = session.scalar(
        select(Bookmark).options(selectinload(Bookmark.tags)).where(Bookmark.id == bookmark_id)
    )
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")

    url = url.strip()
    if not url:
        return RedirectResponse(
            url=f"/bookmarks/{bookmark_id}/edit?error=missing+url",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if url != bm.url:
        clash = session.scalar(select(Bookmark.id).where(Bookmark.url == url))
        if clash is not None:
            return RedirectResponse(
                url=f"/bookmarks/{bookmark_id}/edit?error=another+bookmark+already+uses+that+URL",
                status_code=status.HTTP_303_SEE_OTHER,
            )
        bm.url = url
        bm.domain = extract_domain(url)

    bm.title = (title or "").strip() or None
    bm.description = (description or "").strip() or None
    bm.notes = (notes or "").strip() or None
    bm.favicon_url = (favicon_url or "").strip() or None
    bm.tags = get_or_create_tags(session, [t.strip().lower() for t in tags.split(",") if t.strip()])
    session.commit()
    return RedirectResponse(url="/bookmarks", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/bookmarks/{bookmark_id}/delete", dependencies=[Depends(require_api_key)])
def delete_via_form(bookmark_id: int, session: Session = Depends(get_session)) -> Response:
    bm = session.get(Bookmark, bookmark_id)
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")
    session.delete(bm)
    session.commit()
    return RedirectResponse(url="/bookmarks", status_code=status.HTTP_303_SEE_OTHER)
