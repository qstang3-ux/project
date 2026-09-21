"""Add persistent execution events for reliable SSE replay.

Revision ID: 20260916_0011
Revises: 20260916_0010
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0011"
down_revision: str | None = "20260916_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE app.qa_executions
            ADD COLUMN event_sequence_floor bigint NOT NULL DEFAULT 0
            CHECK (event_sequence_floor >= 0);

        CREATE TABLE app.qa_execution_events (
            id uuid PRIMARY KEY,
            execution_id uuid NOT NULL REFERENCES app.qa_executions(id) ON DELETE CASCADE,
            sequence bigint NOT NULL CHECK (sequence > 0),
            kind varchar(64) NOT NULL,
            status varchar(20) NOT NULL,
            summary text,
            data_json jsonb NOT NULL,
            dedupe_key varchar(200) NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE(execution_id, sequence),
            UNIQUE(execution_id, dedupe_key)
        );
        CREATE INDEX qa_execution_event_retention_idx
            ON app.qa_execution_events(created_at, execution_id);

        WITH candidate_events AS (
            SELECT
                e.id AS execution_id,
                'execution.started'::varchar(64) AS kind,
                'queued'::varchar(20) AS status,
                '执行已开始'::text AS summary,
                jsonb_build_object('kind', 'execution.started') AS data_json,
                'execution.started'::varchar(200) AS dedupe_key,
                e.created_at AS occurred_at,
                0 AS event_order
            FROM app.qa_executions e

            UNION ALL

            SELECT
                s.execution_id,
                CASE s.step_type
                    WHEN 'schema_selection' THEN 'schema.selected'
                    WHEN 'sql_generation' THEN 'sql.generated'
                    WHEN 'sql_validation' THEN 'sql.validated'
                    WHEN 'query_execution' THEN 'query.completed'
                    WHEN 'answer_generation' THEN 'answer.completed'
                    WHEN 'clarification_required' THEN 'clarification.required'
                END::varchar(64),
                CASE WHEN s.step_type='clarification_required'
                    THEN 'awaiting_input' ELSE 'running' END::varchar(20),
                s.summary,
                CASE s.step_type
                    WHEN 'schema_selection' THEN jsonb_build_object(
                        'kind', 'schema.selected', 'selectedObjects', e.selected_objects)
                    WHEN 'sql_generation' THEN jsonb_build_object(
                        'kind', 'sql.generated', 'sqlAvailable', e.generated_sql IS NOT NULL)
                    WHEN 'sql_validation' THEN jsonb_build_object(
                        'kind', 'sql.validated', 'sqlValidationStatus', 'passed',
                        'ruleVersion', '1.0')
                    WHEN 'query_execution' THEN jsonb_build_object(
                        'kind', 'query.completed', 'rowCount', COALESCE(e.row_count, 0),
                        'truncated', COALESCE((e.result_json->>'truncated')::boolean, false))
                    WHEN 'answer_generation' THEN jsonb_build_object(
                        'kind', 'answer.completed', 'assistantMessageId', e.assistant_message_id)
                    WHEN 'clarification_required' THEN jsonb_build_object(
                        'kind', 'clarification.required', 'clarification', e.clarification_json)
                END,
                ('step:' || s.effect_key)::varchar(200),
                COALESCE(s.completed_at, s.started_at, e.created_at),
                1
            FROM app.qa_execution_steps s
            JOIN app.qa_executions e ON e.id=s.execution_id
            WHERE s.step_type IN (
                'schema_selection','sql_generation','sql_validation','query_execution',
                'answer_generation','clarification_required'
            )

            UNION ALL

            SELECT
                e.id,
                CASE
                    WHEN e.status='completed' THEN 'execution.completed'
                    WHEN e.status='cancelled' THEN 'execution.cancelled'
                    ELSE 'execution.failed'
                END::varchar(64),
                e.status,
                COALESCE(e.error_message,
                    CASE WHEN e.status='completed' THEN '执行已完成' ELSE '执行失败' END),
                CASE
                    WHEN e.status='completed' THEN jsonb_build_object(
                        'kind', 'execution.completed',
                        'assistantMessageId', e.assistant_message_id)
                    WHEN e.status='cancelled' THEN jsonb_build_object(
                        'kind', 'execution.cancelled', 'reason', e.error_message)
                    ELSE jsonb_build_object(
                        'kind', 'execution.failed', 'error', jsonb_build_object(
                            'code', COALESCE(e.error_code, 'INTERNAL_ERROR'),
                            'message', COALESCE(e.error_message, '执行失败'),
                            'requestId', e.request_id,
                            'details', NULL))
                END,
                'execution.terminal'::varchar(200),
                COALESCE(e.completed_at, e.created_at),
                2
            FROM app.qa_executions e
            WHERE e.status IN ('completed','failed','cancelled','rejected')
        ), ranked_events AS (
            SELECT *, row_number() OVER (
                PARTITION BY execution_id
                ORDER BY occurred_at, event_order, dedupe_key
            ) AS sequence
            FROM candidate_events
            WHERE kind IS NOT NULL AND data_json IS NOT NULL
        )
        INSERT INTO app.qa_execution_events(
            id, execution_id, sequence, kind, status, summary,
            data_json, dedupe_key, created_at
        )
        SELECT gen_random_uuid(), execution_id, sequence, kind, status, summary,
            data_json, dedupe_key, occurred_at
        FROM ranked_events;

        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_rw') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON app.qa_execution_events TO app_rw;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS app.qa_execution_events;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS event_sequence_floor;
        """
    )
