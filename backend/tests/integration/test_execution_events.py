import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text

from app.event_retention import cleanup_execution_events
from app.main import app
from app.models import QaExecutionEvent

TEST_APP_DATABASE_URL = os.getenv("TEST_APP_DATABASE_URL")
pytestmark = pytest.mark.integration


def _parse_sse(content: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in content.replace("\r\n", "\n").split("\n\n"):
        if not block or block.startswith(":"):
            continue
        fields: dict[str, str] = {}
        for line in block.splitlines():
            name, _, value = line.partition(":")
            fields[name] = value.lstrip()
        if "data" not in fields:
            continue
        payload = json.loads(fields["data"])
        assert payload["id"] == fields["id"]
        assert payload["type"] == fields["event"]
        events.append(payload)
    return events


def _create_completed_execution(client: TestClient) -> tuple[UUID, UUID]:
    source_id = client.get("/api/v1/data-sources").json()["items"][0]["id"]
    session_id = UUID(
        client.post("/api/v1/qa/sessions", json={"title": "sse-replay-test"}).json()["id"]
    )
    response = client.post(
        f"/api/v1/qa/sessions/{session_id}/queries",
        headers={"Idempotency-Key": f"sse-replay-{uuid4()}"},
        json={
            "question": "2026年商业目标最高的5个经营单元",
            "dataSourceIds": [source_id],
        },
    )
    response.raise_for_status()
    return session_id, UUID(response.json()["executionId"])


def _delete_session(session_id: UUID) -> None:
    assert TEST_APP_DATABASE_URL is not None
    engine = create_engine(TEST_APP_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM app.idempotency_records WHERE session_id=:session_id"),
            {"session_id": session_id},
        )
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
def test_sse_persistent_replay_reconnect_and_terminal_exactly_once() -> None:
    assert TEST_APP_DATABASE_URL is not None
    client = TestClient(app)
    session_id, execution_id = _create_completed_execution(client)
    try:
        first = client.get(f"/api/v1/qa/executions/{execution_id}/events")
        first.raise_for_status()
        events = _parse_sse(first.text)
        event_ids = [str(item["id"]) for item in events]
        sequences = [int(item.rsplit(":", 1)[1]) for item in event_ids]
        assert sequences == sorted(sequences)
        assert len(sequences) == len(set(sequences))
        assert events[0]["type"] == "execution.started"
        assert events[-1]["type"] == "execution.completed"
        assert sum(item["type"] == "execution.started" for item in events) == 1
        assert sum(item["type"] == "execution.completed" for item in events) == 1

        cursor_index = 2
        resumed = client.get(
            f"/api/v1/qa/executions/{execution_id}/events",
            headers={"Last-Event-ID": event_ids[cursor_index]},
        )
        resumed.raise_for_status()
        assert [str(item["id"]) for item in _parse_sse(resumed.text)] == event_ids[
            cursor_index + 1 :
        ]

        fallback = client.get(
            f"/api/v1/qa/executions/{execution_id}/events",
            params={"lastEventId": event_ids[cursor_index]},
        )
        fallback.raise_for_status()
        assert [str(item["id"]) for item in _parse_sse(fallback.text)] == event_ids[
            cursor_index + 1 :
        ]

        header_wins = client.get(
            f"/api/v1/qa/executions/{execution_id}/events",
            headers={"Last-Event-ID": event_ids[-1]},
            params={"lastEventId": event_ids[0]},
        )
        header_wins.raise_for_status()
        assert _parse_sse(header_wins.text) == []

        engine = create_engine(TEST_APP_DATABASE_URL)
        with engine.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count())
                    .select_from(QaExecutionEvent)
                    .where(
                        QaExecutionEvent.execution_id == execution_id,
                        QaExecutionEvent.kind == "execution.completed",
                    )
                )
                == 1
            )
    finally:
        _delete_session(session_id)


@pytest.mark.skipif(not TEST_APP_DATABASE_URL, reason="TEST_APP_DATABASE_URL is not configured")
def test_sse_concurrent_connections_receive_identical_persisted_history() -> None:
    client = TestClient(app)
    session_id, execution_id = _create_completed_execution(client)
    try:

        def read_history() -> list[str]:
            with TestClient(app) as concurrent_client:
                response = concurrent_client.get(f"/api/v1/qa/executions/{execution_id}/events")
                response.raise_for_status()
                return [str(item["id"]) for item in _parse_sse(response.text)]

        with ThreadPoolExecutor(max_workers=2) as pool:
            histories = list(pool.map(lambda _: read_history(), range(2)))
        assert histories[0]
        assert histories[0] == histories[1]
    finally:
        _delete_session(session_id)


@pytest.mark.skipif(not TEST_APP_DATABASE_URL, reason="TEST_APP_DATABASE_URL is not configured")
def test_sse_clarification_and_cursor_errors() -> None:
    assert TEST_APP_DATABASE_URL is not None
    client = TestClient(app)
    source_id = client.get("/api/v1/data-sources").json()["items"][0]["id"]
    session_id = UUID(
        client.post("/api/v1/qa/sessions", json={"title": "sse-cursor-test"}).json()["id"]
    )
    other_session_id: UUID | None = None
    try:
        response = client.post(
            f"/api/v1/qa/sessions/{session_id}/queries",
            headers={"Idempotency-Key": f"sse-clarification-{uuid4()}"},
            json={"question": "达成情况", "dataSourceIds": [source_id]},
        )
        response.raise_for_status()
        execution_id = UUID(response.json()["executionId"])
        history = client.get(f"/api/v1/qa/executions/{execution_id}/events")
        history.raise_for_status()
        events = _parse_sse(history.text)
        assert events[-1]["type"] == "clarification.required"
        assert sum(item["type"] == "clarification.required" for item in events) == 1

        invalid = client.get(
            f"/api/v1/qa/executions/{execution_id}/events",
            headers={"Last-Event-ID": "not-an-event"},
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "SSE_EVENT_ID_INVALID"

        other_session_id, other_execution_id = _create_completed_execution(client)
        other_history = _parse_sse(
            client.get(f"/api/v1/qa/executions/{other_execution_id}/events").text
        )
        mismatch = client.get(
            f"/api/v1/qa/executions/{execution_id}/events",
            headers={"Last-Event-ID": str(other_history[0]["id"])},
        )
        assert mismatch.status_code == 409
        assert mismatch.json()["error"]["code"] == "SSE_EVENT_EXECUTION_MISMATCH"

        first_id = str(events[0]["id"])
        first_sequence = int(first_id.rsplit(":", 1)[1])
        engine = create_engine(TEST_APP_DATABASE_URL)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE app.qa_executions SET event_sequence_floor=:sequence "
                    "WHERE id=:execution_id"
                ),
                {"sequence": first_sequence, "execution_id": execution_id},
            )
            connection.execute(
                text(
                    "DELETE FROM app.qa_execution_events "
                    "WHERE execution_id=:execution_id AND sequence<=:sequence"
                ),
                {"sequence": first_sequence, "execution_id": execution_id},
            )
        expired = client.get(
            f"/api/v1/qa/executions/{execution_id}/events",
            headers={"Last-Event-ID": first_id},
        )
        assert expired.status_code == 410
        assert expired.json()["error"]["code"] == "SSE_EVENT_EXPIRED"
    finally:
        _delete_session(session_id)
        if other_session_id is not None:
            _delete_session(other_session_id)


@pytest.mark.skipif(not TEST_APP_DATABASE_URL, reason="TEST_APP_DATABASE_URL is not configured")
def test_event_retention_advances_floor_before_deleting_history() -> None:
    assert TEST_APP_DATABASE_URL is not None
    client = TestClient(app)
    session_id, execution_id = _create_completed_execution(client)
    engine = create_engine(TEST_APP_DATABASE_URL)
    try:
        history = _parse_sse(client.get(f"/api/v1/qa/executions/{execution_id}/events").text)
        last_event_id = str(history[-1]["id"])
        last_sequence = int(last_event_id.rsplit(":", 1)[1])
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE app.qa_executions SET completed_at=:completed_at WHERE id=:execution_id"
                ),
                {"completed_at": datetime(2000, 1, 1, tzinfo=UTC), "execution_id": execution_id},
            )

        result = cleanup_execution_events(7, 1)
        assert result.executions == 1
        assert result.events == len(history)
        with engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT event_sequence_floor, "
                    "(SELECT count(*) FROM app.qa_execution_events WHERE execution_id=:id) "
                    "FROM app.qa_executions WHERE id=:id"
                ),
                {"id": execution_id},
            ).one()
            assert row[0] == last_sequence
            assert row[1] == 0

        expired = client.get(
            f"/api/v1/qa/executions/{execution_id}/events",
            headers={"Last-Event-ID": last_event_id},
        )
        assert expired.status_code == 410
        assert expired.json()["error"]["code"] == "SSE_EVENT_EXPIRED"
    finally:
        _delete_session(session_id)
