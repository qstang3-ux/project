from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.router import _execution_event_data
from app.main import _warm_rag_embedding, app
from app.text2sql.rag import BgeEmbeddingProvider


def test_liveness_and_request_id() -> None:
    response = TestClient(app).get("/health/live", headers={"X-Request-ID": "req_test"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req_test"
    assert response.json()["status"] == "ok"


def test_validation_error_uses_unified_shape() -> None:
    response = TestClient(app).post("/api/v1/qa/sessions", json={"title": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["requestId"].startswith("req_")


def test_generated_openapi_contains_first_milestone_paths() -> None:
    paths = app.openapi()["paths"]
    expected = {
        "/health/live",
        "/health/ready",
        "/api/v1/data-sources",
        "/api/v1/qa/sessions",
        "/api/v1/qa/sessions/{sessionId}/queries",
        "/api/v1/qa/executions/{executionId}",
        "/api/v1/qa/executions/{executionId}/events",
    }
    assert expected <= set(paths)
    validation_data = _execution_event_data(
        SimpleNamespace(
            selected_objects=[],
            generated_sql="SELECT 1",
            result_json=None,
            row_count=None,
            assistant_message_id=None,
        ),
        "sql_validation",
    )
    assert validation_data == {
        "kind": "sql.validated",
        "sqlValidationStatus": "passed",
        "ruleVersion": "1.0",
    }


def test_local_frontend_origin_receives_cors_headers() -> None:
    response = TestClient(app).options(
        "/health/live",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_rag_embedding_warmup_loads_and_encodes_once(monkeypatch: pytest.MonkeyPatch) -> None:
    encoded: list[list[str]] = []
    monkeypatch.setattr(
        BgeEmbeddingProvider,
        "encode",
        lambda self, texts: encoded.append(list(texts)) or [[0.0] * self.dimension],
    )

    _warm_rag_embedding()

    assert encoded == [["经管之星检索预热"]]
