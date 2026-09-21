"""Add globally bound idempotency records.

Revision ID: 20260916_0009
Revises: 20260916_0008
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0009"
down_revision: str | None = "20260916_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE app.idempotency_records (
            idempotency_key varchar(128) PRIMARY KEY,
            operation varchar(40) NOT NULL,
            resource_id varchar(128) NOT NULL,
            request_fingerprint char(64) NOT NULL,
            session_id uuid REFERENCES app.qa_sessions(id) ON DELETE SET NULL,
            user_message_id uuid REFERENCES app.qa_messages(id) ON DELETE SET NULL,
            execution_id uuid REFERENCES app.qa_executions(id) ON DELETE SET NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX idempotency_operation_resource_idx
            ON app.idempotency_records(operation, resource_id);

        INSERT INTO app.idempotency_records (
            idempotency_key,
            operation,
            resource_id,
            request_fingerprint,
            session_id,
            user_message_id,
            execution_id
        )
        SELECT
            idempotency_key,
            'legacy_execution',
            session_id::text,
            md5(id::text) || md5(idempotency_key),
            session_id,
            user_message_id,
            id
        FROM app.qa_executions
        ON CONFLICT (idempotency_key) DO NOTHING;

        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_rw') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON app.idempotency_records TO app_rw;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS app.idempotency_records")
