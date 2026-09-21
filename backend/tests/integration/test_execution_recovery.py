import os
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text, update
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.errors import AppError
from app.main import app
from app.models import (
    DataSource,
    QaExecution,
    QaExecutionEffect,
    QaExecutionEvent,
    QaExecutionStep,
)
from app.repositories.qa import (
    claim_execution_lease,
    compare_and_set_execution_status,
    recoverable_execution_ids,
)
from app.services.query_service import QueryService
from app.text2sql.agent import AgentState, LangGraphQueryRunner
from app.text2sql.executor import QueryExecutor
from app.text2sql.types import IntentClassification, QueryResult, ValidatedSql

TEST_APP_DATABASE_URL = os.getenv("TEST_APP_DATABASE_URL")
TEST_QUERY_DATABASE_URL = os.getenv("TEST_QUERY_DATABASE_URL")
pytestmark = pytest.mark.integration


def _insert_execution(
    connection,  # type: ignore[no-untyped-def]
    *,
    session_id: UUID,
    status: str,
    lease_owner: str | None = None,
    lease_expires_at: datetime | None = None,
) -> UUID:
    message_id = uuid4()
    execution_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO app.qa_messages(id, session_id, role, content) "
            "VALUES(:id, :session_id, 'user', 'recovery-test')"
        ),
        {"id": message_id, "session_id": session_id},
    )
    connection.execute(
        text(
            "INSERT INTO app.qa_executions("
            "id, request_id, idempotency_key, session_id, user_message_id, status, "
            "question, data_source_ids, lease_owner, lease_expires_at, heartbeat_at) "
            "VALUES(:id, :request_id, :key, :session_id, :message_id, :status, "
            "'recovery-test', '[]', :lease_owner, :lease_expires_at, now())"
        ),
        {
            "id": execution_id,
            "request_id": f"req_{execution_id.hex}",
            "key": f"recovery-{execution_id}",
            "session_id": session_id,
            "message_id": message_id,
            "status": status,
            "lease_owner": lease_owner,
            "lease_expires_at": lease_expires_at,
        },
    )
    return execution_id


def _delete_session(engine, session_id: UUID) -> None:  # type: ignore[no-untyped-def]
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM app.qa_answer_versions WHERE execution_id IN "
                "(SELECT id FROM app.qa_executions WHERE session_id=:session_id)"
            ),
            {"session_id": session_id},
        )
        connection.execute(
            text("DELETE FROM app.qa_executions WHERE session_id=:session_id"),
            {"session_id": session_id},
        )
        connection.execute(
            text("DELETE FROM app.qa_sessions WHERE id=:session_id"),
            {"session_id": session_id},
        )


@pytest.mark.skipif(not TEST_APP_DATABASE_URL, reason="TEST_APP_DATABASE_URL is not configured")
def test_execution_lease_claim_takeover_cancel_priority_and_bounded_scan() -> None:
    assert TEST_APP_DATABASE_URL is not None
    engine = create_engine(TEST_APP_DATABASE_URL)
    session_id = uuid4()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app.qa_sessions(id, owner_id, title, updated_at) "
                "VALUES(:id, 'demo-user', 'lease-recovery-test', now())"
            ),
            {"id": session_id},
        )
        queued_id = _insert_execution(connection, session_id=session_id, status="queued")
        expired_id = _insert_execution(
            connection,
            session_id=session_id,
            status="running",
            lease_owner="dead-worker",
            lease_expires_at=now - timedelta(minutes=1),
        )
        active_id = _insert_execution(
            connection,
            session_id=session_id,
            status="running",
            lease_owner="active-worker",
            lease_expires_at=now + timedelta(minutes=5),
        )
        waiting_id = _insert_execution(connection, session_id=session_id, status="awaiting_input")
        cancelled_id = _insert_execution(connection, session_id=session_id, status="cancelled")
        completed_id = _insert_execution(connection, session_id=session_id, status="completed")

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with factory() as db:
            candidates = set(recoverable_execution_ids(db, 100))
            assert {queued_id, expired_id} <= candidates
            assert not {active_id, waiting_id, cancelled_id, completed_id} & candidates
            assert len(recoverable_execution_ids(db, 1)) == 1

            assert claim_execution_lease(db, queued_id, "worker-a", 60, "test-graph")
            db.commit()
        with factory() as contender:
            assert not claim_execution_lease(contender, queued_id, "worker-b", 60, "test-graph")
            contender.rollback()
            assert claim_execution_lease(contender, expired_id, "worker-b", 60, "test-graph")
            contender.commit()
        with factory() as stale_owner:
            assert not compare_and_set_execution_status(
                stale_owner,
                expired_id,
                ("running",),
                "completed",
                expected_lease_owner="dead-worker",
            )
            stale_owner.rollback()
        with factory() as cancel_db:
            assert compare_and_set_execution_status(
                cancel_db,
                expired_id,
                ("queued", "running", "awaiting_input"),
                "cancelled",
                lease_owner=None,
                lease_expires_at=None,
                heartbeat_at=None,
            )
            cancel_db.commit()
        with factory() as late_worker:
            assert not compare_and_set_execution_status(
                late_worker,
                expired_id,
                ("running",),
                "failed",
                expected_lease_owner="worker-b",
            )
            late_worker.rollback()
    finally:
        _delete_session(engine, session_id)


@pytest.mark.skipif(
    not TEST_APP_DATABASE_URL or not TEST_QUERY_DATABASE_URL,
    reason="PostgreSQL application and query connections are not configured",
)
def test_completed_model_and_sql_effects_are_reused_without_budget_or_step_duplication() -> None:
    assert TEST_APP_DATABASE_URL is not None
    assert TEST_QUERY_DATABASE_URL is not None
    engine = create_engine(TEST_APP_DATABASE_URL)
    session_id = uuid4()
    owner_id = f"effect-worker-{uuid4()}"
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app.qa_sessions(id, owner_id, title, updated_at) "
                "VALUES(:id, 'demo-user', 'effect-replay-test', now())"
            ),
            {"id": session_id},
        )
        execution_id = _insert_execution(
            connection,
            session_id=session_id,
            status="running",
            lease_owner=owner_id,
            lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

    settings = Settings(
        app_env="test",
        default_model_config="fake",
        database_url=TEST_APP_DATABASE_URL,
        query_database_url=TEST_QUERY_DATABASE_URL,
        execution_worker_id=owner_id,
        model_call_budget=1,
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    model_calls = 0

    def classify() -> IntentClassification:
        nonlocal model_calls
        model_calls += 1
        return IntentClassification("data_query", "收入", (), 0.99, "test", "fake", 3, 2)

    class CountingExecutor:
        calls = 0

        def execute(self, query: ValidatedSql) -> QueryResult:
            del query
            self.calls += 1
            return QueryResult([], [], 0, False, 2)

    try:
        with factory() as db:
            execution = db.get(QaExecution, execution_id)
            assert execution is not None
            runner = LangGraphQueryRunner(
                db,
                settings,
                execution,
                True,
                create_engine(TEST_QUERY_DATABASE_URL),
                owner_id,
            )
            model_key = runner._effect_key("model:intent_classification")
            first = runner._call_model("intent_classification", model_key, classify)
            second = runner._call_model("intent_classification", model_key, classify)
            assert first == second
            assert model_calls == 1
            assert len(execution.model_call_audit) == 1
            assert execution.token_usage["totalTokens"] == 5
            with pytest.raises(AppError) as budget_error:
                runner._call_model(
                    "sql_generation",
                    runner._effect_key("model:sql_generation"),
                    classify,
                )
            assert budget_error.value.code == "MODEL_BUDGET_EXCEEDED"

            executor = CountingExecutor()
            runner.executor = cast(QueryExecutor, executor)
            state = cast(AgentState, {"correction_count": 0})
            query = ValidatedSql("SELECT 1", "SELECT 1", ())
            assert runner._execute_query_effect(state, query) == runner._execute_query_effect(
                state, query
            )
            assert executor.calls == 1

        with engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(QaExecutionEffect)
                    .where(QaExecutionEffect.execution_id == execution_id)
                )
                == 2
            )
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(QaExecutionStep)
                    .where(QaExecutionStep.execution_id == execution_id)
                )
                == 1
            )
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(QaExecutionEvent)
                    .where(
                        QaExecutionEvent.execution_id == execution_id,
                        QaExecutionEvent.kind == "query.completed",
                    )
                )
                == 1
            )
    finally:
        _delete_session(engine, session_id)


@pytest.mark.skipif(
    not TEST_APP_DATABASE_URL or not TEST_QUERY_DATABASE_URL,
    reason="PostgreSQL application and query connections are not configured",
)
def test_recover_available_completes_oldest_queued_execution_end_to_end() -> None:
    assert TEST_APP_DATABASE_URL is not None
    assert TEST_QUERY_DATABASE_URL is not None
    engine = create_engine(TEST_APP_DATABASE_URL)
    session_id = uuid4()
    idempotency_key = f"queued-recovery-{uuid4()}"
    settings = Settings(
        app_env="test",
        default_model_config="fake",
        database_url=TEST_APP_DATABASE_URL,
        query_database_url=TEST_QUERY_DATABASE_URL,
        execution_worker_id=f"recovery-worker-{uuid4()}",
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO app.qa_sessions(id, owner_id, title, updated_at) "
                "VALUES(:id, 'demo-user', 'queued-recovery-test', now())"
            ),
            {"id": session_id},
        )
    execution_id: UUID | None = None
    try:
        with factory() as db:
            source_id = db.scalar(
                select(DataSource.id).where(DataSource.enabled.is_(True)).limit(1)
            )
            assert source_id is not None
            service = QueryService(db, settings)
            submission = service.create(
                session_id,
                "2026年商业目标最高的5个经营单元",
                [source_id],
                True,
                idempotency_key,
                f"req_{uuid4().hex}",
            )
            execution_id = submission.accepted.execution_id
            db.execute(
                update(QaExecution)
                .where(QaExecution.id == execution_id)
                .values(created_at=datetime(2000, 1, 1, tzinfo=UTC))
            )
            db.commit()

            assert service.recover_available(1) == (1, 1)
            db.expire_all()
            execution = db.get(QaExecution, execution_id)
            assert execution is not None
            assert execution.status == "completed"
            assert execution.run_attempt == 1
            assert execution.lease_owner is None
            assert execution.lease_expires_at is None
    finally:
        if execution_id is not None:
            with engine.begin() as connection:
                connection.execute(
                    text("DELETE FROM app.idempotency_records WHERE execution_id=:id"),
                    {"id": execution_id},
                )
        _delete_session(engine, session_id)


@pytest.mark.skipif(
    not TEST_APP_DATABASE_URL or not TEST_QUERY_DATABASE_URL,
    reason="PostgreSQL application and query connections are not configured",
)
def test_persist_result_effect_replay_does_not_duplicate_message_version_or_step() -> None:
    assert TEST_APP_DATABASE_URL is not None
    assert TEST_QUERY_DATABASE_URL is not None
    client = TestClient(app)
    engine = create_engine(TEST_APP_DATABASE_URL)
    source_id = client.get("/api/v1/data-sources").json()["items"][0]["id"]
    session_id = UUID(
        client.post("/api/v1/qa/sessions", json={"title": "persist-effect-replay"}).json()["id"]
    )
    response = client.post(
        f"/api/v1/qa/sessions/{session_id}/queries",
        headers={"Idempotency-Key": f"persist-replay-{uuid4()}"},
        json={
            "question": "2026年商业目标最高的5个经营单元",
            "dataSourceIds": [source_id],
        },
    )
    response.raise_for_status()
    execution_id = UUID(response.json()["executionId"])
    owner_id = f"replay-worker-{uuid4()}"
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with engine.begin() as connection:
            before = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM app.qa_messages WHERE execution_id=:id), "
                    "(SELECT count(*) FROM app.qa_answer_versions WHERE execution_id=:id), "
                    "(SELECT count(*) FROM app.qa_execution_steps WHERE execution_id=:id), "
                    "(SELECT count(*) FROM app.qa_execution_events WHERE execution_id=:id)"
                ),
                {"id": execution_id},
            ).one()
            connection.execute(
                update(QaExecution)
                .where(QaExecution.id == execution_id)
                .values(
                    status="running",
                    lease_owner=owner_id,
                    lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
                    heartbeat_at=datetime.now(UTC),
                )
            )
        settings = Settings(
            app_env="test",
            default_model_config="fake",
            database_url=TEST_APP_DATABASE_URL,
            query_database_url=TEST_QUERY_DATABASE_URL,
            execution_worker_id=owner_id,
        )
        with factory() as db:
            execution = db.get(QaExecution, execution_id)
            assert execution is not None
            runner = LangGraphQueryRunner(
                db,
                settings,
                execution,
                True,
                create_engine(TEST_QUERY_DATABASE_URL),
                owner_id,
            )
            runner.persist_result(cast(AgentState, {"node_trace": []}))
        with engine.begin() as connection:
            after = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM app.qa_messages WHERE execution_id=:id), "
                    "(SELECT count(*) FROM app.qa_answer_versions WHERE execution_id=:id), "
                    "(SELECT count(*) FROM app.qa_execution_steps WHERE execution_id=:id), "
                    "(SELECT count(*) FROM app.qa_execution_events WHERE execution_id=:id)"
                ),
                {"id": execution_id},
            ).one()
            assert after == before
            connection.execute(
                update(QaExecution)
                .where(QaExecution.id == execution_id)
                .values(
                    status="completed",
                    lease_owner=None,
                    lease_expires_at=None,
                    heartbeat_at=None,
                )
            )
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM app.idempotency_records WHERE execution_id=:id"),
                {"id": execution_id},
            )
        _delete_session(engine, session_id)
