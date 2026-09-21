from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.models import QaExecution, QaExecutionStep, QaMessage, QaSession


def session_query(owner_id: str) -> Select[tuple[QaSession]]:
    return select(QaSession).where(QaSession.owner_id == owner_id, QaSession.deleted_at.is_(None))


def get_session(db: Session, session_id: UUID, owner_id: str) -> QaSession | None:
    return db.scalar(session_query(owner_id).where(QaSession.id == session_id))


def session_message_count(db: Session, session_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(QaMessage).where(QaMessage.session_id == session_id)
        )
        or 0
    )


def latest_message(db: Session, session_id: UUID) -> QaMessage | None:
    return db.scalar(
        select(QaMessage)
        .where(QaMessage.session_id == session_id)
        .order_by(QaMessage.created_at.desc())
        .limit(1)
    )


def session_messages(
    db: Session, session_id: UUID, cursor: UUID | None, limit: int
) -> list[tuple[QaMessage, str | None]]:
    query = (
        select(QaMessage, QaExecution.status)
        .outerjoin(QaExecution, QaExecution.id == QaMessage.execution_id)
        .where(QaMessage.session_id == session_id, QaMessage.role.in_(("user", "assistant")))
    )
    if cursor:
        cursor_message = db.get(QaMessage, cursor)
        if cursor_message and cursor_message.session_id == session_id:
            query = query.where(
                or_(
                    QaMessage.created_at < cursor_message.created_at,
                    and_(
                        QaMessage.created_at == cursor_message.created_at,
                        QaMessage.id < cursor_message.id,
                    ),
                )
            )
    rows = db.execute(
        query.order_by(QaMessage.created_at.desc(), QaMessage.id.desc()).limit(limit + 1)
    )
    return [(message, status) for message, status in rows]


def execution_steps(db: Session, execution_id: UUID) -> list[QaExecutionStep]:
    return list(
        db.scalars(
            select(QaExecutionStep)
            .where(QaExecutionStep.execution_id == execution_id)
            .order_by(QaExecutionStep.started_at, QaExecutionStep.id)
        )
    )


def touch(session: QaSession) -> None:
    session.updated_at = datetime.now(UTC)


def get_execution(db: Session, execution_id: UUID) -> QaExecution | None:
    return db.get(QaExecution, execution_id)


def compare_and_set_execution_status(
    db: Session,
    execution_id: UUID,
    expected_statuses: tuple[str, ...],
    target_status: str,
    expected_lease_owner: str | None = None,
    **values: object,
) -> bool:
    conditions = [QaExecution.id == execution_id, QaExecution.status.in_(expected_statuses)]
    if expected_lease_owner is not None:
        conditions.append(QaExecution.lease_owner == expected_lease_owner)
    result = db.execute(
        update(QaExecution)
        .where(*conditions)
        .values(status=target_status, **values)
        .execution_options(synchronize_session=False)
    )
    return bool(result.rowcount == 1)


def claim_execution_lease(
    db: Session,
    execution_id: UUID,
    owner_id: str,
    lease_seconds: int,
    graph_version: str,
) -> bool:
    database_now = func.now()
    result = db.execute(
        update(QaExecution)
        .where(
            QaExecution.id == execution_id,
            or_(
                QaExecution.status == "queued",
                and_(
                    QaExecution.status == "running",
                    or_(
                        QaExecution.lease_expires_at.is_(None),
                        QaExecution.lease_expires_at <= database_now,
                    ),
                ),
            ),
        )
        .values(
            status="running",
            lease_owner=owner_id,
            lease_expires_at=database_now + timedelta(seconds=lease_seconds),
            heartbeat_at=database_now,
            run_attempt=QaExecution.run_attempt + 1,
            graph_version=graph_version,
            graph_thread_id=str(execution_id),
        )
        .execution_options(synchronize_session=False)
    )
    return bool(result.rowcount == 1)


def heartbeat_execution_lease(
    db: Session,
    execution_id: UUID,
    owner_id: str,
    lease_seconds: int,
) -> bool:
    database_now = func.now()
    result = db.execute(
        update(QaExecution)
        .where(
            QaExecution.id == execution_id,
            QaExecution.status == "running",
            QaExecution.lease_owner == owner_id,
        )
        .values(
            heartbeat_at=database_now,
            lease_expires_at=database_now + timedelta(seconds=lease_seconds),
        )
        .execution_options(synchronize_session=False)
    )
    return bool(result.rowcount == 1)


def recoverable_execution_ids(db: Session, limit: int) -> list[UUID]:
    database_now = func.now()
    return list(
        db.scalars(
            select(QaExecution.id)
            .where(
                or_(
                    QaExecution.status == "queued",
                    and_(
                        QaExecution.status == "running",
                        or_(
                            QaExecution.lease_expires_at.is_(None),
                            QaExecution.lease_expires_at <= database_now,
                        ),
                    ),
                )
            )
            .order_by(QaExecution.created_at, QaExecution.id)
            .limit(limit)
        )
    )
