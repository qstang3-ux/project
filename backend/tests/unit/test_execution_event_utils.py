from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.event_retention import cleanup_execution_events
from app.services.execution_events import event_id, parse_event_id


def test_execution_event_id_round_trip_and_validation() -> None:
    execution_id = uuid4()
    assert parse_event_id(event_id(execution_id, 12), execution_id) == 12
    with pytest.raises(AppError, match="SSE 事件 ID 格式无效"):
        parse_event_id("broken", execution_id)
    with pytest.raises(AppError) as mismatch:
        parse_event_id(event_id(uuid4(), 1), execution_id)
    assert mismatch.value.code == "SSE_EVENT_EXECUTION_MISMATCH"
    with pytest.raises(AppError) as invalid_sequence:
        parse_event_id(event_id(execution_id, 0), execution_id)
    assert invalid_sequence.value.code == "SSE_EVENT_ID_INVALID"


@pytest.mark.parametrize("days,limit", [(0, 10), (366, 10), (7, 0), (7, 1001)])
def test_event_retention_rejects_unbounded_arguments(days: int, limit: int) -> None:
    with pytest.raises(ValueError):
        cleanup_execution_events(days, limit)
