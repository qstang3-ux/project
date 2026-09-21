import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError

from app.core.errors import AppError
from app.text2sql.types import QueryResult, ValidatedSql

RECOVERABLE_SQLSTATES = {
    "22P02": "invalid_text_representation",
    "42601": "syntax_error",
    "42703": "undefined_column",
    "42803": "grouping_error",
    "42804": "datatype_mismatch",
    "42846": "cannot_coerce",
    "42883": "undefined_function",
    "42P01": "undefined_table",
}
RECOVERABLE_ERROR_CATEGORIES = frozenset(RECOVERABLE_SQLSTATES.values())


class QueryExecutionError(AppError):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        *,
        recoverable: bool,
        category: str,
    ) -> None:
        super().__init__(code, message, status_code)
        self.recoverable = recoverable
        self.category = category


def classify_query_error(sqlstate: str | None, message: str) -> QueryExecutionError:
    normalized = message.lower()
    if "statement timeout" in normalized or "lock timeout" in normalized:
        return QueryExecutionError(
            "QUERY_TIMEOUT",
            "查询执行超时",
            504,
            recoverable=False,
            category="timeout",
        )
    if sqlstate in RECOVERABLE_SQLSTATES:
        return QueryExecutionError(
            "QUERY_FAILED",
            "查询执行失败",
            422,
            recoverable=True,
            category=RECOVERABLE_SQLSTATES[sqlstate],
        )
    if sqlstate == "57014":
        category = "cancelled"
    elif sqlstate == "42501":
        category = "permission_denied"
    elif sqlstate and sqlstate.startswith("08"):
        category = "connection_error"
    elif sqlstate and sqlstate[:2] in {"53", "54", "55"}:
        category = "resource_error"
    elif sqlstate and sqlstate[:2] in {"57", "58", "XX"}:
        category = "internal_error"
    else:
        category = "unknown_error"
    return QueryExecutionError(
        "QUERY_FAILED",
        "查询执行失败",
        422,
        recoverable=False,
        category=category,
    )


def _sqlstate(error: BaseException | None) -> str | None:
    if error is None:
        return None
    value = getattr(error, "sqlstate", None) or getattr(error, "pgcode", None)
    return str(value) if value else None


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


class QueryExecutor:
    def __init__(
        self,
        engine: Engine,
        timeout_seconds: int,
        lock_timeout_seconds: int,
        max_rows: int,
        max_bytes: int,
    ) -> None:
        self.engine = engine
        self.timeout_seconds = timeout_seconds
        self.lock_timeout_seconds = lock_timeout_seconds
        self.max_rows = max_rows
        self.max_bytes = max_bytes

    def execute(self, query: ValidatedSql) -> QueryResult:
        try:
            with self.engine.connect() as connection, connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                connection.execute(
                    text(f"SET LOCAL statement_timeout = {self.timeout_seconds * 1000}")
                )
                connection.execute(
                    text(f"SET LOCAL lock_timeout = {self.lock_timeout_seconds * 1000}")
                )
                result = connection.execute(text(query.sql))
                keys = list(result.keys())
                raw_rows = result.fetchmany(self.max_rows + 1)
        except DBAPIError as exc:
            raise classify_query_error(_sqlstate(exc.orig), str(exc.orig)) from exc
        except SQLAlchemyError as exc:
            raise QueryExecutionError(
                "QUERY_FAILED",
                "查询执行失败",
                422,
                recoverable=False,
                category="internal_error",
            ) from exc
        truncated = len(raw_rows) > self.max_rows
        rows = [
            {key: json_value(value) for key, value in zip(keys, row, strict=True)}
            for row in raw_rows[: self.max_rows]
        ]
        encoded = json.dumps(rows, ensure_ascii=False).encode("utf-8")
        if len(encoded) > self.max_bytes:
            raise AppError("RESULT_TOO_LARGE", "查询结果超过大小限制", 413)
        columns = [self._column(key, rows) for key in keys]
        return QueryResult(columns, rows, len(rows), truncated, len(encoded))

    @staticmethod
    def _column(key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
        value = next((row[key] for row in rows if row[key] is not None), None)
        data_type = "string"
        if isinstance(value, bool):
            data_type = "boolean"
        elif isinstance(value, int):
            data_type = "integer"
        elif (
            isinstance(value, float)
            or isinstance(value, str)
            and value.replace(".", "", 1).isdigit()
        ):
            data_type = "decimal"
        if "率" in key or "占比" in key:
            data_type = "percent"
        if "月份" in key or "日期" in key:
            data_type = "date"
        unit = (
            "%"
            if data_type == "percent"
            else ("元" if any(word in key for word in ("额", "收入", "目标", "金额")) else None)
        )
        return {"key": key, "label": key, "dataType": data_type, "unit": unit}
