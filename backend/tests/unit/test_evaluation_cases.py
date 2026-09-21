import json
from pathlib import Path
from typing import Any

import pytest

from app.core.errors import SqlValidationError
from app.text2sql.adapters import FakeModelAdapter
from app.text2sql.schema import SchemaRetriever
from app.text2sql.validator import SqlValidator

ALLOWED = [
    "mart.v_sales_performance",
    "mart.v_target_achievement",
    "mart.v_pipeline_risk",
]


def evaluation_cases() -> list[dict[str, Any]]:
    payload = json.loads(Path("tests/evaluation/text2sql-cases.json").read_text(encoding="utf-8"))
    return list(payload["cases"])


@pytest.mark.parametrize("case", evaluation_cases(), ids=lambda item: str(item["id"]))
def test_all_evaluation_cases_follow_generation_and_validation_contract(
    case: dict[str, Any],
) -> None:
    question = str(case["question"])
    context = ["2026年商业目标最高的5个经营单元"] if case.get("dependsOn") else []
    schema = SchemaRetriever().retrieve(question, ALLOWED)
    candidate = FakeModelAdapter().generate_sql(question, schema, context)

    if case.get("expectClarification"):
        assert candidate.intent == "clarification"
        assert candidate.sql is None
        return
    if case.get("expectNoQuery"):
        assert candidate.intent == "no_query"
        assert candidate.sql is None
        return
    if case.get("expectRejected"):
        assert candidate.sql is not None
        with pytest.raises(SqlValidationError):
            SqlValidator().validate(candidate.sql, set(ALLOWED))
        return

    assert candidate.sql is not None
    validated = SqlValidator().validate(candidate.sql, set(ALLOWED))
    expected_objects = {f"mart.{name}" for name in case.get("objects", [])}
    assert expected_objects <= set(validated.objects)
    assert expected_objects <= set(candidate.selected_objects)
    if "maxRows" in case:
        assert validated.sql.endswith(f"LIMIT {case['maxRows']}")
