from datetime import datetime
from re import fullmatch

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

TAG_PATTERN = r"[a-z0-9][a-z0-9._-]*(:[a-z0-9][a-z0-9._-]*)*"


def _normalize_tag(raw: str) -> str:
    t = raw.strip().lower()
    if not fullmatch(TAG_PATTERN, t):
        raise ValueError(f"invalid tag: {raw!r} (expected wytcher-style tag:subtag)")
    return t


class BookmarkIn(BaseModel):
    url: HttpUrl
    title: str | None = None
    description: str | None = None
    notes: str | None = None
    source: str | None = None
    favicon_url: HttpUrl | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for raw in v:
            t = _normalize_tag(raw)
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out


class BookmarkUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    notes: str | None = None
    source: str | None = None
    favicon_url: HttpUrl | None = None
    tags: list[str] | None = None

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return [_normalize_tag(t) for t in v]


class BookmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    title: str | None
    description: str | None
    notes: str | None
    source: str | None
    favicon_url: str | None
    domain: str | None
    created_at: datetime
    updated_at: datetime
    tags: list[str]

    @field_validator("tags", mode="before")
    @classmethod
    def _flatten_tags(cls, v: object) -> list[str]:
        if isinstance(v, list) and v and not isinstance(v[0], str):
            return sorted(t.name for t in v)  # type: ignore[attr-defined]
        return list(v) if isinstance(v, list) else []


class TagCount(BaseModel):
    name: str
    count: int


class DomainCount(BaseModel):
    domain: str
    count: int


class DayCount(BaseModel):
    day: str
    count: int


class Stats(BaseModel):
    total: int
    added_today: int
    added_last_7d: int
    added_last_30d: int
    per_day: list[DayCount]
    top_domains: list[DomainCount]
    top_tags: list[TagCount]
