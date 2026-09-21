import asyncio
import csv
import io
import json
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Path, Query, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session, new_session
from app.core.errors import AppError, NotFoundError
from app.models import (
    DataSource,
    QaExecution,
)
from app.schemas.qa import (
    AnswerVersion,
    ClarificationSubmit,
    DataSourceListResponse,
    DataSourceOut,
    ExecutionDetail,
    ExecutionStatusResponse,
    MessageListResponse,
    MessageResubmitRequest,
    QueryAccepted,
    QueryCreate,
    RegenerateRequest,
    SessionCreate,
    SessionListResponse,
    SessionOut,
    SessionUpdate,
)
from app.services.execution_events import (
    TERMINAL_STATUSES,
    event_envelope,
    event_id,
    execution_events_after,
    parse_event_id,
    validate_event_cursor,
)
from app.services.query_service import QueryService, execution_detail
from app.services.session_service import SessionService

router = APIRouter(prefix="/api/v1")


def _execution_event_data(execution: QaExecution, step_type: str | None = None) -> dict[str, Any]:
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
    if step_type == "clarification_required":
        clarification = execution.clarification_json or {}
        return {
            "kind": "clarification.required",
            "clarification": clarification,
        }
    return {"kind": "execution.started"}


@router.get("/data-sources", response_model=DataSourceListResponse)
def list_data_sources(
    db: Session = Depends(get_session), settings: Settings = Depends(get_settings)
) -> DataSourceListResponse:
    sources = db.scalars(
        select(DataSource).order_by(DataSource.is_default.desc(), DataSource.name)
    ).all()
    return DataSourceListResponse(
        items=[
            DataSourceOut(
                id=s.id,
                name=s.name,
                description=s.description,
                group=s.group_name,
                enabled=s.enabled,
                is_default=s.is_default,
                unavailable_reason=s.unavailable_reason,
                data_as_of=s.data_as_of,
                allowed_objects=s.allowed_objects,
            )
            for s in sources
        ],
        max_selection=settings.max_data_source_selection,
    )


@router.post("/qa/sessions", response_model=SessionOut, status_code=201)
def create_session(
    body: SessionCreate,
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionOut:
    return SessionService(db, settings.fixed_user_id).create(body.title)


@router.get("/qa/sessions", response_model=SessionListResponse)
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    keyword: str | None = Query(None, max_length=60),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionListResponse:
    return SessionService(db, settings.fixed_user_id).list(page, page_size, keyword)


@router.get("/qa/sessions/{sessionId}", response_model=SessionOut)
def get_qa_session(
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionOut:
    return SessionService(db, settings.fixed_user_id).get(session_id)


@router.patch("/qa/sessions/{sessionId}", response_model=SessionOut)
def update_qa_session(
    body: SessionUpdate,
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> SessionOut:
    if body.title is None and body.pinned is None:
        raise AppError("VALIDATION_ERROR", "至少提供一个更新字段", 422)
    return SessionService(db, settings.fixed_user_id).update(session_id, body.title, body.pinned)


@router.delete("/qa/sessions/{sessionId}", status_code=204)
def delete_qa_session(
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    SessionService(db, settings.fixed_user_id).delete(session_id)
    return Response(status_code=204)


@router.get("/qa/sessions/{sessionId}/messages", response_model=MessageListResponse)
def list_messages(
    session_id: UUID = Path(alias="sessionId"),
    cursor: UUID | None = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MessageListResponse:
    return SessionService(db, settings.fixed_user_id).messages(session_id, cursor, limit)


@router.post("/qa/sessions/{sessionId}/queries", response_model=QueryAccepted, status_code=202)
def create_query(
    body: QueryCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    session_id: UUID = Path(alias="sessionId"),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QueryAccepted:
    accepted = QueryService(db, settings).create(
        session_id,
        body.question,
        body.data_source_ids,
        body.generate_chart,
        idempotency_key,
        request.state.request_id,
        body.context_message_ids,
    )
    if not accepted.replayed and accepted.accepted.status == "queued":
        background_tasks.add_task(
            QueryService(db, settings).run,
            accepted.accepted.execution_id,
            body.generate_chart,
        )
    return accepted.accepted


@router.get("/qa/executions/{executionId}", response_model=ExecutionDetail)
def get_execution(
    execution_id: UUID = Path(alias="executionId"), db: Session = Depends(get_session)
) -> ExecutionDetail:
    return execution_detail(db, execution_id)


@router.post(
    "/qa/executions/{executionId}/clarifications",
    response_model=QueryAccepted,
    status_code=202,
)
def submit_clarification(
    body: ClarificationSubmit,
    background_tasks: BackgroundTasks,
    execution_id: UUID = Path(alias="executionId"),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QueryAccepted:
    submission = QueryService(db, settings).submit_clarification(
        execution_id, body.content, idempotency_key
    )
    if not submission.replayed and submission.accepted.status == "queued":
        background_tasks.add_task(
            QueryService(db, settings).run,
            submission.accepted.execution_id,
            True,
            True,
        )
    return submission.accepted


@router.post("/qa/executions/{executionId}/cancel", response_model=ExecutionStatusResponse)
def cancel_execution(
    execution_id: UUID = Path(alias="executionId"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ExecutionStatusResponse:
    execution = QueryService(db, settings).cancel(execution_id)
    return ExecutionStatusResponse(
        execution_id=execution.id,
        status=execution.status,
        updated_at=execution.completed_at or execution.created_at,
    )


@router.get("/qa/executions/{executionId}/events")
async def stream_execution(
    request: Request,
    execution_id: UUID = Path(alias="executionId"),
    last_event_id: str | None = Header(None, alias="Last-Event-ID", max_length=80),
    last_event_id_query: str | None = Query(None, alias="lastEventId", max_length=80),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    raw_cursor = last_event_id if last_event_id is not None else last_event_id_query

    def initial_cursor() -> int:
        with new_session() as db:
            execution = db.get(QaExecution, execution_id)
            if execution is None:
                raise NotFoundError("执行记录不存在")
            if raw_cursor is None:
                return execution.event_sequence_floor
            cursor = parse_event_id(raw_cursor.strip(), execution_id)
            validate_event_cursor(db, execution_id, cursor)
            return cursor

    cursor = await asyncio.to_thread(initial_cursor)

    def poll(after_sequence: int) -> tuple[list[dict[str, Any]], str]:
        with new_session() as db:
            rows, status = execution_events_after(
                db,
                execution_id,
                after_sequence,
                settings.execution_event_batch_size,
            )
            return [event_envelope(row) for row in rows], status

    async def events() -> AsyncIterator[str]:
        next_sequence = cursor
        loop = asyncio.get_running_loop()
        next_keepalive = loop.time() + settings.execution_event_heartbeat_seconds
        try:
            while True:
                if await request.is_disconnected():
                    return
                batch, status = await asyncio.to_thread(poll, next_sequence)
                if batch:
                    for envelope in batch:
                        next_sequence = parse_event_id(str(envelope["id"]), execution_id)
                        payload = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))
                        yield (
                            f"id: {event_id(execution_id, next_sequence)}\n"
                            f"event: {envelope['type']}\n"
                            f"data: {payload}\n\n"
                        )
                    next_keepalive = loop.time() + settings.execution_event_heartbeat_seconds
                    if (
                        str(batch[-1]["type"]).startswith("execution.")
                        and batch[-1]["type"] != "execution.started"
                    ):
                        return
                    if len(batch) >= settings.execution_event_batch_size:
                        continue
                if status == "awaiting_input" or status in TERMINAL_STATUSES:
                    return
                if loop.time() >= next_keepalive:
                    yield ": keepalive\n\n"
                    next_keepalive = loop.time() + settings.execution_event_heartbeat_seconds
                await asyncio.sleep(settings.execution_event_poll_interval_seconds)
        except asyncio.CancelledError:
            raise

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/qa/executions/{executionId}/export")
def export_execution(
    execution_id: UUID = Path(alias="executionId"), db: Session = Depends(get_session)
) -> Response:
    execution = db.get(QaExecution, execution_id)
    if not execution:
        raise NotFoundError("执行记录不存在")
    result = execution.result_json or {}
    rows = result.get("rows", [])
    columns = [column["key"] for column in result.get("columns", [])]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    filename = f"execution-{execution_id}.csv"
    return Response(
        content="\ufeff" + stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/qa/messages/{messageId}/resubmit", response_model=QueryAccepted, status_code=202)
def resubmit_message(
    body: MessageResubmitRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    message_id: UUID = Path(alias="messageId"),
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QueryAccepted:
    submission = QueryService(db, settings).resubmit(
        message_id,
        body.question,
        body.data_source_ids,
        body.generate_chart,
        body.branch_title,
        idempotency_key,
        request.state.request_id,
        body.context_message_ids,
    )
    if not submission.replayed and submission.accepted.status == "queued":
        background_tasks.add_task(
            QueryService(db, settings).run,
            submission.accepted.execution_id,
            body.generate_chart,
        )
    return submission.accepted


@router.post("/qa/messages/{messageId}/regenerate", response_model=QueryAccepted, status_code=202)
def regenerate_answer(
    background_tasks: BackgroundTasks,
    request: Request,
    message_id: UUID = Path(alias="messageId"),
    body: RegenerateRequest | None = None,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=128),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> QueryAccepted:
    generate_chart = body.generate_chart if body else True
    submission = QueryService(db, settings).regenerate(
        message_id,
        generate_chart,
        body.model_config_id if body else None,
        idempotency_key,
        request.state.request_id,
    )
    if not submission.replayed and submission.accepted.status == "queued":
        background_tasks.add_task(
            QueryService(db, settings).run,
            submission.accepted.execution_id,
            generate_chart,
        )
    return submission.accepted


@router.get("/qa/messages/{messageId}/versions", response_model=list[AnswerVersion])
def list_answer_versions(
    message_id: UUID = Path(alias="messageId"),
    db: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[AnswerVersion]:
    return QueryService(db, settings).list_answer_versions(message_id)
