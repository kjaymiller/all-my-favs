from importlib.metadata import version as _pkg_version
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import bookmarks, io, stats, tags, web

STATIC_DIR = Path(__file__).resolve().parent / "static"
APP_VERSION = _pkg_version("all-my-favs")

app = FastAPI(title="all-my-favs", version=APP_VERSION)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(web.router)
app.include_router(bookmarks.router)
app.include_router(tags.router)
app.include_router(stats.router)
app.include_router(io.router)


@app.exception_handler(StarletteHTTPException)
async def _redirect_unauth(request, exc):
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    from fastapi.responses import JSONResponse

    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}
