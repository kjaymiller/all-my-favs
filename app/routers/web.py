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
from app.services import fetch_url_metadata, upsert_bookmark

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


@router.post("/bookmarks/{bookmark_id}/delete", dependencies=[Depends(require_api_key)])
def delete_via_form(bookmark_id: int, session: Session = Depends(get_session)) -> Response:
    bm = session.get(Bookmark, bookmark_id)
    if bm is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "bookmark not found")
    session.delete(bm)
    session.commit()
    return RedirectResponse(url="/bookmarks", status_code=status.HTTP_303_SEE_OTHER)
