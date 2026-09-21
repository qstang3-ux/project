import json

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import AppError, SqlValidationError
from app.text2sql.adapters import FakeModelAdapter, OpenAICompatibleAdapter
from app.text2sql.validator import SqlValidator


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("2026年商业目标最高的5个经营单元", "data_query"),
        ("今年销售额怎么样", "clarification"),
        ("什么是完成率", "business_definition"),
        ("这个产品怎么使用", "product_help"),
        ("你好", "chat"),
        ("1+1等于几", "chat"),
        ("A=1", "chat"),
        ("我刚刚问了什么", "chat"),
        ("今天天气如何", "out_of_scope"),
        ("删除所有订单", "unsafe"),
    ],
)
def test_fake_intent_matrix_is_closed(question: str, expected: str) -> None:
    output = FakeModelAdapter().classify_intent(question, [])
    assert output.intent == expected
    assert output.normalized_question
    assert 0 <= output.confidence <= 1
    assert output.reason_code
    if expected == "clarification":
        assert output.missing_slots


def test_unknown_real_model_intent_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "intent": "unknown",
        "normalizedQuestion": "查询收入",
        "missingSlots": [],
        "confidence": 1,
        "reasonCode": "UNKNOWN",
    }
    request = httpx.Request("POST", "https://model.example/v1/chat/completions")
    response = httpx.Response(
        200,
        request=request,
        headers={"content-type": "application/json"},
        json={"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {}},
    )
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: response)
    adapter = OpenAICompatibleAdapter("https://model.example/v1", "secret", "model", 10)
    with pytest.raises(AppError) as exc_info:
        adapter.classify_intent("查询收入", [])
    assert exc_info.value.code == "MODEL_INVALID_RESPONSE"


def test_selected_object_boundary_cannot_be_bypassed() -> None:
    with pytest.raises(SqlValidationError):
        SqlValidator().validate(
            "SELECT project_name FROM mart.v_pipeline_risk",
            {"mart.v_sales_performance"},
        )


def test_agent_limits_are_explicit_and_fail_closed() -> None:
    settings = Settings()
    assert settings.graph_recursion_limit == 30
    assert settings.clarification_max_rounds == 2
    assert settings.model_call_budget == 8
    assert settings.model_http_attempt_budget == 12
    assert settings.model_http_max_attempts_per_call == 3
    assert settings.execution_deadline_seconds == 120
