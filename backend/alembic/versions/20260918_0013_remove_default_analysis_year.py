"""Remove the implicit default analysis year setting.

Revision ID: 20260918_0013
Revises: 20260916_0012
Create Date: 2026-09-18
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260918_0013"
down_revision: str | None = "20260916_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.application_config
            DROP COLUMN IF EXISTS default_analysis_year;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.application_config
            ADD COLUMN default_analysis_year smallint NOT NULL DEFAULT 2026;
        """
    )
