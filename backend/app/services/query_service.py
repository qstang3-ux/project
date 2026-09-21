import logging
import os
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, TypeVar, cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_query_engine, new_session
from app.core.errors import AppError, NotFoundError
from app.core.security import decrypt_secret
from app.models import (
    DataSource,
    IdempotencyRecord,
    ModelConfig,
    QaExecution,
    QaExecutionStep,
    QaMessage,
    QaSession,
)
from app.repositories.qa import (
    claim_execution_lease,
    compare_and_set_execution_status,
    get_execution,
    get_session,
    heartbeat_execution_lease,
    recoverable_execution_ids,
)
from app.schemas.common import TokenUsage
from app.schemas.qa import (
    AnswerVersion,
    ExecutionDetail,
    ExecutionStepOut,
    QueryAccepted,
    ResultSet,
)
from app.services.context_service import (
    resolve_context_messages,
    validate_context_message_ids,
)
from app.services.execution_events import append_started_event, append_terminal_event
from app.services.execution_steps import execution_step_duration_ms
from app.services.idempotency import claim_idempotency
from app.text2sql.adapters import FakeModelAdapter, ModelAdapter, OpenAICompatibleAdapter
from app.text2sql.agent import LangGraphQueryRunner
from app.text2sql.types import ModelAnswerOutput, ModelSqlOutput

logger = logging.getLogger(__name__)
PROCESS_WORKER_ID = f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
TModelOutput = TypeVar("TModelOutput", ModelSqlOutput, ModelAnswerOutput)
STEP_ORDER = [
    "schema_selection",
    "sql_generation",
    "sql_validation",
    "query_execution",
    "answer_generation",
]


@dataclass(frozen=True)
class QuerySubmission:
    accepted: QueryAccepted
    replayed: bool


class QueryService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.worker_id = settings.execution_worker_id or PROCESS_WORKER_ID

    def list_answer_versions(self, message_id: UUID) -> list[AnswerVersion]:
        source = self.db.scalar(
            select(QaExecution)
            .where(
                (QaExecution.user_message_id == message_id)
                | (QaExecution.assistant_message_id == message_id)
            )
            .order_by(QaExecution.created_at.desc())
        )
        if source is None:
            raise NotFoundError("回答版本不存在")

        executions = list(
            self.db.scalars(
                select(QaExecution)
                .where(QaExecution.session_id == source.session_id)
                .order_by(QaExecution.created_at, QaExecution.id)
            )
        )
        by_id = {item.id: item for item in executions}
        root = source
        visited: set[UUID] = set()
        while root.regenerated_from_execution_id is not None:
            if root.id in visited:
                raise AppError("ANSWER_VERSION_LINEAGE_INVALID", "回答版本链路异常", 409)
            visited.add(root.id)
            parent = by_id.get(root.regenerated_from_execution_id)
            if parent is None:
                break
            root = parent

        lineage_ids = {root.id}
        changed = True
        while changed:
            changed = False
            for item in executions:
                if item.regenerated_from_execution_id in lineage_ids and item.id not in lineage_ids:
                    lineage_ids.add(item.id)
                    changed = True

        versions = [
            item
            for item in executions
            if item.id in lineage_ids
            and item.status == "completed"
            and item.assistant_message_id is not None
            and item.answer is not None
        ]
        if not versions:
            raise NotFoundError("回答版本不存在")
        return [
            AnswerVersion(
                version_no=index,
                execution_id=item.id,
                answer=item.answer or "",
                sql=item.executed_sql,
                chart=item.chart_json,
                model_name=item.model_name,
                duration_ms=item.duration_ms,
                is_current=index == len(versions),
                created_at=item.created_at,
            )
            for index, item in enumerate(versions, start=1)
        ]

    def create(
        self,
        session_id: UUID,
        question: str,
        data_source_ids: list[UUID],
        generate_chart: bool,
        idempotency_key: str,
        request_id: str,
        context_message_ids: list[UUID] | None = None,
    ) -> QuerySubmission:
        context_ids = context_message_ids or []
        claim = claim_idempotency(
            self.db,
            idempotency_key=idempotency_key,
            operation="query.create",
            resource_id=str(session_id),
            request_body={
                "question": question,
                "dataSourceIds": data_source_ids,
                "generateChart": generate_chart,
                "contextMessageIds": context_ids,
            },
        )
        if not claim.created:
            return QuerySubmission(self._accepted_from_record(claim.record), True)
        try:
            execution = self._create_execution(
                session_id,
                question,
                data_source_ids,
                generate_chart,
                idempotency_key,
                request_id,
                context_ids,
            )
            self._bind_record(claim.record, execution)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return QuerySubmission(self._accepted(execution), False)

    def resubmit(
        self,
        source_message_id: UUID,
        question: str,
        data_source_ids: list[UUID],
        generate_chart: bool,
        branch_title: str | None,
        idempotency_key: str,
        request_id: str,
        context_message_ids: list[UUID] | None = None,
    ) -> QuerySubmission:
        context_ids = context_message_ids or []
        claim = claim_idempotency(
            self.db,
            idempotency_key=idempotency_key,
            operation="message.resubmit",
            resource_id=str(source_message_id),
            request_body={
                "question": question,
                "dataSourceIds": data_source_ids,
                "generateChart": generate_chart,
                "contextMessageIds": context_ids,
                "branchTitle": branch_title,
            },
        )
        if not claim.created:
            return QuerySubmission(self._accepted_from_record(claim.record), True)
        try:
            source = self.db.get(QaMessage, source_message_id)
            if not source or source.role != "user":
                raise NotFoundError("原问题消息不存在")
            parent = self.db.get(QaSession, source.session_id)
            if not parent:
                raise NotFoundError("原会话不存在")
            branch = QaSession(
                owner_id=self.settings.fixed_user_id,
                title=branch_title or question[:60],
                parent_session_id=parent.id,
                updated_at=datetime.now(UTC),
            )
            self.db.add(branch)
            self.db.flush()
            execution = self._create_execution(
                branch.id,
                question,
                data_source_ids,
                generate_chart,
                idempotency_key,
                request_id,
                context_ids,
                source_message_id=source.id,
            )
            self._bind_record(claim.record, execution)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return QuerySubmission(self._accepted(execution), False)

    def regenerate(
        self,
        message_id: UUID,
        generate_chart: bool,
        model_config_id: UUID | None,
        idempotency_key: str,
        request_id: str,
    ) -> QuerySubmission:
        claim = claim_idempotency(
            self.db,
            idempotency_key=idempotency_key,
            operation="message.regenerate",
            resource_id=str(message_id),
            request_body={
                "generateChart": generate_chart,
                "modelConfigId": model_config_id,
            },
        )
        if not claim.created:
            return QuerySubmission(self._accepted_from_record(claim.record), True)
        try:
            message = self.db.get(QaMessage, message_id)
            if not message:
                raise NotFoundError("消息不存在")
            original = self.db.scalar(
                select(QaExecution)
                .where(
                    (QaExecution.user_message_id == message_id)
                    | (QaExecution.assistant_message_id == message_id)
                )
                .order_by(QaExecution.created_at.desc())
            )
            if not original:
                raise NotFoundError("原执行记录不存在")
            context_ids = [UUID(value) for value in original.context_message_ids]
            if not context_ids:
                _, context_ids, _ = resolve_context_messages(self.db, original)
            execution = self._create_execution(
                original.session_id,
                original.question,
                [UUID(value) for value in original.data_source_ids],
                generate_chart,
                idempotency_key,
                request_id,
                context_ids,
                regenerated_from_execution_id=original.id,
            )
            self._bind_record(claim.record, execution)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return QuerySubmission(self._accepted(execution), False)

    def _create_execution(
        self,
        session_id: UUID,
        question: str,
        data_source_ids: list[UUID],
        generate_chart: bool,
        idempotency_key: str,
        request_id: str,
        context_ids: list[UUID],
        *,
        source_message_id: UUID | None = None,
        regenerated_from_execution_id: UUID | None = None,
    ) -> QaExecution:
        session = get_session(self.db, session_id, self.settings.fixed_user_id)
        if not session:
            raise NotFoundError("会话不存在")
        sources = list(
            self.db.scalars(select(DataSource).where(DataSource.id.in_(data_source_ids)))
        )
        if len(sources) != len(set(data_source_ids)) or any(
            not source.enabled for source in sources
        ):
            raise AppError("DATA_SOURCE_UNAVAILABLE", "数据源不可用", 503)
        validate_context_message_ids(self.db, session_id, context_ids)
        now = datetime.now(UTC)
        message = QaMessage(
            session_id=session_id,
            role="user",
            content=question,
            source_message_id=source_message_id,
        )
        self.db.add(message)
        self.db.flush()
        execution = QaExecution(
            request_id=request_id,
            idempotency_key=idempotency_key,
            generate_chart=generate_chart,
            session_id=session_id,
            user_message_id=message.id,
            status="queued",
            question=question,
            data_source_ids=[str(item) for item in data_source_ids],
            context_message_ids=[str(item) for item in context_ids],
            regenerated_from_execution_id=regenerated_from_execution_id,
        )
        self.db.add(execution)
        self.db.flush()
        append_started_event(self.db, execution)
        message.execution_id = execution.id
        if session.title == "新对话":
            session.title = question[:60]
        session.updated_at = now
        return execution

    def submit_clarification(
        self,
        execution_id: UUID,
        content: str,
        idempotency_key: str,
    ) -> QuerySubmission:
        claim = claim_idempotency(
            self.db,
            idempotency_key=idempotency_key,
            operation="execution.clarify",
            resource_id=str(execution_id),
            request_body={"content": content},
        )
        if not claim.created:
            return QuerySubmission(self._accepted_from_record(claim.record), True)
        try:
            execution = get_execution(self.db, execution_id)
            if not execution:
                raise NotFoundError("执行记录不存在")
            if execution.status != "awaiting_input":
                raise AppError("EXECUTION_NOT_AWAITING_INPUT", "当前执行不处于等待补充状态", 409)
            if execution.clarification_round >= self.settings.clarification_max_rounds:
                raise AppError("CLARIFICATION_LIMIT_REACHED", "当前执行已达到澄清轮次上限", 409)
            message = QaMessage(
                session_id=execution.session_id,
                role="user",
                content=content,
                execution_id=execution.id,
            )
            self.db.add(message)
            self.db.flush()
            history = [
                *execution.clarification_history,
                {
                    "idempotencyKey": idempotency_key,
                    "messageId": str(message.id),
                    "content": content,
                    "createdAt": datetime.now(UTC).isoformat(),
                },
            ]
            provenance = [
                *execution.context_provenance,
                {
                    "source": "clarification",
                    "role": "user",
                    "messageId": str(message.id),
                    "sessionId": str(execution.session_id),
                    "executionId": str(execution.id),
                    "round": execution.clarification_round + 1,
                    "includedInPrompt": True,
                },
            ]
            with self.db.no_autoflush:
                transitioned = compare_and_set_execution_status(
                    self.db,
                    execution.id,
                    ("awaiting_input",),
                    "queued",
                    clarification_history=history,
                    context_provenance=provenance,
                    checkpoint_status="resume_pending",
                    clarification_json=None,
                    error_code=None,
                    error_message=None,
                )
            if not transitioned:
                raise AppError("EXECUTION_NOT_AWAITING_INPUT", "当前执行不处于等待补充状态", 409)
            claim.record.session_id = execution.session_id
            claim.record.user_message_id = message.id
            claim.record.execution_id = execution.id
            self.db.commit()
            self.db.refresh(execution)
        except Exception:
            self.db.rollback()
            raise
        return QuerySubmission(self._accepted(execution, message.id), False)

    def cancel(self, execution_id: UUID) -> QaExecution:
        execution = get_execution(self.db, execution_id)
        if not execution:
            raise NotFoundError("执行记录不存在")
        now = datetime.now(UTC)
        transitioned = compare_and_set_execution_status(
            self.db,
            execution_id,
            ("queued", "running", "awaiting_input"),
            "cancelled",
            completed_at=now,
            checkpoint_status="cancelled",
            error_code="EXECUTION_CANCELLED",
            error_message="执行已取消",
            lease_owner=None,
            lease_expires_at=None,
            heartbeat_at=None,
        )
        if transitioned:
            self.db.refresh(execution)
            append_terminal_event(self.db, execution, status="cancelled", created_at=now)
            self.db.commit()
            self.db.refresh(execution)
        else:
            self.db.rollback()
            self.db.refresh(execution)
        return execution

    def run(
        self,
        execution_id: UUID,
        generate_chart: bool | None = None,
        resume_with_input: bool = False,
    ) -> bool:
        started = time.perf_counter()
        with new_session() as db:
            execution = get_execution(db, execution_id)
            if not execution or execution.status not in ("queued", "running"):
                return False
            resume_with_input = resume_with_input or execution.checkpoint_status == "resume_pending"
            if not claim_execution_lease(
                db,
                execution.id,
                self.worker_id,
                self.settings.execution_lease_seconds,
                self.settings.graph_version,
            ):
                db.rollback()
                return False
            db.commit()
            db.refresh(execution)
            stop_heartbeat = threading.Event()
            heartbeat = threading.Thread(
                target=self._heartbeat_loop,
                args=(execution.id, stop_heartbeat),
                name=f"execution-heartbeat-{execution.id}",
                daemon=True,
            )
            heartbeat.start()
            try:
                LangGraphQueryRunner(
                    db,
                    self.settings,
                    execution,
                    execution.generate_chart if generate_chart is None else generate_chart,
                    get_query_engine(),
                    self.worker_id,
                ).run(resume_with_input=resume_with_input)
                db.refresh(execution)
                if execution.status != "cancelled":
                    execution.duration_ms = int((time.perf_counter() - started) * 1000)
                    db.commit()
            except AppError as exc:
                db.rollback()
                if exc.code not in ("EXECUTION_CANCELLED", "EXECUTION_LEASE_LOST"):
                    target = "rejected" if exc.code == "SQL_VALIDATION_FAILED" else "failed"
                    transitioned = compare_and_set_execution_status(
                        db,
                        execution_id,
                        ("running",),
                        target,
                        expected_lease_owner=self.worker_id,
                        error_code=exc.code,
                        error_message=exc.message,
                        checkpoint_status=f"failed:{exc.code}",
                        completed_at=datetime.now(UTC),
                        duration_ms=int((time.perf_counter() - started) * 1000),
                        lease_owner=None,
                        lease_expires_at=None,
                        heartbeat_at=None,
                    )
                    if transitioned:
                        db.refresh(execution)
                        append_terminal_event(
                            db,
                            execution,
                            status=target,
                            created_at=execution.completed_at or datetime.now(UTC),
                        )
                    db.commit()
            except Exception:
                logger.exception("query execution failed", extra={"event": "query.failed"})
                db.rollback()
                transitioned = compare_and_set_execution_status(
                    db,
                    execution_id,
                    ("running",),
                    "failed",
                    expected_lease_owner=self.worker_id,
                    error_code="INTERNAL_ERROR",
                    error_message="问数执行失败",
                    checkpoint_status="failed:INTERNAL_ERROR",
                    completed_at=datetime.now(UTC),
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    lease_owner=None,
                    lease_expires_at=None,
                    heartbeat_at=None,
                )
                if transitioned:
                    db.refresh(execution)
                    append_terminal_event(
                        db,
                        execution,
                        status="failed",
                        created_at=execution.completed_at or datetime.now(UTC),
                    )
                db.commit()
            finally:
                stop_heartbeat.set()
                heartbeat.join(timeout=self.settings.execution_heartbeat_seconds + 1)
            return True

    def recover_available(self, limit: int | None = None) -> tuple[int, int]:
        batch_size = limit or self.settings.execution_recovery_batch_size
        execution_ids = recoverable_execution_ids(self.db, batch_size)
        self.db.rollback()
        claimed = sum(self.run(execution_id) for execution_id in execution_ids)
        return len(execution_ids), claimed

    def _heartbeat_loop(self, execution_id: UUID, stop: threading.Event) -> None:
        while not stop.wait(self.settings.execution_heartbeat_seconds):
            with new_session() as heartbeat_db:
                renewed = heartbeat_execution_lease(
                    heartbeat_db,
                    execution_id,
                    self.worker_id,
                    self.settings.execution_lease_seconds,
                )
                heartbeat_db.commit()
                if not renewed:
                    return

    @staticmethod
    def _accepted(execution: QaExecution, message_id: UUID | None = None) -> QueryAccepted:
        return QueryAccepted(
            session_id=execution.session_id,
            user_message_id=message_id or execution.user_message_id,
            execution_id=execution.id,
            status=execution.status,
            event_url=f"/api/v1/qa/executions/{execution.id}/events",
        )

    def _accepted_from_record(self, record: IdempotencyRecord) -> QueryAccepted:
        if record.execution_id is None or record.user_message_id is None:
            raise AppError("INTERNAL_ERROR", "幂等请求记录不完整", 500)
        execution = get_execution(self.db, record.execution_id)
        if execution is None:
            raise AppError("INTERNAL_ERROR", "幂等请求关联的执行不存在", 500)
        return self._accepted(execution, record.user_message_id)

    @staticmethod
    def _bind_record(record: IdempotencyRecord, execution: QaExecution) -> None:
        record.session_id = execution.session_id
        record.user_message_id = execution.user_message_id
        record.execution_id = execution.id

    def _adapter(self, db: Session, execution: QaExecution) -> ModelAdapter:
        if self.settings.default_model_config == "fake":
            if self.settings.app_env not in ("local", "test"):
                raise AppError("FAKE_MODEL_FORBIDDEN", "当前环境禁止使用 Fake 模型", 503)
            return FakeModelAdapter()
        model = db.scalar(
            select(ModelConfig).where(ModelConfig.active.is_(True), ModelConfig.enabled.is_(True))
        )
        if model:
            execution.model_config_id = model.id
            key = decrypt_secret(model.encrypted_api_key or "", self.settings.model_secret_key)
            return OpenAICompatibleAdapter(
                model.base_url,
                key,
                model.model_name,
                model.timeout_seconds,
                cast(Literal["responses", "chat_completions"], model.protocol),
                self.settings.model_http_max_attempts_per_call,
            )
        runtime_key = self.settings.real_model_api_key
        if (
            self.settings.real_model_base_url
            and runtime_key is not None
            and runtime_key.get_secret_value()
            and self.settings.real_model_name
        ):
            return OpenAICompatibleAdapter(
                self.settings.real_model_base_url,
                runtime_key.get_secret_value(),
                self.settings.real_model_name,
                self.settings.real_model_timeout_seconds,
                self.settings.real_model_protocol,
                self.settings.model_http_max_attempts_per_call,
            )
        raise AppError("MODEL_NOT_CONFIGURED", "未配置可用真实模型", 409)

    def _call_model(
        self,
        db: Session,
        execution: QaExecution,
        adapter: ModelAdapter,
        purpose: str,
        call: Callable[[], TModelOutput],
    ) -> TModelOutput:
        started = time.perf_counter()
        try:
            output = call()
        except AppError as exc:
            self._record_model_call(
                db,
                execution,
                adapter,
                purpose,
                int((time.perf_counter() - started) * 1000),
                0,
                0,
                "failed",
                exc.code,
            )
            raise
        self._record_model_call(
            db,
            execution,
            adapter,
            purpose,
            int((time.perf_counter() - started) * 1000),
            output.prompt_tokens,
            output.completion_tokens,
            "success",
            None,
        )
        return output

    @staticmethod
    def _record_model_call(
        db: Session,
        execution: QaExecution,
        adapter: ModelAdapter,
        purpose: str,
        duration_ms: int,
        prompt_tokens: int,
        completion_tokens: int,
        status: str,
        error_code: str | None,
    ) -> None:
        entry = {
            "provider": adapter.provider_name,
            "model": adapter.model_name,
            "purpose": purpose,
            "durationMs": duration_ms,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "totalTokens": prompt_tokens + completion_tokens,
            "retryCount": adapter.last_retry_count,
            "status": status,
            "errorCode": error_code,
        }
        execution.model_call_audit = [*execution.model_call_audit, entry]
        usage = execution.token_usage or {}
        execution.token_usage = {
            "promptTokens": int(usage.get("promptTokens", 0)) + prompt_tokens,
            "completionTokens": int(usage.get("completionTokens", 0)) + completion_tokens,
            "totalTokens": int(usage.get("totalTokens", 0)) + prompt_tokens + completion_tokens,
        }
        db.commit()
        logger.info(
            "model call completed",
            extra={
                "event": "model.call",
                "execution_id": str(execution.id),
                "request_id": execution.request_id,
                **entry,
            },
        )

    @staticmethod
    def _mark_last_model_call_invalid(db: Session, execution: QaExecution) -> None:
        calls = list(execution.model_call_audit)
        if calls:
            calls[-1] = {
                **calls[-1],
                "status": "invalid_output",
                "errorCode": "MODEL_INVALID_RESPONSE",
            }
            execution.model_call_audit = calls
            db.commit()

    @staticmethod
    def _ensure_not_cancelled(db: Session, execution: QaExecution) -> None:
        db.refresh(execution)
        if execution.status == "cancelled":
            raise AppError("EXECUTION_CANCELLED", "执行已取消", 409)

    @staticmethod
    def _step(db: Session, execution: QaExecution, step_type: str, summary: str) -> None:
        now = datetime.now(UTC)
        db.add(
            QaExecutionStep(
                execution_id=execution.id,
                effect_key=f"legacy:{uuid4()}",
                step_type=step_type,
                status="completed",
                summary=summary,
                started_at=now,
                completed_at=now,
            )
        )
        db.commit()


def execution_detail(db: Session, execution_id: UUID) -> ExecutionDetail:
    execution = get_execution(db, execution_id)
    if not execution:
        raise NotFoundError("执行记录不存在")
    steps = list(
        db.scalars(
            select(QaExecutionStep)
            .where(QaExecutionStep.execution_id == execution_id)
            .order_by(QaExecutionStep.started_at)
        )
    )
    result = ResultSet.model_validate(execution.result_json) if execution.result_json else None
    error = (
        {
            "code": execution.error_code,
            "message": execution.error_message,
            "requestId": execution.request_id,
            "details": None,
        }
        if execution.error_code
        else None
    )
    return ExecutionDetail(
        id=execution.id,
        request_id=execution.request_id,
        session_id=execution.session_id,
        user_message_id=execution.user_message_id,
        assistant_message_id=execution.assistant_message_id,
        question=execution.question,
        intent=execution.intent,
        normalized_question=execution.normalized_question,
        missing_slots=execution.missing_slots,
        clarification_round=execution.clarification_round,
        clarification=execution.clarification_json,
        data_source_ids=[UUID(value) for value in execution.data_source_ids],
        status=execution.status,
        sql_validation_status=(
            "rejected"
            if execution.error_code == "SQL_VALIDATION_FAILED"
            else "passed"
            if execution.validation_summary
            else "not_started"
        ),
        steps=[
            ExecutionStepOut(
                type=s.step_type,
                status=s.status,
                summary=s.summary,
                started_at=s.started_at,
                completed_at=s.completed_at,
                duration_ms=execution_step_duration_ms(s, execution.model_call_audit),
            )
            for s in steps
        ],
        selected_objects=execution.selected_objects,
        sql=execution.executed_sql,
        result=result,
        answer=execution.answer,
        chart=execution.chart_json,
        follow_up_questions=execution.follow_up_questions,
        model_name=execution.model_name,
        token_usage=TokenUsage.model_validate(execution.token_usage or {}),
        current_version_no=1 if execution.assistant_message_id else None,
        duration_ms=execution.duration_ms,
        error=error,
        created_at=execution.created_at,
        completed_at=execution.completed_at,
    )
