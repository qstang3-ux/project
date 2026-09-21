from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import QaExecution
from app.services.query_service import QueryService


class VersionSession:
    def __init__(self, source: QaExecution, executions: list[QaExecution]) -> None:
        self.source = source
        self.executions = executions

    def scalar(self, statement: object) -> QaExecution:
        del statement
        return self.source

    def scalars(self, statement: object) -> list[QaExecution]:
        del statement
        return self.executions


def execution(
    *,
    created_at: datetime,
    session_id: Any,
    parent_id: Any = None,
) -> QaExecution:
    return QaExecution(
        id=uuid4(),
        request_id=f"request-{uuid4()}",
        idempotency_key=f"idempotency-{uuid4()}",
        generate_chart=True,
        session_id=session_id,
        user_message_id=uuid4(),
        assistant_message_id=uuid4(),
        status="completed",
        question="查询经营数据",
        data_source_ids=[],
        context_message_ids=[],
        answer=f"回答 {created_at.isoformat()}",
        executed_sql="SELECT 1",
        model_name="fake",
        duration_ms=100,
        regenerated_from_execution_id=parent_id,
        created_at=created_at,
    )


def test_answer_versions_follow_regeneration_lineage_from_descendant() -> None:
    now = datetime.now(UTC)
    session_id = uuid4()
    root = execution(created_at=now, session_id=session_id)
    second = execution(
        created_at=now + timedelta(seconds=1),
        session_id=session_id,
        parent_id=root.id,
    )
    third = execution(
        created_at=now + timedelta(seconds=2),
        session_id=session_id,
        parent_id=second.id,
    )
    unrelated = execution(
        created_at=now + timedelta(seconds=3),
        session_id=session_id,
    )
    db = VersionSession(third, [root, second, third, unrelated])
    service = QueryService(
        cast(Session, db),
        Settings(app_env="test", default_model_config="fake"),
    )

    versions = service.list_answer_versions(cast(Any, third.assistant_message_id))

    assert [item.execution_id for item in versions] == [root.id, second.id, third.id]
    assert [item.version_no for item in versions] == [1, 2, 3]
    assert [item.is_current for item in versions] == [False, False, True]
