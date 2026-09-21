from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import QaExecution, QaExecutionEffect, QaExecutionStep
from app.services.execution_effects import begin_execution_effect, fail_execution_effect
from app.services.query_service import QueryService
from app.text2sql.adapters import FakeModelAdapter


class RecordingSession:
    def __init__(self, scalar_result: object | None = None) -> None:
        self.scalar_result = scalar_result
        self.added: list[object] = []
        self.commits = 0
        self.executed = 0
        self.refreshed = 0

    def execute(self, statement: object) -> None:
        del statement
        self.executed += 1

    def scalar(self, statement: object) -> object | None:
        del statement
        return self.scalar_result

    def add(self, model: object) -> None:
        self.added.append(model)

    def commit(self) -> None:
        self.commits += 1

    def refresh(self, model: object) -> None:
        del model
        self.refreshed += 1


def execution(*, status: str = "running") -> QaExecution:
    return QaExecution(
        id=uuid4(),
        request_id=f"request-{uuid4()}",
        idempotency_key=f"idempotency-{uuid4()}",
        session_id=uuid4(),
        user_message_id=uuid4(),
        status=status,
        question="测试审计",
        data_source_ids=[],
        context_message_ids=[],
        model_call_audit=[],
        token_usage={},
        generate_chart=True,
    )


def test_begin_execution_effect_takes_over_an_existing_started_effect() -> None:
    effect = QaExecutionEffect(
        id=uuid4(),
        execution_id=uuid4(),
        effect_key="sql-generation:1",
        node_name="generate_sql",
        attempt=1,
        status="started",
        owner_id="old-worker",
        started_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db = RecordingSession(effect)

    result = begin_execution_effect(
        cast(Session, db),
        execution_id=effect.execution_id,
        effect_key=effect.effect_key,
        node_name=effect.node_name,
        attempt=2,
        owner_id="new-worker",
    )

    assert result is effect
    assert effect.owner_id == "new-worker"
    assert db.executed == 1
    assert db.commits == 1


def test_begin_execution_effect_requires_persisted_row() -> None:
    db = RecordingSession()

    with pytest.raises(RuntimeError, match="was not persisted"):
        begin_execution_effect(
            cast(Session, db),
            execution_id=uuid4(),
            effect_key="missing",
            node_name="generate_sql",
            attempt=1,
            owner_id="worker",
        )


def test_fail_execution_effect_records_terminal_payload() -> None:
    effect = QaExecutionEffect(
        id=uuid4(),
        execution_id=uuid4(),
        effect_key="query:1",
        node_name="execute_sql",
        attempt=1,
        status="started",
        owner_id="worker",
        started_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    fail_execution_effect(effect, error_code="QUERY_FAILED", payload={"retryable": True})

    assert effect.status == "failed"
    assert effect.error_code == "QUERY_FAILED"
    assert effect.payload_json == {"retryable": True}
    assert effect.completed_at is not None


def test_model_call_audit_accumulates_tokens_and_can_mark_invalid() -> None:
    db = RecordingSession()
    item = execution()
    adapter = FakeModelAdapter()

    QueryService._record_model_call(
        cast(Session, db), item, adapter, "sql_generation", 42, 11, 7, "success", None
    )
    QueryService._record_model_call(
        cast(Session, db), item, adapter, "answer_generation", 8, 3, 2, "success", None
    )

    assert item.token_usage == {"promptTokens": 14, "completionTokens": 9, "totalTokens": 23}
    assert len(item.model_call_audit) == 2
    assert item.model_call_audit[-1]["totalTokens"] == 5

    QueryService._mark_last_model_call_invalid(cast(Session, db), item)
    assert item.model_call_audit[-1]["status"] == "invalid_output"
    assert item.model_call_audit[-1]["errorCode"] == "MODEL_INVALID_RESPONSE"
    assert db.commits == 3


def test_mark_invalid_with_no_model_calls_is_a_noop() -> None:
    db = RecordingSession()
    QueryService._mark_last_model_call_invalid(cast(Session, db), execution())
    assert db.commits == 0


def test_cancel_guard_and_legacy_step_persistence() -> None:
    db = RecordingSession()
    cancelled = execution(status="cancelled")
    with pytest.raises(AppError) as exc_info:
        QueryService._ensure_not_cancelled(cast(Session, db), cancelled)
    assert exc_info.value.code == "EXECUTION_CANCELLED"

    running = execution()
    QueryService._ensure_not_cancelled(cast(Session, db), running)
    QueryService._step(cast(Session, db), running, "schema_selection", "已选择数据对象")

    assert db.refreshed == 2
    assert db.commits == 1
    step = cast(QaExecutionStep, db.added[0])
    assert step.execution_id == running.id
    assert step.status == "completed"
    assert step.summary == "已选择数据对象"
