"""Add intent classification and clarification audit fields.

Revision ID: 20260916_0007
Revises: 20260916_0006
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0007"
down_revision: str | None = "20260916_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.qa_executions
            DROP CONSTRAINT IF EXISTS qa_executions_status_check;
        ALTER TABLE app.qa_executions
            ADD CONSTRAINT qa_executions_status_check CHECK (
                status IN (
                    'queued','running','awaiting_input','completed','failed','cancelled','rejected'
                )
            );
        ALTER TABLE app.qa_executions ADD COLUMN intent varchar(40);
        ALTER TABLE app.qa_executions ADD COLUMN normalized_question text;
        ALTER TABLE app.qa_executions
            ADD COLUMN missing_slots jsonb NOT NULL DEFAULT '[]'::jsonb;
        ALTER TABLE app.qa_executions ADD COLUMN intent_confidence numeric(5,4);
        ALTER TABLE app.qa_executions ADD COLUMN intent_reason_code varchar(100);
        ALTER TABLE app.qa_executions
            ADD COLUMN clarification_round integer NOT NULL DEFAULT 0
            CHECK (clarification_round BETWEEN 0 AND 2);
        ALTER TABLE app.qa_executions ADD COLUMN clarification_json jsonb;
        ALTER TABLE app.qa_executions
            ADD COLUMN clarification_history jsonb NOT NULL DEFAULT '[]'::jsonb;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE app.qa_executions
        SET status='failed',
            error_code=COALESCE(error_code, 'EXECUTION_NOT_AWAITING_INPUT'),
            error_message=COALESCE(error_message, '澄清功能回滚，等待输入状态已关闭'),
            completed_at=COALESCE(completed_at, now())
        WHERE status='awaiting_input';
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS clarification_history;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS clarification_json;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS clarification_round;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS intent_reason_code;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS intent_confidence;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS missing_slots;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS normalized_question;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS intent;
        ALTER TABLE app.qa_executions
            DROP CONSTRAINT IF EXISTS qa_executions_status_check;
        ALTER TABLE app.qa_executions
            ADD CONSTRAINT qa_executions_status_check CHECK (
                status IN ('queued','running','completed','failed','cancelled','rejected')
            );
        """
    )
