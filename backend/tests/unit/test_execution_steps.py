from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models import QaExecutionStep
from app.services.execution_steps import execution_step_duration_ms


def step(step_type: str, duration_ms: int) -> QaExecutionStep:
    started_at = datetime.now(UTC)
    return QaExecutionStep(
        id=uuid4(),
        execution_id=uuid4(),
        effect_key=f"step:{step_type}",
        step_type=step_type,
        status="completed",
        summary="done",
        started_at=started_at,
        completed_at=started_at + timedelta(milliseconds=duration_ms),
    )


def test_execution_step_duration_uses_measured_wall_time() -> None:
    assert execution_step_duration_ms(step("query_execution", 137)) == 137


def test_legacy_zero_duration_uses_matching_model_audit() -> None:
    assert (
        execution_step_duration_ms(
            step("sql_generation", 0),
            [
                {"purpose": "intent_classification", "durationMs": 50},
                {"purpose": "sql_generation", "durationMs": 830},
            ],
        )
        == 830
    )


def test_legacy_zero_duration_without_evidence_is_unknown() -> None:
    assert execution_step_duration_ms(step("schema_selection", 0)) is None
