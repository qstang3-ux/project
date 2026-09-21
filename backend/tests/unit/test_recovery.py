import pytest

from app.recovery import recover


@pytest.mark.parametrize("limit", [0, 101])
def test_recovery_command_rejects_unbounded_limit(limit: int) -> None:
    with pytest.raises(ValueError, match="between 1 and 100"):
        recover(limit)
