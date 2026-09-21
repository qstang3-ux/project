from collections.abc import Callable
from dataclasses import dataclass

from app.text2sql.adapters import ModelAdapter
from app.text2sql.executor import (
    RECOVERABLE_ERROR_CATEGORIES,
    QueryExecutionError,
    QueryExecutor,
)
from app.text2sql.types import (
    ModelSqlOutput,
    PromptContextItem,
    QueryResult,
    SchemaContext,
    ValidatedSql,
)
from app.text2sql.validator import SqlValidator


@dataclass(frozen=True)
class CorrectionOutcome:
    result: QueryResult
    validated: ValidatedSql
    corrected: bool
    correction_output: ModelSqlOutput | None = None


def execute_with_one_correction(
    *,
    question: str,
    schema: SchemaContext,
    allowed_objects: set[str],
    adapter: ModelAdapter,
    validator: SqlValidator,
    executor: QueryExecutor,
    initial: ValidatedSql,
    before_retry: Callable[[ValidatedSql], None] | None = None,
    generate_correction: Callable[[QueryExecutionError], ModelSqlOutput] | None = None,
) -> CorrectionOutcome:
    try:
        return CorrectionOutcome(executor.execute(initial), initial, False)
    except QueryExecutionError as first_error:
        if not first_error.recoverable or first_error.category not in RECOVERABLE_ERROR_CATEGORIES:
            raise
        correction = (
            generate_correction(first_error)
            if generate_correction
            else adapter.generate_sql(
                question,
                schema,
                [
                    PromptContextItem(
                        channel="generated_sql",
                        source="validator_approved_candidate",
                        role="data",
                        trust="untrusted",
                        content=initial.sql,
                        provenance={},
                    ),
                    PromptContextItem(
                        channel="database_error",
                        source="sqlstate_category",
                        role="data",
                        trust="untrusted",
                        content=first_error.category,
                        provenance={"rawErrorIncluded": False},
                    ),
                ],
            )
        )
        if correction.sql is None:
            raise first_error
        corrected = validator.validate(correction.sql, allowed_objects)
        if before_retry:
            before_retry(corrected)
        return CorrectionOutcome(executor.execute(corrected), corrected, True, correction)
