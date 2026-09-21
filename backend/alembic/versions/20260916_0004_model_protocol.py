"""Add model API protocol selection.

Revision ID: 20260916_0004
Revises: 20260916_0003
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260916_0004"
down_revision: str | None = "20260916_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "model_configs",
        sa.Column(
            "protocol",
            sa.String(length=30),
            server_default="chat_completions",
            nullable=False,
        ),
        schema="app",
    )
    op.create_check_constraint(
        "model_configs_protocol_valid",
        "model_configs",
        "protocol IN ('responses','chat_completions')",
        schema="app",
    )
    op.execute(
        "UPDATE app.model_configs SET protocol='responses' WHERE lower(model_name)='gpt-5.6-sol'"
    )


def downgrade() -> None:
    op.drop_constraint("model_configs_protocol_valid", "model_configs", schema="app", type_="check")
    op.drop_column("model_configs", "protocol", schema="app")
