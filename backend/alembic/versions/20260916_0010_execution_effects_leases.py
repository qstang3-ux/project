"""Add execution effect idempotency and worker leases.

Revision ID: 20260916_0010
Revises: 20260916_0009
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0010"
down_revision: str | None = "20260916_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.qa_executions
            ADD COLUMN generate_chart boolean NOT NULL DEFAULT true,
            ADD COLUMN lease_owner varchar(128),
            ADD COLUMN lease_expires_at timestamptz,
            ADD COLUMN heartbeat_at timestamptz,
            ADD COLUMN run_attempt integer NOT NULL DEFAULT 0 CHECK (run_attempt >= 0);

        CREATE INDEX qa_execution_recovery_idx
            ON app.qa_executions(status, lease_expires_at, created_at);

        ALTER TABLE app.qa_execution_steps ADD COLUMN effect_key varchar(160);
        UPDATE app.qa_execution_steps SET effect_key='legacy:' || id::text;
        ALTER TABLE app.qa_execution_steps ALTER COLUMN effect_key SET NOT NULL;
        ALTER TABLE app.qa_execution_steps
            ADD CONSTRAINT qa_execution_steps_execution_effect_key_key
            UNIQUE(execution_id, effect_key);

        CREATE TABLE app.qa_execution_effects (
            id uuid PRIMARY KEY,
            execution_id uuid NOT NULL REFERENCES app.qa_executions(id) ON DELETE CASCADE,
            effect_key varchar(160) NOT NULL,
            node_name varchar(60) NOT NULL,
            attempt integer NOT NULL CHECK (attempt >= 0),
            status varchar(20) NOT NULL CHECK (status IN ('started','completed','failed')),
            payload_json jsonb,
            error_code varchar(80),
            owner_id varchar(128) NOT NULL,
            started_at timestamptz NOT NULL DEFAULT now(),
            completed_at timestamptz,
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(execution_id, effect_key)
        );
        CREATE INDEX qa_execution_effect_status_idx
            ON app.qa_execution_effects(execution_id, status);

        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_rw') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON app.qa_execution_effects TO app_rw;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS app.qa_execution_effects;
        ALTER TABLE app.qa_execution_steps
            DROP CONSTRAINT IF EXISTS qa_execution_steps_execution_effect_key_key;
        ALTER TABLE app.qa_execution_steps DROP COLUMN IF EXISTS effect_key;
        DROP INDEX IF EXISTS app.qa_execution_recovery_idx;
        ALTER TABLE app.qa_executions
            DROP COLUMN IF EXISTS run_attempt,
            DROP COLUMN IF EXISTS heartbeat_at,
            DROP COLUMN IF EXISTS lease_expires_at,
            DROP COLUMN IF EXISTS lease_owner,
            DROP COLUMN IF EXISTS generate_chart;
        """
    )
