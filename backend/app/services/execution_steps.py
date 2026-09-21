from collections.abc import Mapping, Sequence
from typing import Any

from app.models import QaExecutionStep

MODEL_PURPOSE_BY_STEP = {
    "intent_classification": "intent_classification",
    "sql_generation": "sql_generation",
    "answer_generation": "answer_generation",
}


def execution_step_duration_ms(
    step: QaExecutionStep, model_calls: Sequence[Mapping[str, Any]] = ()
) -> int | None:
    """Return measured wall time, with model audit as a legacy-data fallback."""
    if step.started_at is not None and step.completed_at is not None:
        measured = max(0, round((step.completed_at - step.started_at).total_seconds() * 1000))
        if measured > 0:
            return measured

    purpose = MODEL_PURPOSE_BY_STEP.get(step.step_type)
    if purpose is None:
        return None
    durations = [
        int(call.get("durationMs", 0))
        for call in model_calls
        if call.get("purpose") == purpose and int(call.get("durationMs", 0)) > 0
    ]
    return sum(durations) or None
