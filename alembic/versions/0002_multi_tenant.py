"""Isolation multi-tenant : colonnes tenant_id sur documents et reports.

Revision ID: 0002
Revises: 0001
Create Date: 2025-01-02
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("tenant_id", sa.String(128), nullable=False, server_default="default"),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.add_column(
        "reports",
        sa.Column("tenant_id", sa.String(128), nullable=False, server_default="default"),
    )
    op.create_index("ix_reports_tenant_id", "reports", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_tenant_id", "reports")
    op.drop_column("reports", "tenant_id")
    op.drop_index("ix_documents_tenant_id", "documents")
    op.drop_column("documents", "tenant_id")
