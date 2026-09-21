from uuid import uuid4

import pytest
from sqlglot import exp

from app.core.errors import SqlValidationError
from app.text2sql.executor import json_value
from app.text2sql.validator import SqlValidator

ALLOWED = {
    "mart.v_sales_performance",
    "mart.v_target_achievement",
    "mart.v_pipeline_risk",
}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT contract_no FROM mart.v_sales_performance; DROP TABLE mart.contracts",
        "DELETE FROM mart.v_sales_performance",
        "SELECT encrypted_api_key FROM app.model_configs",
        "SELECT usename FROM pg_catalog.pg_user",
        "COPY mart.v_sales_performance TO '/tmp/leak.csv'",
        "SELECT * FROM mart.v_sales_performance",
        "SELECT pg_read_file('/etc/passwd') FROM mart.v_sales_performance",
        "SELECT missing_column FROM mart.v_sales_performance",
        "SELECT contract_no FROM v_sales_performance",
        "SELECT contract_no INTO TEMP temp_contracts FROM mart.v_sales_performance",
        "SELECT contract_no FROM mart.v_sales_performance FOR UPDATE",
        "WITH RECURSIVE x AS (SELECT 1 UNION ALL SELECT 1 FROM x) "
        "SELECT contract_no FROM mart.v_sales_performance",
        "SELECT fake.contract_no FROM mart.v_sales_performance AS real",
        "SELECT derived.missing FROM (SELECT contract_no FROM mart.v_sales_performance) derived",
        "WITH safe AS (SELECT contract_no FROM mart.v_sales_performance) "
        "SELECT safe.missing FROM safe",
        "SELECT contract_no FROM (SELECT contract_no FROM app.qa_messages) nested",
        "SELECT current_user FROM mart.v_sales_performance",
        "SELECT set_config('search_path', 'app', false) FROM mart.v_sales_performance",
    ],
)
def test_rejects_unsafe_sql(sql: str) -> None:
    with pytest.raises(SqlValidationError):
        SqlValidator().validate(sql, ALLOWED)


def test_adds_limit() -> None:
    validated = SqlValidator(500).validate(
        "SELECT business_unit_name FROM mart.v_target_achievement", ALLOWED
    )
    assert validated.sql.endswith("LIMIT 500")


def test_shrinks_limit() -> None:
    validated = SqlValidator(500).validate(
        "SELECT contract_no FROM mart.v_sales_performance LIMIT 9999", ALLOWED
    )
    assert validated.sql.endswith("LIMIT 500")


def test_keeps_limit_within_maximum() -> None:
    validated = SqlValidator(500).validate(
        "SELECT contract_no FROM mart.v_sales_performance LIMIT 5", ALLOWED
    )

    assert validated.sql.endswith("LIMIT 5")


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("SELECT '", "SQL 无法解析"),
        ("SELECT 1", "查询未访问允许的数据对象"),
        (
            "SELECT sales.missing_column FROM mart.v_sales_performance AS sales",
            "列 sales.missing_column 不在白名单",
        ),
        (
            "SELECT contract_no FROM mart.v_sales_performance LIMIT 1.5",
            "LIMIT 必须为整数常量",
        ),
    ],
)
def test_rejects_specific_invalid_shapes(sql: str, message: str) -> None:
    with pytest.raises(SqlValidationError, match=message):
        SqlValidator().validate(sql, ALLOWED)


def test_allows_join_with_explicit_condition() -> None:
    validated = SqlValidator().validate(
        "SELECT sales.business_unit_name, target.achievement_rate "
        "FROM mart.v_sales_performance AS sales "
        "JOIN mart.v_target_achievement AS target "
        "ON target.business_unit_code = sales.business_unit_code",
        ALLOWED,
    )

    assert "JOIN mart.v_target_achievement" in validated.sql


def test_allows_cross_join_to_provably_scalar_aggregate_cte() -> None:
    sql = (
        "WITH total AS ("
        "SELECT sum(revenue_amount) AS total_revenue "
        "FROM mart.v_sales_performance WHERE year = 2026"
        ") "
        "SELECT sales.product_line_name, "
        "sum(sales.revenue_amount) / nullif(total.total_revenue, 0) AS revenue_share "
        "FROM mart.v_sales_performance AS sales CROSS JOIN total "
        "WHERE sales.year = 2026 "
        "GROUP BY sales.product_line_name, total.total_revenue"
    )

    validated = SqlValidator().validate(sql, ALLOWED)

    assert "CROSS JOIN total" in validated.sql


def test_rejects_cross_join_to_non_scalar_cte() -> None:
    sql = (
        "WITH totals AS ("
        "SELECT business_unit_name, sum(revenue_amount) AS revenue_amount "
        "FROM mart.v_sales_performance GROUP BY business_unit_name"
        ") "
        "SELECT sales.contract_no FROM mart.v_sales_performance AS sales CROSS JOIN totals"
    )

    with pytest.raises(SqlValidationError, match="禁止无连接条件的多表查询"):
        SqlValidator().validate(sql, ALLOWED)


def test_scalar_query_detection_is_bounded_and_defensive() -> None:
    assert SqlValidator._is_scalar_query(exp.select("1")) is True
    assert SqlValidator._is_scalar_query(exp.select("1").limit(1)) is True
    assert SqlValidator._is_scalar_query(exp.select("1").limit(2)) is False
    non_integer_limit = exp.select("1")
    non_integer_limit.set("limit", exp.Limit(expression=exp.Literal.string("1")))
    assert SqlValidator._is_scalar_query(non_integer_limit) is True
    assert (
        SqlValidator._is_scalar_query(exp.Union(this=exp.select("1"), expression=exp.select("2")))
        is False
    )


def test_scalar_subquery_join_is_recognized_without_relaxing_physical_joins() -> None:
    statement = exp.select("sales.contract_no").from_(
        exp.Table(
            this=exp.Identifier(this="v_sales_performance"),
            db=exp.Identifier(this="mart"),
            alias="sales",
        )
    )
    scalar = exp.Subquery(this=exp.select("1"), alias="singleton")
    join = exp.Join(this=scalar, kind="CROSS")
    statement.append("joins", join)

    assert "singleton" in SqlValidator._scalar_sources(statement)
    assert SqlValidator._is_scalar_join(join, {"singleton"}) is True
    assert SqlValidator._is_scalar_join(exp.Join(this=exp.Literal.number(1)), set()) is False


def test_unaliased_subquery_is_not_registered_as_a_derived_source() -> None:
    with pytest.raises(SqlValidationError, match="查询未访问允许的数据对象"):
        SqlValidator().validate("SELECT value FROM (SELECT 1 AS value)", ALLOWED)


def test_non_query_cte_is_ignored_defensively() -> None:
    statement = exp.Select(expressions=[exp.Literal.number(1)])
    statement.set(
        "with",
        exp.With(
            expressions=[
                exp.CTE(this=exp.Table(this=exp.Identifier(this="not_a_query")), alias="safe")
            ]
        ),
    )

    assert SqlValidator._derived_sources(statement) == {}


def test_allows_read_only_cte_and_count_star() -> None:
    validated = SqlValidator().validate(
        "WITH totals AS (SELECT business_unit_name, sum(revenue_amount) amount "
        "FROM mart.v_sales_performance GROUP BY business_unit_name) "
        "SELECT count(*) AS total FROM totals",
        ALLOWED,
    )
    assert "WITH totals" in validated.sql


def test_rejects_cross_join() -> None:
    with pytest.raises(SqlValidationError):
        SqlValidator().validate(
            "SELECT a.contract_no FROM mart.v_sales_performance a "
            "CROSS JOIN mart.v_target_achievement b",
            ALLOWED,
        )


def test_allows_base_alias_and_valid_derived_columns() -> None:
    sql = (
        "SELECT derived.contract_no FROM "
        "(SELECT sales.contract_no FROM mart.v_sales_performance AS sales) derived"
    )
    validated = SqlValidator().validate(sql, ALLOWED)
    assert "derived.contract_no" in validated.sql


def test_allows_safe_functions_in_nested_query() -> None:
    sql = (
        "SELECT coalesce(summary.amount, 0) AS amount FROM "
        "(SELECT sum(revenue_amount) AS amount FROM mart.v_sales_performance) summary"
    )
    validated = SqlValidator().validate(sql, ALLOWED)
    assert "COALESCE" in validated.sql


def test_allows_or_in_read_only_filter() -> None:
    validated = SqlValidator().validate(
        "SELECT year FROM mart.v_sales_performance WHERE year = 2025 OR year = 2026 ORDER BY year",
        ALLOWED,
    )

    assert " OR " in validated.sql


def test_allows_case_expression_in_read_only_projection() -> None:
    validated = SqlValidator().validate(
        "SELECT CASE WHEN year = 2026 THEN revenue_amount ELSE 0 END AS current_revenue "
        "FROM mart.v_sales_performance",
        ALLOWED,
    )

    assert "CASE WHEN" in validated.sql


def test_allows_cte_reference_with_a_second_alias() -> None:
    sql = (
        "WITH safe AS (SELECT contract_no FROM mart.v_sales_performance) "
        "SELECT renamed.contract_no FROM safe AS renamed"
    )
    validated = SqlValidator().validate(sql, ALLOWED)
    assert "renamed.contract_no" in validated.sql


def test_query_result_uuid_is_serialized_without_internal_error() -> None:
    value = uuid4()

    assert json_value(value) == str(value)


def test_allows_postgres_date_trunc_cast_after_sqlglot_normalization() -> None:
    validated = SqlValidator().validate(
        "SELECT date_trunc('month', expected_landing_date)::date AS month, "
        "count(DISTINCT project_id) AS project_count FROM mart.v_pipeline_risk "
        "GROUP BY date_trunc('month', expected_landing_date)::date ORDER BY month",
        ALLOWED,
    )

    assert "DATE_TRUNC('MONTH', expected_landing_date)" in validated.sql


@pytest.mark.parametrize(
    ("column", "natural_value", "canonical_value"),
    [
        ("region", "华东地区", "华东"),
        ("region", "华南地区", "华南"),
        ("industry_name", "金融行业", "金融"),
        ("industry_major_name", "金融行业", "金融"),
    ],
)
def test_normalizes_allowlisted_natural_enum_suffixes(
    column: str, natural_value: str, canonical_value: str
) -> None:
    validated = SqlValidator().validate(
        f"SELECT count(*) FROM mart.v_sales_performance WHERE {column}='{natural_value}'",
        ALLOWED,
    )

    assert f"{column} = '{canonical_value}'" in validated.sql
    assert natural_value not in validated.sql


def test_enum_normalization_does_not_rewrite_non_enum_columns() -> None:
    validated = SqlValidator().validate(
        "SELECT contract_no FROM mart.v_sales_performance WHERE customer_name='华东地区'",
        ALLOWED,
    )

    assert "customer_name = '华东地区'" in validated.sql
