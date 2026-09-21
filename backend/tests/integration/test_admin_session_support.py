import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.main import app
from app.text2sql.adapters import OpenAICompatibleAdapter

TEST_APP_DATABASE_URL = os.getenv("TEST_APP_DATABASE_URL")
TEST_QUERY_DATABASE_URL = os.getenv("TEST_QUERY_DATABASE_URL")
pytestmark = pytest.mark.integration


def _application_config_payload(config: dict[str, object]) -> dict[str, object]:
    return {
        "greetingEnabled": config["greetingEnabled"],
        "greetingText": config["greetingText"],
        "recommendedQuestions": config["recommendedQuestions"],
        "followUpEnabled": config["followUpEnabled"],
        "frequentQuestionsEnabled": config["frequentQuestionsEnabled"],
        "frequentQuestionThreshold": config["frequentQuestionThreshold"],
        "modelQaEnabled": config["modelQaEnabled"],
        "ttsEnabled": config["ttsEnabled"],
        "sttEnabled": config["sttEnabled"],
        "version": config["version"],
    }


@pytest.mark.skipif(not TEST_APP_DATABASE_URL, reason="TEST_APP_DATABASE_URL is not configured")
def test_session_favorite_and_application_config_lifecycle() -> None:
    client = TestClient(app)
    session_ids: list[str] = []
    favorite_id: str | None = None
    original_config = client.get("/api/v1/application-config").json()
    try:
        first = client.post("/api/v1/qa/sessions", json={"title": None})
        first.raise_for_status()
        first_body = first.json()
        session_ids.append(first_body["id"])
        assert first_body["title"] == "新对话"
        assert first_body["lastMessagePreview"] is None

        second = client.post("/api/v1/qa/sessions", json={"title": "覆盖率会话"})
        second.raise_for_status()
        session_ids.append(second.json()["id"])

        listed = client.get(
            "/api/v1/qa/sessions", params={"page": 1, "pageSize": 1, "keyword": "覆盖率"}
        ).json()
        assert listed["page"]["total"] == 1
        assert listed["items"][0]["id"] == second.json()["id"]

        updated = client.patch(
            f"/api/v1/qa/sessions/{second.json()['id']}",
            json={"title": "覆盖率已更新", "pinned": True},
        )
        updated.raise_for_status()
        assert updated.json()["pinned"] is True
        assert client.get(f"/api/v1/qa/sessions/{second.json()['id']}").status_code == 200
        assert (
            client.patch(f"/api/v1/qa/sessions/{second.json()['id']}", json={}).status_code == 422
        )

        messages = client.get(
            f"/api/v1/qa/sessions/{second.json()['id']}/messages", params={"limit": 1}
        )
        messages.raise_for_status()
        assert messages.json() == {"items": [], "nextCursor": None, "hasMore": False}
        assert client.get(f"/api/v1/qa/sessions/{uuid4()}/messages").status_code == 404

        question = f"  覆盖率收藏 {uuid4()}  "
        created = client.post("/api/v1/questions/favorites", json={"question": question})
        assert created.status_code == 201
        favorite_id = created.json()["id"]
        duplicate = client.post(
            "/api/v1/questions/favorites", json={"question": question.replace(" ", "")}
        )
        assert duplicate.status_code == 200
        assert duplicate.json()["id"] == favorite_id
        assert favorite_id in {
            item["id"] for item in client.get("/api/v1/questions/favorites").json()
        }

        changed_payload = _application_config_payload(original_config)
        changed_payload["greetingText"] = "覆盖率配置"
        changed = client.put("/api/v1/application-config", json=changed_payload)
        changed.raise_for_status()
        assert changed.json()["version"] == int(original_config["version"]) + 1
        stale = client.put("/api/v1/application-config", json=changed_payload)
        assert stale.status_code == 409

        restore_payload = _application_config_payload(original_config)
        restore_payload["version"] = changed.json()["version"]
        restored = client.put("/api/v1/application-config", json=restore_payload)
        restored.raise_for_status()
        assert restored.json()["greetingText"] == original_config["greetingText"]

        assert client.delete(f"/api/v1/qa/sessions/{first_body['id']}").status_code == 204
        assert client.get(f"/api/v1/qa/sessions/{first_body['id']}").status_code == 404
        assert client.delete(f"/api/v1/qa/sessions/{first_body['id']}").status_code == 204
    finally:
        if favorite_id:
            client.delete(f"/api/v1/questions/favorites/{favorite_id}")
            client.delete(f"/api/v1/questions/favorites/{favorite_id}")
        if TEST_APP_DATABASE_URL:
            engine = create_engine(TEST_APP_DATABASE_URL)
            with engine.begin() as connection:
                for session_id in session_ids:
                    connection.execute(
                        text("DELETE FROM app.qa_sessions WHERE id=:id"), {"id": session_id}
                    )


@pytest.mark.skipif(not TEST_APP_DATABASE_URL, reason="TEST_APP_DATABASE_URL is not configured")
def test_model_config_crud_activation_and_connection_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert TEST_APP_DATABASE_URL is not None
    client = TestClient(app)
    model_ids: list[str] = []
    monkeypatch.setattr(OpenAICompatibleAdapter, "probe", lambda self: None)
    engine = create_engine(TEST_APP_DATABASE_URL)
    with engine.connect() as connection:
        originally_active_ids = set(
            connection.scalars(text("SELECT id FROM app.model_configs WHERE active IS TRUE"))
        )

    def create(name: str, enabled: bool = True) -> dict[str, object]:
        response = client.post(
            "/api/v1/model-configs",
            json={
                "name": name,
                "provider": "openai_compatible",
                "protocol": "chat_completions",
                "baseUrl": "https://model.example/v1/",
                "modelName": "coverage-model",
                "apiKey": "coverage-secret-key",
                "timeoutSeconds": 12,
                "enabled": enabled,
            },
        )
        response.raise_for_status()
        model_ids.append(response.json()["id"])
        return response.json()

    try:
        first = create(f"coverage-{uuid4().hex[:12]}")
        second = create(f"disabled-{uuid4().hex[:12]}", enabled=False)
        assert first["apiKeyMask"] != "coverage-secret-key"
        assert str(first["baseUrl"]).endswith("/v1")
        assert first["id"] in {item["id"] for item in client.get("/api/v1/model-configs").json()}
        assert client.get(f"/api/v1/model-configs/{first['id']}").status_code == 200

        updated = client.patch(
            f"/api/v1/model-configs/{first['id']}",
            json={
                "baseUrl": "https://updated.example/v1/",
                "modelName": "gpt-5.6-sol",
                "apiKey": "new-coverage-secret",
            },
        )
        updated.raise_for_status()
        assert updated.json()["protocol"] == "responses"
        assert str(updated.json()["baseUrl"]).endswith("/v1")

        assert client.post(f"/api/v1/model-configs/{second['id']}/activate").status_code == 409
        active = client.post(f"/api/v1/model-configs/{first['id']}/activate")
        active.raise_for_status()
        assert active.json()["isActive"] is True
        assert client.delete(f"/api/v1/model-configs/{first['id']}").status_code == 409

        saved_probe = client.post("/api/v1/model-configs/test", json={"modelConfigId": first["id"]})
        saved_probe.raise_for_status()
        assert saved_probe.json()["status"] == "success"
        inline_probe = client.post(
            "/api/v1/model-configs/test",
            json={
                "provider": "openai_compatible",
                "protocol": "responses",
                "baseUrl": "https://inline.example/v1",
                "modelName": "coverage-model",
                "apiKey": "inline-secret",
            },
        )
        inline_probe.raise_for_status()
        assert inline_probe.json()["success"] is True

        enabled_second = client.patch(
            f"/api/v1/model-configs/{second['id']}", json={"enabled": True}
        )
        enabled_second.raise_for_status()
        client.post(f"/api/v1/model-configs/{second['id']}/activate").raise_for_status()
        assert client.delete(f"/api/v1/model-configs/{first['id']}").status_code == 204
        model_ids.remove(str(first["id"]))
        assert client.delete(f"/api/v1/model-configs/{uuid4()}").status_code == 204
        assert client.get(f"/api/v1/model-configs/{uuid4()}").status_code == 404
        assert (
            client.patch(f"/api/v1/model-configs/{uuid4()}", json={"name": "x"}).status_code == 404
        )
        assert client.post(f"/api/v1/model-configs/{uuid4()}/activate").status_code == 404
    finally:
        with engine.begin() as connection:
            for model_id in model_ids:
                connection.execute(
                    text("DELETE FROM app.model_configs WHERE id=:id"), {"id": model_id}
                )
            if originally_active_ids:
                connection.execute(
                    text("UPDATE app.model_configs SET active=TRUE WHERE id = ANY(:ids)"),
                    {"ids": list(originally_active_ids)},
                )
        with engine.connect() as connection:
            restored_active_ids = set(
                connection.scalars(text("SELECT id FROM app.model_configs WHERE active IS TRUE"))
            )
        assert restored_active_ids == originally_active_ids


@pytest.mark.skipif(
    not TEST_APP_DATABASE_URL or not TEST_QUERY_DATABASE_URL,
    reason="PostgreSQL application and query connections are not configured",
)
def test_feedback_and_log_endpoints_cover_real_execution() -> None:
    assert TEST_APP_DATABASE_URL is not None
    client = TestClient(app)
    session_id = client.post("/api/v1/qa/sessions", json={"title": "反馈覆盖率"}).json()["id"]
    source_id = client.get("/api/v1/data-sources").json()["items"][0]["id"]
    feedback_id: str | None = None
    try:
        accepted = client.post(
            f"/api/v1/qa/sessions/{session_id}/queries",
            headers={"Idempotency-Key": f"coverage-{uuid4()}"},
            json={
                "question": "目前有多少高风险项目",
                "dataSourceIds": [source_id],
                "generateChart": True,
            },
        )
        accepted.raise_for_status()
        detail = client.get(f"/api/v1/qa/executions/{accepted.json()['executionId']}")
        detail.raise_for_status()
        execution = detail.json()
        assert execution["status"] == "completed"

        created = client.post(
            "/api/v1/feedback",
            json={
                "sessionId": session_id,
                "assistantMessageId": execution["assistantMessageId"],
                "executionId": execution["id"],
                "reason": "answer_error",
                "description": "覆盖率反馈",
            },
        )
        created.raise_for_status()
        feedback_id = created.json()["id"]
        assert created.json()["userId"] == "demo-user"

        now = datetime.now(UTC).isoformat()
        listed = client.get(
            "/api/v1/feedback",
            params={
                "keyword": "高风险",
                "status": "pending",
                "reason": "answer_error",
                "userId": "demo-user",
                "from": "2020-01-01T00:00:00Z",
                "to": now,
            },
        )
        listed.raise_for_status()
        assert feedback_id in {item["id"] for item in listed.json()["items"]}
        assert client.get(f"/api/v1/feedback/{feedback_id}").status_code == 200

        resolved = client.patch(
            f"/api/v1/feedback/{feedback_id}",
            json={"status": "resolved", "resolutionNote": "已校对", "version": 1},
        )
        resolved.raise_for_status()
        assert resolved.json()["version"] == 2
        stale = client.patch(
            f"/api/v1/feedback/{feedback_id}",
            json={"status": "ignored", "version": 1},
        )
        assert stale.status_code == 409

        logs = client.get(
            "/api/v1/qa/logs",
            params={
                "keyword": "高风险",
                "status": "completed",
                "userId": "demo-user",
                "from": "2020-01-01T00:00:00Z",
                "to": now,
            },
        )
        logs.raise_for_status()
        assert execution["id"] in {item["executionId"] for item in logs.json()["items"]}
        log_detail = client.get(f"/api/v1/qa/logs/{execution['id']}")
        log_detail.raise_for_status()
        assert log_detail.json()["modelCalls"]
        assert client.get(f"/api/v1/qa/logs/{uuid4()}").status_code == 404
        assert client.get(f"/api/v1/feedback/{uuid4()}").status_code == 404
        invalid_feedback = client.post(
            "/api/v1/feedback",
            json={
                "sessionId": session_id,
                "assistantMessageId": uuid4().hex,
                "executionId": execution["id"],
                "reason": "other",
            },
        )
        assert invalid_feedback.status_code == 404
    finally:
        engine = create_engine(TEST_APP_DATABASE_URL)
        with engine.begin() as connection:
            params = {"session_id": session_id}
            connection.execute(
                text(
                    "DELETE FROM app.qa_feedback WHERE execution_id IN "
                    "(SELECT id FROM app.qa_executions WHERE session_id=:session_id)"
                ),
                params,
            )
            connection.execute(
                text("DELETE FROM app.idempotency_records WHERE session_id=:session_id"),
                params,
            )
            connection.execute(
                text(
                    "DELETE FROM app.qa_answer_versions WHERE execution_id IN "
                    "(SELECT id FROM app.qa_executions WHERE session_id=:session_id)"
                ),
                params,
            )
            connection.execute(
                text(
                    "DELETE FROM app.qa_execution_steps WHERE execution_id IN "
                    "(SELECT id FROM app.qa_executions WHERE session_id=:session_id)"
                ),
                params,
            )
            connection.execute(
                text("DELETE FROM app.qa_executions WHERE session_id=:session_id"), params
            )
            connection.execute(text("DELETE FROM app.qa_sessions WHERE id=:session_id"), params)
