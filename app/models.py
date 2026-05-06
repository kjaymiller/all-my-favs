from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

bookmark_tags = Table(
    "bookmark_tags",
    Base.metadata,
    Column("bookmark_id", ForeignKey("bookmarks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)

    bookmarks: Mapped[list["Bookmark"]] = relationship(
        secondary=bookmark_tags, back_populates="tags"
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text)
    favicon_url: Mapped[str | None] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(Text, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "setweight(to_tsvector('english', coalesce(title,'')), 'A') || "
            "setweight(to_tsvector('english', coalesce(description,'')), 'B') || "
            "setweight(to_tsvector('english', coalesce(url,'')), 'C') || "
            "setweight(to_tsvector('english', coalesce(notes,'')), 'D')",
            persisted=True,
        ),
    )

    tags: Mapped[list[Tag]] = relationship(secondary=bookmark_tags, back_populates="bookmarks")

    __table_args__ = (
        Index("bookmarks_search_idx", "search_vector", postgresql_using="gin"),
        Index("bookmarks_created_at_idx", "created_at"),
    )
