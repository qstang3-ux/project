from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import QaExecutionEffect


def begin_execution_effect(
    db: Session,
    *,
    execution_id: UUID,
    effect_key: str,
    node_name: str,
    attempt: int,
    owner_id: str,
) -> QaExecutionEffect:
    now = datetime.now(UTC)
    db.execute(
        insert(QaExecutionEffect)
        .values(
            id=uuid4(),
            execution_id=execution_id,
            effect_key=effect_key,
            node_name=node_name,
            attempt=attempt,
            status="started",
            owner_id=owner_id,
            started_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(
            index_elements=[QaExecutionEffect.execution_id, QaExecutionEffect.effect_key]
        )
    )
    effect = db.scalar(select_effect(execution_id=execution_id, effect_key=effect_key))
    if effect is None:
        raise RuntimeError("execution effect was not persisted")
    if effect.status == "started" and effect.owner_id != owner_id:
        effect.owner_id = owner_id
        effect.updated_at = now
    db.commit()
    return effect


def select_effect(*, execution_id: UUID, effect_key: str) -> Select[tuple[QaExecutionEffect]]:
    return select(QaExecutionEffect).where(
        QaExecutionEffect.execution_id == execution_id,
        QaExecutionEffect.effect_key == effect_key,
    )


def complete_execution_effect(
    effect: QaExecutionEffect,
    payload: dict[str, object],
) -> None:
    now = datetime.now(UTC)
    effect.status = "completed"
    effect.payload_json = payload
    effect.error_code = None
    effect.completed_at = now
    effect.updated_at = now


def fail_execution_effect(
    effect: QaExecutionEffect,
    *,
    error_code: str,
    payload: dict[str, object],
) -> None:
    now = datetime.now(UTC)
    effect.status = "failed"
    effect.payload_json = payload
    effect.error_code = error_code
    effect.completed_at = now
    effect.updated_at = now
