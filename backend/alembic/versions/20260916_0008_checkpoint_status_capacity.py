"""Expand checkpoint status for explicit graph node names.

Revision ID: 20260916_0008
Revises: 20260916_0007
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0008"
down_revision: str | None = "20260916_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE app.qa_executions ALTER COLUMN checkpoint_status TYPE varchar(80)")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE app.qa_executions ALTER COLUMN checkpoint_status TYPE varchar(30) "
        "USING left(checkpoint_status, 30)"
    )
