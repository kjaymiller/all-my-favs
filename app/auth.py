import hmac

from fastapi import Cookie, Header, HTTPException, Query, status

from app.config import settings


def _check(token: str | None) -> bool:
    return bool(token) and hmac.compare_digest(token, settings.api_key)


def require_api_key(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    api_key_query: str | None = Query(default=None, alias="api_key"),
    session: str | None = Cookie(default=None, alias=settings.cookie_name),
) -> None:
    bearer = None
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    for token in (bearer, x_api_key, api_key_query, session):
        if _check(token):
            return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="missing or invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )
