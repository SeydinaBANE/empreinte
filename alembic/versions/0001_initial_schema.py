"""Schema initial : documents, document_pages, reports.

Revision ID: 0001
Revises:
Create Date: 2025-01-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("doc_id", sa.String(128), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "document_pages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "doc_id",
            sa.String(128),
            sa.ForeignKey("documents.doc_id"),
            nullable=False,
            index=True,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(1024), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
    )
    op.create_table(
        "reports",
        sa.Column("doc_id", sa.String(128), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("document_pages")
    op.drop_table("documents")
