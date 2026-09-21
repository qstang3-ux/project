from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import QaSession
from app.repositories.qa import get_session, latest_message, session_message_count, session_messages
from app.schemas.common import PageMeta
from app.schemas.qa import MessageListResponse, MessageOut, SessionListResponse, SessionOut


def session_out(db: Session, model: QaSession) -> SessionOut:
    latest = latest_message(db, model.id)
    return SessionOut(
        id=model.id,
        title=model.title,
        pinned=model.pinned,
        parent_session_id=model.parent_session_id,
        message_count=session_message_count(db, model.id),
        last_message_preview=latest.content[:100] if latest else None,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


class SessionService:
    def __init__(self, db: Session, owner_id: str) -> None:
        self.db = db
        self.owner_id = owner_id

    def create(self, title: str | None) -> SessionOut:
        now = datetime.now(UTC)
        model = QaSession(owner_id=self.owner_id, title=title or "新对话", updated_at=now)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return session_out(self.db, model)

    def list(self, page: int, page_size: int, keyword: str | None) -> SessionListResponse:
        condition = [QaSession.owner_id == self.owner_id, QaSession.deleted_at.is_(None)]
        if keyword:
            condition.append(QaSession.title.ilike(f"%{keyword}%"))
        total = int(
            self.db.scalar(select(func.count()).select_from(QaSession).where(*condition)) or 0
        )
        models = self.db.scalars(
            select(QaSession)
            .where(*condition)
            .order_by(QaSession.pinned.desc(), QaSession.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return SessionListResponse(
            items=[session_out(self.db, item) for item in models],
            page=PageMeta(
                page=page, page_size=page_size, total=total, has_more=page * page_size < total
            ),
        )

    def get(self, session_id: UUID) -> SessionOut:
        model = get_session(self.db, session_id, self.owner_id)
        if not model:
            raise NotFoundError("会话不存在")
        return session_out(self.db, model)

    def update(self, session_id: UUID, title: str | None, pinned: bool | None) -> SessionOut:
        model = get_session(self.db, session_id, self.owner_id)
        if not model:
            raise NotFoundError("会话不存在")
        if title is not None:
            model.title = title
        if pinned is not None:
            model.pinned = pinned
        model.updated_at = datetime.now(UTC)
        self.db.commit()
        return session_out(self.db, model)

    def delete(self, session_id: UUID) -> None:
        model = get_session(self.db, session_id, self.owner_id)
        if not model:
            return
        model.deleted_at = datetime.now(UTC)
        self.db.commit()

    def messages(self, session_id: UUID, cursor: UUID | None, limit: int) -> MessageListResponse:
        if not get_session(self.db, session_id, self.owner_id):
            raise NotFoundError("会话不存在")
        rows = session_messages(self.db, session_id, cursor, limit)
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [
            MessageOut(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                source_message_id=m.source_message_id,
                execution_id=m.execution_id,
                execution_status=execution_status,
                created_at=m.created_at,
            )
            for m, execution_status in reversed(rows)
        ]
        return MessageListResponse(
            items=items,
            next_cursor=str(rows[-1][0].id) if has_more and rows else None,
            has_more=has_more,
        )
