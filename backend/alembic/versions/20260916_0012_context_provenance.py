"""Add execution context provenance audit.

Revision ID: 20260916_0012
Revises: 20260916_0011
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0012"
down_revision: str | None = "20260916_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.qa_executions
            ADD COLUMN context_provenance jsonb NOT NULL DEFAULT '[]'::jsonb;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS context_provenance;
        """
    )
