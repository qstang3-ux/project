from datetime import date, datetime
from typing import Any
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin


class DataSource(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "data_sources"
    __table_args__ = {"schema": "app"}
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    group_name: Mapped[str] = mapped_column("group", String(20), default="ledger")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    unavailable_reason: Mapped[str | None] = mapped_column(String(500))
    data_as_of: Mapped[date] = mapped_column(Date)
    allowed_objects: Mapped[list[str]] = mapped_column(JSONB, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QaSession(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "qa_sessions"
    __table_args__ = (
        Index("session_owner_updated_idx", "owner_id", "pinned", "updated_at"),
        {"schema": "app"},
    )
    owner_id: Mapped[str] = mapped_column(String(64), default="demo-user")
    title: Mapped[str] = mapped_column(String(60), default="新对话")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_session_id: Mapped[UUID | None] = mapped_column(ForeignKey("app.qa_sessions.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QaMessage(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "qa_messages"
    __table_args__ = {"schema": "app"}
    session_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_sessions.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    source_message_id: Mapped[UUID | None] = mapped_column(ForeignKey("app.qa_messages.id"))
    execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.qa_executions.id", ondelete="SET NULL"), index=True
    )


class ModelConfig(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "model_configs"
    __table_args__ = (
        Index("model_one_active", "active", unique=True, postgresql_where="active"),
        {"schema": "app"},
    )
    name: Mapped[str] = mapped_column(String(100), unique=True)
    provider: Mapped[str] = mapped_column(String(50))
    protocol: Mapped[str] = mapped_column(String(30), default="chat_completions")
    base_url: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(200))
    encrypted_api_key: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    last_test_status: Mapped[str | None] = mapped_column(String(30))
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QaExecution(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "qa_executions"
    __table_args__ = (UniqueConstraint("idempotency_key"), {"schema": "app"})
    request_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    generate_chart: Mapped[bool] = mapped_column(Boolean, default=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_sessions.id"))
    user_message_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_messages.id"))
    assistant_message_id: Mapped[UUID | None] = mapped_column(ForeignKey("app.qa_messages.id"))
    model_config_id: Mapped[UUID | None] = mapped_column(ForeignKey("app.model_configs.id"))
    status: Mapped[str] = mapped_column(String(20))
    question: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(40))
    normalized_question: Mapped[str | None] = mapped_column(Text)
    missing_slots: Mapped[list[str]] = mapped_column(JSONB, default=list)
    intent_confidence: Mapped[float | None]
    intent_reason_code: Mapped[str | None] = mapped_column(String(100))
    clarification_round: Mapped[int] = mapped_column(Integer, default=0)
    clarification_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    clarification_history: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    data_source_ids: Mapped[list[str]] = mapped_column(JSONB)
    context_message_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    context_provenance: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    selected_objects: Mapped[list[str]] = mapped_column(JSONB, default=list)
    generated_sql: Mapped[str | None] = mapped_column(Text)
    executed_sql: Mapped[str | None] = mapped_column(Text)
    validation_summary: Mapped[str | None] = mapped_column(Text)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    answer: Mapped[str | None] = mapped_column(Text)
    chart_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    follow_up_questions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    model_name: Mapped[str | None] = mapped_column(String(200))
    token_usage: Mapped[dict[str, int]] = mapped_column(JSONB, default=dict)
    model_call_audit: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    graph_version: Mapped[str | None] = mapped_column(String(50))
    graph_thread_id: Mapped[str | None] = mapped_column(String(64))
    graph_node_trace: Mapped[list[str]] = mapped_column(JSONB, default=list)
    checkpoint_status: Mapped[str | None] = mapped_column(String(80))
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_attempt: Mapped[int] = mapped_column(Integer, default=0)
    event_sequence_floor: Mapped[int] = mapped_column(BigInteger, default=0)
    rag_document_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    rag_degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    row_count: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    regenerated_from_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.qa_executions.id")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdempotencyRecord(CreatedAtMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        Index("idempotency_operation_resource_idx", "operation", "resource_id"),
        {"schema": "app"},
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), primary_key=True)
    operation: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.qa_sessions.id", ondelete="SET NULL")
    )
    user_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.qa_messages.id", ondelete="SET NULL")
    )
    execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.qa_executions.id", ondelete="SET NULL")
    )


class QaExecutionStep(UuidPrimaryKeyMixin, Base):
    __tablename__ = "qa_execution_steps"
    __table_args__ = (
        UniqueConstraint("execution_id", "effect_key"),
        {"schema": "app"},
    )
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.qa_executions.id", ondelete="CASCADE")
    )
    step_type: Mapped[str] = mapped_column(String(40))
    effect_key: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QaExecutionEffect(UuidPrimaryKeyMixin, Base):
    __tablename__ = "qa_execution_effects"
    __table_args__ = (
        UniqueConstraint("execution_id", "effect_key"),
        Index("qa_execution_effect_status_idx", "execution_id", "status"),
        {"schema": "app"},
    )
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.qa_executions.id", ondelete="CASCADE")
    )
    effect_key: Mapped[str] = mapped_column(String(160))
    node_name: Mapped[str] = mapped_column(String(60))
    attempt: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(80))
    owner_id: Mapped[str] = mapped_column(String(128))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QaExecutionEvent(UuidPrimaryKeyMixin, Base):
    __tablename__ = "qa_execution_events"
    __table_args__ = (
        UniqueConstraint("execution_id", "sequence"),
        UniqueConstraint("execution_id", "dedupe_key"),
        CheckConstraint("sequence > 0", name="sequence_positive"),
        Index("qa_execution_event_retention_idx", "created_at", "execution_id"),
        {"schema": "app"},
    )
    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.qa_executions.id", ondelete="CASCADE")
    )
    sequence: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str | None] = mapped_column(Text)
    data_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    dedupe_key: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class QaAnswerVersion(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "qa_answer_versions"
    __table_args__ = (UniqueConstraint("assistant_message_id", "version_no"), {"schema": "app"})
    assistant_message_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_messages.id"))
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_executions.id"))
    version_no: Mapped[int] = mapped_column(Integer)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class QaFeedback(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "qa_feedback"
    __table_args__ = {"schema": "app"}
    session_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_sessions.id"))
    assistant_message_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_messages.id"))
    execution_id: Mapped[UUID] = mapped_column(ForeignKey("app.qa_executions.id"))
    reason: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    resolution_note: Mapped[str | None] = mapped_column(String(2000))
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FavoriteQuestion(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "favorite_questions"
    __table_args__ = (UniqueConstraint("owner_id", "normalized_question"), {"schema": "app"})
    owner_id: Mapped[str] = mapped_column(String(64), default="demo-user")
    normalized_question: Mapped[str] = mapped_column(String(2000))
    display_question: Mapped[str] = mapped_column(String(2000))
    source_message_id: Mapped[UUID | None] = mapped_column(ForeignKey("app.qa_messages.id"))


class ApplicationConfig(Base):
    __tablename__ = "application_config"
    __table_args__ = {"schema": "app"}
    id: Mapped[bool] = mapped_column(Boolean, primary_key=True, default=True)
    greeting_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    greeting_text: Mapped[str] = mapped_column(String(1000))
    recommended_questions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    follow_up_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    frequent_questions_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    frequent_question_threshold: Mapped[int] = mapped_column(Integer, default=3)
    model_qa_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    tts_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    stt_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RagDocument(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "rag_documents"
    __table_args__ = (
        UniqueConstraint("stable_key"),
        Index("rag_documents_enabled_type_idx", "enabled", "knowledge_type"),
        {"schema": "app"},
    )
    stable_key: Mapped[str] = mapped_column(String(200))
    knowledge_type: Mapped[str] = mapped_column(String(30))
    source_path: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[str] = mapped_column(Text)
    data_source_id: Mapped[UUID | None] = mapped_column(ForeignKey("app.data_sources.id"))
    object_names: Mapped[list[str]] = mapped_column(JSONB, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64))
    embedding_model: Mapped[str] = mapped_column(String(200))
    embedding_dimension: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float]] = mapped_column(Vector(512))
    version: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
