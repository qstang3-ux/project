"""Link messages directly to their execution.

Revision ID: 20260916_0002
Revises: 20260916_0001
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260916_0002"
down_revision: str | None = "20260916_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("qa_messages", sa.Column("execution_id", sa.Uuid(), nullable=True), schema="app")
    op.create_foreign_key(
        "qa_messages_execution_id_fkey",
        "qa_messages",
        "qa_executions",
        ["execution_id"],
        ["id"],
        source_schema="app",
        referent_schema="app",
        ondelete="SET NULL",
    )
    op.execute(
        """
        UPDATE app.qa_messages AS message
        SET execution_id = execution.id
        FROM app.qa_executions AS execution
        WHERE message.id = execution.user_message_id
           OR message.id = execution.assistant_message_id
        """
    )
    op.create_index("qa_messages_execution_id_idx", "qa_messages", ["execution_id"], schema="app")


def downgrade() -> None:
    op.drop_index("qa_messages_execution_id_idx", table_name="qa_messages", schema="app")
    op.drop_constraint(
        "qa_messages_execution_id_fkey", "qa_messages", schema="app", type_="foreignkey"
    )
    op.drop_column("qa_messages", "execution_id", schema="app")
