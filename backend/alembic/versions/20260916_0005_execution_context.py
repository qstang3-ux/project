"""Persist execution context message ids.

Revision ID: 20260916_0005
Revises: 20260916_0004
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260916_0005"
down_revision: str | None = "20260916_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "qa_executions",
        sa.Column(
            "context_message_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        schema="app",
    )


def downgrade() -> None:
    op.drop_column("qa_executions", "context_message_ids", schema="app")
