from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import QaExecution, QaExecutionEvent

TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled", "rejected"})
STEP_EVENT_KINDS = {
    "schema_selection": "schema.selected",
    "sql_generation": "sql.generated",
    "sql_validation": "sql.validated",
    "query_execution": "query.completed",
    "answer_generation": "answer.completed",
    "clarification_required": "clarification.required",
}


def event_id(execution_id: UUID, sequence: int) -> str:
    return f"{execution_id}:{sequence}"


def parse_event_id(raw_event_id: str, execution_id: UUID) -> int:
    try:
        raw_execution_id, raw_sequence = raw_event_id.rsplit(":", 1)
        cursor_execution_id = UUID(raw_execution_id)
        sequence = int(raw_sequence)
    except (TypeError, ValueError) as exc:
        raise AppError("SSE_EVENT_ID_INVALID", "SSE 事件 ID 格式无效", 422) from exc
    if cursor_execution_id != execution_id:
        raise AppError("SSE_EVENT_EXECUTION_MISMATCH", "SSE 事件不属于当前执行", 409)
    if sequence <= 0:
        raise AppError("SSE_EVENT_ID_INVALID", "SSE 事件 sequence 必须为正整数", 422)
    return sequence


def append_execution_event(
    db: Session,
    *,
    execution_id: UUID,
    kind: str,
    status: str,
    summary: str | None,
    data: dict[str, Any],
    dedupe_key: str,
    created_at: datetime | None = None,
    expected_lease_owner: str | None = None,
) -> QaExecutionEvent:
    execution = db.scalar(
        select(QaExecution)
        .where(QaExecution.id == execution_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if execution is None:
        raise AppError("RESOURCE_NOT_FOUND", "执行记录不存在", 404)
    if expected_lease_owner is not None and (
        execution.status != "running" or execution.lease_owner != expected_lease_owner
    ):
        raise AppError("EXECUTION_LEASE_LOST", "执行租约已失效", 409)
    existing = db.scalar(
        select(QaExecutionEvent).where(
            QaExecutionEvent.execution_id == execution_id,
            QaExecutionEvent.dedupe_key == dedupe_key,
        )
    )
    if existing is not None:
        return existing
    latest_sequence = int(
        db.scalar(
            select(func.max(QaExecutionEvent.sequence)).where(
                QaExecutionEvent.execution_id == execution_id
            )
        )
        or 0
    )
    sequence = max(latest_sequence, execution.event_sequence_floor) + 1
    event = QaExecutionEvent(
        execution_id=execution_id,
        sequence=sequence,
        kind=kind,
        status=status,
        summary=summary,
        data_json=data,
        dedupe_key=dedupe_key,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    return event


def append_started_event(db: Session, execution: QaExecution) -> QaExecutionEvent:
    return append_execution_event(
        db,
        execution_id=execution.id,
        kind="execution.started",
        status="queued",
        summary="执行已开始",
        data={"kind": "execution.started"},
        dedupe_key="execution.started",
        created_at=execution.created_at,
    )


def append_step_event(
    db: Session,
    execution: QaExecution,
    *,
    effect_key: str,
    step_type: str,
    summary: str,
    created_at: datetime,
    owner_id: str,
) -> QaExecutionEvent | None:
    kind = STEP_EVENT_KINDS.get(step_type)
    if kind is None:
        return None
    status = "awaiting_input" if step_type == "clarification_required" else "running"
    return append_execution_event(
        db,
        execution_id=execution.id,
        kind=kind,
        status=status,
        summary=summary,
        data=_step_event_data(execution, step_type),
        dedupe_key=f"step:{effect_key}",
        created_at=created_at,
        expected_lease_owner=owner_id,
    )


def append_terminal_event(
    db: Session,
    execution: QaExecution,
    *,
    status: str,
    created_at: datetime,
) -> QaExecutionEvent:
    if status == "completed":
        kind = "execution.completed"
        summary = "执行已完成"
        data: dict[str, Any] = {
            "kind": kind,
            "assistantMessageId": (
                str(execution.assistant_message_id) if execution.assistant_message_id else None
            ),
        }
    elif status == "cancelled":
        kind = "execution.cancelled"
        summary = execution.error_message or "执行已取消"
        data = {"kind": kind, "reason": execution.error_message}
    else:
        kind = "execution.failed"
        summary = execution.error_message or "执行失败"
        data = {
            "kind": kind,
            "error": {
                "code": execution.error_code or "INTERNAL_ERROR",
                "message": execution.error_message or "执行失败",
                "requestId": execution.request_id,
                "details": None,
            },
        }
    return append_execution_event(
        db,
        execution_id=execution.id,
        kind=kind,
        status=status,
        summary=summary,
        data=data,
        dedupe_key="execution.terminal",
        created_at=created_at,
    )


def validate_event_cursor(db: Session, execution_id: UUID, sequence: int) -> None:
    execution = db.get(QaExecution, execution_id)
    if execution is None:
        raise AppError("RESOURCE_NOT_FOUND", "执行记录不存在", 404)
    if sequence <= execution.event_sequence_floor:
        raise AppError("SSE_EVENT_EXPIRED", "SSE 事件已超过保留期", 410)
    latest_sequence = int(
        db.scalar(
            select(func.max(QaExecutionEvent.sequence)).where(
                QaExecutionEvent.execution_id == execution_id
            )
        )
        or execution.event_sequence_floor
    )
    if sequence > latest_sequence:
        raise AppError("SSE_EVENT_ID_INVALID", "SSE 事件 sequence 超出当前历史", 422)
    exists = db.scalar(
        select(QaExecutionEvent.id).where(
            QaExecutionEvent.execution_id == execution_id,
            QaExecutionEvent.sequence == sequence,
        )
    )
    if exists is None:
        raise AppError("SSE_EVENT_ID_INVALID", "SSE 事件 sequence 不存在", 422)


def execution_events_after(
    db: Session, execution_id: UUID, after_sequence: int, limit: int
) -> tuple[list[QaExecutionEvent], str]:
    execution = db.get(QaExecution, execution_id)
    if execution is None:
        raise AppError("RESOURCE_NOT_FOUND", "执行记录不存在", 404)
    events = list(
        db.scalars(
            select(QaExecutionEvent)
            .where(
                QaExecutionEvent.execution_id == execution_id,
                QaExecutionEvent.sequence > after_sequence,
            )
            .order_by(QaExecutionEvent.sequence)
            .limit(limit)
        )
    )
    return events, execution.status


def event_envelope(event: QaExecutionEvent) -> dict[str, Any]:
    return {
        "id": event_id(event.execution_id, event.sequence),
        "executionId": str(event.execution_id),
        "type": event.kind,
        "status": event.status,
        "summary": event.summary,
        "occurredAt": event.created_at.isoformat(),
        "data": event.data_json,
    }


def _step_event_data(execution: QaExecution, step_type: str) -> dict[str, Any]:
    if step_type == "schema_selection":
        return {"kind": "schema.selected", "selectedObjects": execution.selected_objects}
    if step_type == "sql_generation":
        return {"kind": "sql.generated", "sqlAvailable": execution.generated_sql is not None}
    if step_type == "sql_validation":
        return {
            "kind": "sql.validated",
            "sqlValidationStatus": "passed",
            "ruleVersion": "1.0",
        }
    if step_type == "query_execution":
        result = execution.result_json or {}
        return {
            "kind": "query.completed",
            "rowCount": execution.row_count or 0,
            "truncated": bool(result.get("truncated", False)),
        }
    if step_type == "answer_generation":
        return {
            "kind": "answer.completed",
            "assistantMessageId": (
                str(execution.assistant_message_id) if execution.assistant_message_id else None
            ),
        }
    clarification = execution.clarification_json or {}
    return {"kind": "clarification.required", "clarification": clarification}
