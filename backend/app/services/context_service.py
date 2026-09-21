from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import QaExecution, QaMessage
from app.text2sql.types import PromptContextItem

MAX_CONTEXT_MESSAGES = 6
MAX_CONVERSATION_CONTEXT_MESSAGES = 8
MAX_CONTEXT_CONTENT_LENGTH = 1000


def validate_context_message_ids(db: Session, session_id: UUID, context_ids: list[UUID]) -> None:
    if not context_ids:
        return
    allowed_ids = set(
        db.scalars(
            select(QaMessage.id)
            .join(QaExecution, QaExecution.id == QaMessage.execution_id)
            .where(
                QaMessage.id.in_(context_ids),
                QaMessage.session_id == session_id,
                QaMessage.role.in_(("user", "assistant")),
                QaExecution.status == "completed",
                QaExecution.intent == "data_query",
            )
        )
    )
    if allowed_ids != set(context_ids):
        raise AppError(
            "CONTEXT_NOT_ALLOWED",
            "上下文消息不属于当前会话或不是已完成的数据查询",
            422,
        )


def resolve_context_messages(
    db: Session, execution: QaExecution
) -> tuple[list[PromptContextItem], list[UUID], list[dict[str, Any]]]:
    explicit_ids = [UUID(value) for value in execution.context_message_ids]
    if explicit_ids:
        validate_context_message_ids(db, execution.session_id, explicit_ids)
        selected_ids = explicit_ids[-MAX_CONTEXT_MESSAGES:]
        messages = list(db.scalars(select(QaMessage).where(QaMessage.id.in_(selected_ids))))
        by_id = {message.id: message for message in messages}
        ordered_messages = [by_id[item] for item in selected_ids if item in by_id]
        selection = "explicit_context"
    elif execution.regenerated_from_execution_id is not None:
        # An empty copied snapshot is still a snapshot. It must not be reinterpreted as
        # "select current history", or regeneration can absorb messages created later.
        selected_ids = []
        ordered_messages = []
        selection = "regenerated_snapshot"
    else:
        ordered_messages = list(
            reversed(
                list(
                    db.scalars(
                        select(QaMessage)
                        .join(QaExecution, QaExecution.id == QaMessage.execution_id)
                        .where(
                            QaMessage.session_id == execution.session_id,
                            QaMessage.id != execution.user_message_id,
                            QaMessage.role.in_(("user", "assistant")),
                            QaExecution.status == "completed",
                            QaExecution.intent == "data_query",
                            QaExecution.created_at < execution.created_at,
                        )
                        .order_by(QaMessage.created_at.desc(), QaMessage.id.desc())
                        .limit(MAX_CONTEXT_MESSAGES)
                    )
                )
            )
        )
        selected_ids = [message.id for message in ordered_messages]
        selection = "session_history"

    items: list[PromptContextItem] = []
    provenance: list[dict[str, Any]] = []
    for message in ordered_messages:
        source_execution = db.get(QaExecution, message.execution_id)
        if source_execution is None:
            continue
        item_provenance = {
            "messageId": str(message.id),
            "sessionId": str(message.session_id),
            "executionId": str(source_execution.id),
            "selection": selection,
        }
        items.append(
            PromptContextItem(
                channel="history",
                source=selection,
                role=message.role,
                trust="untrusted",
                content=message.content[:MAX_CONTEXT_CONTENT_LENGTH],
                provenance=item_provenance,
            )
        )
        provenance.append(
            {
                "source": selection,
                "role": message.role,
                **item_provenance,
                "includedInPrompt": True,
            }
        )
    return items, selected_ids, provenance


def resolve_conversation_context_messages(
    db: Session, execution: QaExecution
) -> tuple[list[PromptContextItem], list[dict[str, Any]]]:
    """Load recent same-session conversation for classification/non-SQL answers only."""
    if execution.regenerated_from_execution_id is not None:
        return [], []
    messages = list(
        reversed(
            list(
                db.scalars(
                    select(QaMessage)
                    .join(QaExecution, QaExecution.id == QaMessage.execution_id)
                    .where(
                        QaMessage.session_id == execution.session_id,
                        QaMessage.id != execution.user_message_id,
                        QaMessage.role.in_(("user", "assistant")),
                        QaExecution.status == "completed",
                        QaExecution.created_at < execution.created_at,
                    )
                    .order_by(QaMessage.created_at.desc(), QaMessage.id.desc())
                    .limit(MAX_CONVERSATION_CONTEXT_MESSAGES)
                )
            )
        )
    )
    items: list[PromptContextItem] = []
    provenance: list[dict[str, Any]] = []
    for message in messages:
        source_execution = db.get(QaExecution, message.execution_id)
        if source_execution is None:
            continue
        item_provenance = {
            "messageId": str(message.id),
            "sessionId": str(message.session_id),
            "executionId": str(source_execution.id),
            "selection": "session_conversation_history",
            "sqlEligible": False,
        }
        items.append(
            PromptContextItem(
                channel="history",
                source="session_conversation_history",
                role=message.role,
                trust="untrusted",
                content=message.content[:MAX_CONTEXT_CONTENT_LENGTH],
                provenance=item_provenance,
            )
        )
        provenance.append(
            {
                "source": "session_conversation_history",
                "role": message.role,
                **item_provenance,
                "includedInPrompt": True,
                "promptScope": "intent_and_non_data_only",
            }
        )
    return items, provenance
