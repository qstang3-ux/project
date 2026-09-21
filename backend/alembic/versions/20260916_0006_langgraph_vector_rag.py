"""Add LangGraph audit, PostgreSQL checkpoints, and pgvector RAG.

Revision ID: 20260916_0006
Revises: 20260916_0005
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0006"
down_revision: str | None = "20260916_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE app.rag_documents (
            id uuid PRIMARY KEY,
            stable_key varchar(200) NOT NULL UNIQUE,
            knowledge_type varchar(30) NOT NULL CHECK (
                knowledge_type IN ('schema','column','metric','join','few_shot','business_rule')
            ),
            source_path varchar(500) NOT NULL,
            title varchar(300) NOT NULL,
            content text NOT NULL,
            data_source_id uuid REFERENCES app.data_sources(id),
            object_names jsonb NOT NULL DEFAULT '[]'::jsonb,
            metadata_json jsonb NOT NULL DEFAULT '{}'::jsonb,
            content_hash varchar(64) NOT NULL,
            embedding_model varchar(200) NOT NULL,
            embedding_dimension integer NOT NULL CHECK (embedding_dimension = 512),
            embedding vector(512) NOT NULL,
            version integer NOT NULL DEFAULT 1 CHECK (version > 0),
            enabled boolean NOT NULL DEFAULT true,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX rag_documents_enabled_type_idx
            ON app.rag_documents(enabled, knowledge_type);

        ALTER TABLE app.qa_executions ADD COLUMN graph_version varchar(50);
        ALTER TABLE app.qa_executions ADD COLUMN graph_thread_id varchar(64);
        ALTER TABLE app.qa_executions ADD COLUMN graph_node_trace jsonb NOT NULL DEFAULT '[]';
        ALTER TABLE app.qa_executions ADD COLUMN checkpoint_status varchar(30);
        ALTER TABLE app.qa_executions ADD COLUMN rag_document_ids jsonb NOT NULL DEFAULT '[]';
        ALTER TABLE app.qa_executions ADD COLUMN rag_degraded boolean NOT NULL DEFAULT false;

        CREATE TABLE app.checkpoint_migrations (v integer PRIMARY KEY);
        CREATE TABLE app.checkpoints (
            thread_id text NOT NULL,
            checkpoint_ns text NOT NULL DEFAULT '',
            checkpoint_id text NOT NULL,
            parent_checkpoint_id text,
            type text,
            checkpoint jsonb NOT NULL,
            metadata jsonb NOT NULL DEFAULT '{}',
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
        );
        CREATE TABLE app.checkpoint_blobs (
            thread_id text NOT NULL,
            checkpoint_ns text NOT NULL DEFAULT '',
            channel text NOT NULL,
            version text NOT NULL,
            type text NOT NULL,
            blob bytea,
            PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
        );
        CREATE TABLE app.checkpoint_writes (
            thread_id text NOT NULL,
            checkpoint_ns text NOT NULL DEFAULT '',
            checkpoint_id text NOT NULL,
            task_id text NOT NULL,
            idx integer NOT NULL,
            channel text NOT NULL,
            type text,
            blob bytea NOT NULL,
            task_path text NOT NULL DEFAULT '',
            PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
        );
        CREATE INDEX checkpoints_thread_id_idx ON app.checkpoints(thread_id);
        CREATE INDEX checkpoint_blobs_thread_id_idx ON app.checkpoint_blobs(thread_id);
        CREATE INDEX checkpoint_writes_thread_id_idx ON app.checkpoint_writes(thread_id);
        INSERT INTO app.checkpoint_migrations(v) SELECT generate_series(0, 9);

        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_rw') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON app.rag_documents,
                    app.checkpoint_migrations, app.checkpoints, app.checkpoint_blobs,
                    app.checkpoint_writes TO app_rw;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='text2sql_ro') THEN
                REVOKE ALL ON app.rag_documents, app.checkpoint_migrations, app.checkpoints,
                    app.checkpoint_blobs, app.checkpoint_writes FROM text2sql_ro;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS app.checkpoint_writes;
        DROP TABLE IF EXISTS app.checkpoint_blobs;
        DROP TABLE IF EXISTS app.checkpoints;
        DROP TABLE IF EXISTS app.checkpoint_migrations;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS rag_degraded;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS rag_document_ids;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS checkpoint_status;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS graph_node_trace;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS graph_thread_id;
        ALTER TABLE app.qa_executions DROP COLUMN IF EXISTS graph_version;
        DROP TABLE IF EXISTS app.rag_documents;
        """
    )
