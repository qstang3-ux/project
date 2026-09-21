import re
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError
from app.models import (
    DataSource,
    FavoriteQuestion,
    QaExecution,
    QaExecutionStep,
    QaFeedback,
    QaMessage,
    QaSession,
)
from app.schemas.admin import (
    FavoriteOut,
    FeedbackCreate,
    FeedbackDetail,
    FeedbackListResponse,
    FeedbackSummary,
    FeedbackUpdate,
    FrequentQuestionOut,
    QaLogDetail,
    QaLogListResponse,
    QaLogSummary,
)
from app.schemas.common import PageMeta, TokenUsage
from app.schemas.qa import ExecutionStepOut
from app.services.execution_steps import execution_step_duration_ms


def normalize_question(question: str) -> str:
    return re.sub(r"\s+", "", question).strip().lower()


def favorite_out(model: FavoriteQuestion) -> FavoriteOut:
    return FavoriteOut(
        id=model.id,
        question=model.display_question,
        source_message_id=model.source_message_id,
        created_at=model.created_at,
    )


class SupportService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def favorites(self) -> list[FavoriteOut]:
        rows = self.db.scalars(
            select(FavoriteQuestion)
            .where(FavoriteQuestion.owner_id == self.settings.fixed_user_id)
            .order_by(FavoriteQuestion.created_at.desc())
        )
        return [favorite_out(item) for item in rows]

    def add_favorite(
        self, question: str, source_message_id: UUID | None
    ) -> tuple[FavoriteOut, bool]:
        normalized = normalize_question(question)
        existing = self.db.scalar(
            select(FavoriteQuestion).where(
                FavoriteQuestion.owner_id == self.settings.fixed_user_id,
                FavoriteQuestion.normalized_question == normalized,
            )
        )
        if existing:
            return favorite_out(existing), False
        model = FavoriteQuestion(
            owner_id=self.settings.fixed_user_id,
            normalized_question=normalized,
            display_question=question,
            source_message_id=source_message_id,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return favorite_out(model), True

    def remove_favorite(self, favorite_id: UUID) -> None:
        model = self.db.get(FavoriteQuestion, favorite_id)
        if model and model.owner_id == self.settings.fixed_user_id:
            self.db.delete(model)
            self.db.commit()

    def frequent(self, limit: int) -> list[FrequentQuestionOut]:
        since = datetime.now(UTC) - timedelta(days=30)
        normalized = func.regexp_replace(func.lower(QaExecution.question), r"\s+", "", "g")
        rows = self.db.execute(
            select(func.min(QaExecution.question), func.count(), func.max(QaExecution.created_at))
            .where(QaExecution.status == "completed", QaExecution.created_at >= since)
            .group_by(normalized)
            .having(func.count() >= 3)
            .order_by(func.count().desc())
            .limit(limit)
        ).all()
        return [
            FrequentQuestionOut(question=row[0], count=row[1], last_asked_at=row[2]) for row in rows
        ]

    def create_feedback(self, body: FeedbackCreate) -> FeedbackDetail:
        execution = self.db.get(QaExecution, body.execution_id)
        assistant = self.db.get(QaMessage, body.assistant_message_id)
        if (
            not execution
            or not assistant
            or execution.session_id != body.session_id
            or execution.assistant_message_id != assistant.id
        ):
            raise NotFoundError("反馈关联的回答不存在")
        now = datetime.now(UTC)
        model = QaFeedback(
            session_id=body.session_id,
            assistant_message_id=body.assistant_message_id,
            execution_id=body.execution_id,
            reason=body.reason,
            description=body.description,
            status="pending",
            version=1,
            updated_at=now,
        )
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self.feedback_detail(model.id)

    def feedback_detail(self, feedback_id: UUID) -> FeedbackDetail:
        model = self.db.get(QaFeedback, feedback_id)
        if not model:
            raise NotFoundError("反馈不存在")
        execution = self.db.get(QaExecution, model.execution_id)
        assistant = self.db.get(QaMessage, model.assistant_message_id)
        if not execution or not assistant:
            raise NotFoundError("反馈关联记录不存在")
        owner_id = self.db.scalar(
            select(QaSession.owner_id).where(QaSession.id == execution.session_id)
        )
        if owner_id is None:
            raise NotFoundError("反馈所属会话不存在")
        names = self._source_names(execution.data_source_ids)
        return FeedbackDetail(
            id=model.id,
            user_id=owner_id,
            question=execution.question,
            reason=model.reason,
            description=model.description,
            status=model.status,
            version=model.version,
            created_at=model.created_at,
            updated_at=model.updated_at,
            session_id=model.session_id,
            assistant_message_id=model.assistant_message_id,
            execution_id=model.execution_id,
            data_source_names=names,
            sql=execution.executed_sql,
            result_summary=f"{execution.row_count or 0} 行",
            model_name=execution.model_name,
            answer=assistant.content,
            resolution_note=model.resolution_note,
        )

    def list_feedback(
        self,
        page: int,
        page_size: int,
        keyword: str | None,
        status: str | None,
        reason: str | None,
        user_id: str | None,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> FeedbackListResponse:
        query = (
            select(QaFeedback, QaExecution.question, QaSession.owner_id)
            .join(QaExecution, QaExecution.id == QaFeedback.execution_id)
            .join(QaSession, QaSession.id == QaExecution.session_id)
        )
        count_query = (
            select(func.count())
            .select_from(QaFeedback)
            .join(QaExecution, QaExecution.id == QaFeedback.execution_id)
            .join(QaSession, QaSession.id == QaExecution.session_id)
        )
        filters: list[ColumnElement[bool]] = []
        if keyword:
            filters.append(QaExecution.question.ilike(f"%{keyword}%"))
        if status:
            filters.append(QaFeedback.status == status)
        if reason:
            filters.append(QaFeedback.reason == reason)
        if user_id:
            filters.append(QaSession.owner_id == user_id)
        if from_at:
            filters.append(QaFeedback.created_at >= from_at)
        if to_at:
            filters.append(QaFeedback.created_at <= to_at)
        total = int(self.db.scalar(count_query.where(*filters)) or 0)
        rows = self.db.execute(
            query.where(*filters)
            .order_by(QaFeedback.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        items = [
            FeedbackSummary(
                id=model.id,
                user_id=user_id_value,
                question=question,
                reason=model.reason,
                description=model.description,
                status=model.status,
                version=model.version,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model, question, user_id_value in rows
        ]
        return FeedbackListResponse(
            items=items,
            page=PageMeta(
                page=page, page_size=page_size, total=total, has_more=page * page_size < total
            ),
        )

    def update_feedback(self, feedback_id: UUID, body: FeedbackUpdate) -> FeedbackDetail:
        model = self.db.get(QaFeedback, feedback_id)
        if not model:
            raise NotFoundError("反馈不存在")
        if model.version != body.version:
            raise ConflictError("反馈已被其他请求更新")
        model.status = body.status
        model.resolution_note = body.resolution_note
        model.version += 1
        model.updated_at = datetime.now(UTC)
        self.db.commit()
        return self.feedback_detail(model.id)

    def logs(
        self,
        page: int,
        page_size: int,
        keyword: str | None,
        status: str | None,
        model_config_id: UUID | None,
        user_id: str | None,
        from_at: datetime | None,
        to_at: datetime | None,
    ) -> QaLogListResponse:
        filters: list[ColumnElement[bool]] = []
        if keyword:
            filters.append(QaExecution.question.ilike(f"%{keyword}%"))
        if status:
            filters.append(QaExecution.status == status)
        if model_config_id:
            filters.append(QaExecution.model_config_id == model_config_id)
        if user_id:
            filters.append(QaSession.owner_id == user_id)
        if from_at:
            filters.append(QaExecution.created_at >= from_at)
        if to_at:
            filters.append(QaExecution.created_at <= to_at)
        total = int(
            self.db.scalar(
                select(func.count())
                .select_from(QaExecution)
                .join(QaSession, QaSession.id == QaExecution.session_id)
                .where(*filters)
            )
            or 0
        )
        rows = self.db.execute(
            select(QaExecution, QaSession.owner_id)
            .join(QaSession, QaSession.id == QaExecution.session_id)
            .where(*filters)
            .order_by(QaExecution.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [
            QaLogSummary(
                execution_id=e.id,
                user_id=user_id_value,
                request_id=e.request_id,
                question=e.question,
                status=e.status,
                model_name=e.model_name,
                row_count=e.row_count,
                duration_ms=e.duration_ms,
                error_code=e.error_code,
                created_at=e.created_at,
            )
            for e, user_id_value in rows
        ]
        return QaLogListResponse(
            items=items,
            page=PageMeta(
                page=page, page_size=page_size, total=total, has_more=page * page_size < total
            ),
        )

    def log_detail(self, execution_id: UUID) -> QaLogDetail:
        e = self.db.get(QaExecution, execution_id)
        if not e:
            raise NotFoundError("执行记录不存在")
        steps = self.db.scalars(
            select(QaExecutionStep)
            .where(QaExecutionStep.execution_id == e.id)
            .order_by(QaExecutionStep.started_at)
        )
        usage = e.token_usage or {}
        owner_id = self.db.scalar(select(QaSession.owner_id).where(QaSession.id == e.session_id))
        if owner_id is None:
            raise NotFoundError("执行记录所属会话不存在")
        return QaLogDetail(
            execution_id=e.id,
            user_id=owner_id,
            request_id=e.request_id,
            question=e.question,
            status=e.status,
            model_name=e.model_name,
            row_count=e.row_count,
            duration_ms=e.duration_ms,
            error_code=e.error_code,
            created_at=e.created_at,
            session_id=e.session_id,
            user_message_id=e.user_message_id,
            assistant_message_id=e.assistant_message_id,
            intent=e.intent,
            normalized_question=e.normalized_question,
            missing_slots=e.missing_slots,
            clarification_round=e.clarification_round,
            data_source_names=self._source_names(e.data_source_ids),
            selected_objects=e.selected_objects,
            generated_sql=e.generated_sql,
            executed_sql=e.executed_sql,
            validation_summary=e.validation_summary,
            token_usage=TokenUsage.model_validate(usage),
            model_calls=e.model_call_audit,
            graph_version=e.graph_version,
            graph_node_trace=e.graph_node_trace,
            checkpoint_status=e.checkpoint_status,
            rag_document_ids=[UUID(item) for item in e.rag_document_ids],
            rag_degraded=e.rag_degraded,
            steps=[
                ExecutionStepOut(
                    type=s.step_type,
                    status=s.status,
                    summary=s.summary,
                    started_at=s.started_at,
                    completed_at=s.completed_at,
                    duration_ms=execution_step_duration_ms(s, e.model_call_audit),
                )
                for s in steps
            ],
            error_message=e.error_message,
        )

    def _source_names(self, source_ids: list[str]) -> list[str]:
        ids = [UUID(item) for item in source_ids]
        return list(self.db.scalars(select(DataSource.name).where(DataSource.id.in_(ids))))
