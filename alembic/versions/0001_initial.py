"""initial schema: bookmarks, tags, bookmark_tags, FTS

Revision ID: 0001
Revises:
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
    )
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("url", sa.Text, nullable=False, unique=True),
        sa.Column("title", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("source", sa.Text),
        sa.Column("favicon_url", sa.Text),
        sa.Column("domain", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "search_vector",
            TSVECTOR,
            sa.Computed(
                "setweight(to_tsvector('english', coalesce(title,'')), 'A') || "
                "setweight(to_tsvector('english', coalesce(description,'')), 'B') || "
                "setweight(to_tsvector('english', coalesce(url,'')), 'C') || "
                "setweight(to_tsvector('english', coalesce(notes,'')), 'D')",
                persisted=True,
            ),
        ),
    )
    op.create_index("ix_bookmarks_domain", "bookmarks", ["domain"])
    op.create_index("bookmarks_created_at_idx", "bookmarks", ["created_at"])
    op.create_index(
        "bookmarks_search_idx", "bookmarks", ["search_vector"], postgresql_using="gin"
    )

    op.create_table(
        "bookmark_tags",
        sa.Column("bookmark_id", sa.BigInteger, sa.ForeignKey("bookmarks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.BigInteger, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("bookmark_tags")
    op.drop_index("bookmarks_search_idx", table_name="bookmarks")
    op.drop_index("bookmarks_created_at_idx", table_name="bookmarks")
    op.drop_index("ix_bookmarks_domain", table_name="bookmarks")
    op.drop_table("bookmarks")
    op.drop_table("tags")
