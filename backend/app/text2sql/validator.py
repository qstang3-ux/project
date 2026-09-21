from dataclasses import dataclass

from sqlglot import exp, parse
from sqlglot.errors import ParseError, TokenError

from app.core.errors import SqlValidationError
from app.text2sql.types import ValidatedSql

ALLOWED_FUNCTIONS = {
    "sum",
    "count",
    "avg",
    "min",
    "max",
    "round",
    "coalesce",
    "nullif",
    "greatest",
    "least",
    "extract",
    "date_trunc",
    "lag",
    "lead",
    "row_number",
    "rank",
    "dense_rank",
    "and",
    "or",
    "case",
    "if",
    "cast",
}
FORBIDDEN_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Copy,
    exp.Merge,
    exp.Transaction,
    exp.Into,
    exp.Lock,
)
OBJECT_COLUMNS = {
    "mart.v_sales_performance": {
        "contract_id",
        "contract_no",
        "contract_name",
        "signed_at",
        "year",
        "business_month",
        "business_unit_code",
        "business_unit_name",
        "region",
        "industry_major_name",
        "industry_name",
        "product_line_code",
        "product_line_name",
        "customer_name",
        "customer_level",
        "customer_category",
        "province",
        "contract_amount_tax_included",
        "contract_amount_tax_excluded",
        "revenue_amount",
        "payment_amount",
        "recognized_total",
        "paid_total",
        "unrecognized_amount",
        "unpaid_amount",
        "receivable_amount",
        "status",
        "is_statistical",
        "special_program",
    },
    "mart.v_target_achievement": {
        "year",
        "business_unit_code",
        "business_unit_name",
        "region",
        "commercial_target_amount",
        "solution_target_amount",
        "revenue_amount",
        "solution_revenue_amount",
        "achievement_rate",
        "solution_achievement_rate",
    },
    "mart.v_pipeline_risk": {
        "project_id",
        "opportunity_no",
        "project_name",
        "business_unit_code",
        "business_unit_name",
        "industry_name",
        "product_line_name",
        "stage",
        "competition_risk",
        "signing_risk",
        "delivery_risk",
        "overall_risk",
        "expected_landing_date",
        "amount_tax_excluded",
        "production_scheduled",
        "progress_note",
    },
}


@dataclass(frozen=True)
class SqlValidator:
    max_rows: int = 500

    def validate(self, sql: str, allowed_objects: set[str]) -> ValidatedSql:
        try:
            statements = [
                statement for statement in parse(sql, read="postgres") if statement is not None
            ]
        except (ParseError, TokenError) as exc:
            raise SqlValidationError("SQL 无法解析") from exc
        if len(statements) != 1:
            raise SqlValidationError("仅允许单条查询语句")
        statement = statements[0]
        if isinstance(statement, FORBIDDEN_TYPES) or not isinstance(statement, exp.Query):
            raise SqlValidationError("仅允许 SELECT 或只读 CTE")
        if any(isinstance(node, FORBIDDEN_TYPES) for node in statement.walk()):
            raise SqlValidationError("查询包含写入或管理语句")
        with_clause = statement.args.get("with")
        if isinstance(with_clause, exp.With) and with_clause.args.get("recursive"):
            raise SqlValidationError("禁止递归 CTE")
        derived_sources = self._derived_sources(statement)
        scalar_sources = self._scalar_sources(statement)
        cte_names = {cte.alias_or_name.lower() for cte in statement.find_all(exp.CTE)}
        objects: set[str] = set()
        table_aliases: dict[str, str] = {}
        table_count = 0
        for table in statement.find_all(exp.Table):
            name = table.name.lower()
            if name in cte_names and not table.db:
                derived_sources[table.alias_or_name.lower()] = derived_sources.get(name, set())
                continue
            table_count += 1
            if not table.db:
                raise SqlValidationError("所有数据对象必须显式使用 mart Schema")
            full_name = f"{table.db.lower()}.{name}"
            if table.catalog or full_name not in allowed_objects or table.db.lower() != "mart":
                raise SqlValidationError(f"禁止访问对象 {full_name}")
            objects.add(full_name)
            table_aliases[table.alias_or_name.lower()] = full_name
        if not objects:
            raise SqlValidationError("查询未访问允许的数据对象")
        for star in statement.find_all(exp.Star):
            if not isinstance(star.parent, exp.Count):
                raise SqlValidationError("禁止 SELECT *")
        for function in statement.find_all(exp.Func):
            name = str(function.sql_name()).lower()  # type: ignore[no-untyped-call]
            if name and name not in ALLOWED_FUNCTIONS:
                raise SqlValidationError(f"函数 {name} 不在白名单")
        allowed_columns = set().union(*(OBJECT_COLUMNS.get(obj, set()) for obj in objects))
        projected_aliases = {alias.alias.lower() for alias in statement.find_all(exp.Alias)}
        derived_columns = set().union(*derived_sources.values()) if derived_sources else set()
        for column in statement.find_all(exp.Column):
            name = column.name.lower()
            qualifier = column.table.lower()
            if qualifier in derived_sources:
                if name not in derived_sources[qualifier]:
                    raise SqlValidationError(f"派生列 {column.sql()} 不存在")
                continue
            if column.table:
                source = table_aliases.get(qualifier)
                if source is None:
                    raise SqlValidationError(f"未知数据源限定符 {column.table}")
                if name not in OBJECT_COLUMNS.get(source, set()):
                    raise SqlValidationError(f"列 {column.sql()} 不在白名单")
            elif name not in allowed_columns | projected_aliases | derived_columns:
                raise SqlValidationError(f"列 {name} 不在白名单")
        if table_count > 1:
            joins = list(statement.find_all(exp.Join))
            if any(
                join.args.get("on") is None
                and join.args.get("using") is None
                and not self._is_scalar_join(join, scalar_sources)
                for join in joins
            ):
                raise SqlValidationError("禁止无连接条件的多表查询")
        self._apply_limit(statement)
        return ValidatedSql(sql, statement.sql(dialect="postgres"), tuple(sorted(objects)))

    @staticmethod
    def _derived_sources(statement: exp.Query) -> dict[str, set[str]]:
        sources: dict[str, set[str]] = {}
        for cte in statement.find_all(exp.CTE):
            query = cte.this
            if isinstance(query, exp.Query):
                sources[cte.alias_or_name.lower()] = {
                    expression.alias_or_name.lower()
                    for expression in query.selects
                    if expression.alias_or_name
                }
        for subquery in statement.find_all(exp.Subquery):
            if not subquery.alias_or_name or not isinstance(subquery.this, exp.Query):
                continue
            sources[subquery.alias_or_name.lower()] = {
                expression.alias_or_name.lower()
                for expression in subquery.this.selects
                if expression.alias_or_name
            }
        return sources

    @classmethod
    def _scalar_sources(cls, statement: exp.Query) -> set[str]:
        sources = {
            cte.alias_or_name.lower()
            for cte in statement.find_all(exp.CTE)
            if isinstance(cte.this, exp.Query) and cls._is_scalar_query(cte.this)
        }
        sources.update(
            subquery.alias_or_name.lower()
            for subquery in statement.find_all(exp.Subquery)
            if subquery.alias_or_name
            and isinstance(subquery.this, exp.Query)
            and cls._is_scalar_query(subquery.this)
        )
        return sources

    @staticmethod
    def _is_scalar_query(query: exp.Query) -> bool:
        limit = query.args.get("limit")
        if isinstance(limit, exp.Limit):
            expression = limit.expression
            if isinstance(expression, exp.Literal) and expression.is_int:
                return int(expression.this) <= 1
        if not isinstance(query, exp.Select):
            return False
        if query.args.get("from") is None:
            return True
        return query.args.get("group") is None and any(
            isinstance(node, exp.AggFunc) for node in query.walk()
        )

    @classmethod
    def _is_scalar_join(cls, join: exp.Join, scalar_sources: set[str]) -> bool:
        target = join.this
        if isinstance(target, exp.Table):
            return not target.db and target.name.lower() in scalar_sources
        return (
            isinstance(target, exp.Subquery)
            and isinstance(target.this, exp.Query)
            and cls._is_scalar_query(target.this)
        )

    def _apply_limit(self, statement: exp.Query) -> None:
        limit = statement.args.get("limit")
        if limit is None:
            statement.set("limit", exp.Limit(expression=exp.Literal.number(self.max_rows)))
            return
        expression = limit.expression
        if isinstance(expression, exp.Literal) and expression.is_int:
            if int(expression.this) > self.max_rows:
                limit.set("expression", exp.Literal.number(self.max_rows))
            return
        raise SqlValidationError("LIMIT 必须为整数常量")
