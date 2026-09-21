import pytest

from app.text2sql.executor import RECOVERABLE_SQLSTATES, classify_query_error


@pytest.mark.parametrize("sqlstate,category", RECOVERABLE_SQLSTATES.items())
def test_recoverable_sqlstates_are_explicitly_allowlisted(sqlstate: str, category: str) -> None:
    error = classify_query_error(sqlstate, "raw database detail must stay internal")
    assert error.code == "QUERY_FAILED"
    assert error.recoverable is True
    assert error.category == category
    assert error.message == "查询执行失败"
    assert error.details is None


@pytest.mark.parametrize(
    "sqlstate,message,code,category",
    [
        ("57014", "canceling statement due to statement timeout", "QUERY_TIMEOUT", "timeout"),
        ("57014", "canceling statement due to user request", "QUERY_FAILED", "cancelled"),
        ("42501", "permission denied for relation secret", "QUERY_FAILED", "permission_denied"),
        ("08006", "connection failure host=internal", "QUERY_FAILED", "connection_error"),
        ("53100", "disk full", "QUERY_FAILED", "resource_error"),
        ("54000", "program limit", "QUERY_FAILED", "resource_error"),
        ("55P03", "lock not available", "QUERY_FAILED", "resource_error"),
        ("XX000", "internal database error", "QUERY_FAILED", "internal_error"),
        (None, "unknown raw error", "QUERY_FAILED", "unknown_error"),
    ],
)
def test_nonrecoverable_sqlstates_never_enter_correction(
    sqlstate: str | None,
    message: str,
    code: str,
    category: str,
) -> None:
    error = classify_query_error(sqlstate, message)
    assert error.code == code
    assert error.recoverable is False
    assert error.category == category
    assert message not in error.message
    assert error.details is None
