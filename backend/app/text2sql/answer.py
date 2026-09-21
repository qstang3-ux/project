import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.errors import AppError
from app.text2sql.types import AnswerBundle, ModelAnswerOutput, QueryResult


class AnswerValidator:
    _chart_keys = {"type", "title", "xField", "yFields", "nameField", "valueField", "unit"}
    _number_pattern = re.compile(r"(?<!\d)[-+]?\d[\d,]*(?:\.\d+)?(?:万|亿)?")

    def validate(
        self,
        output: ModelAnswerOutput,
        question: str,
        result: QueryResult,
        generate_chart: bool,
    ) -> AnswerBundle:
        answer = output.answer.strip()
        if not answer or len(answer) > 4000:
            raise AppError("MODEL_INVALID_RESPONSE", "模型返回的答案结构无效", 502)
        self._validate_answer_facts(answer, question, result)
        questions = output.follow_up_questions
        if len(questions) > 3 or any(
            not isinstance(item, str) or not item.strip() or len(item) > 200 for item in questions
        ):
            raise AppError("MODEL_INVALID_RESPONSE", "模型返回的推荐问题结构无效", 502)
        chart = self._validate_chart(output.chart, result, generate_chart)
        return AnswerBundle(answer, chart, [item.strip() for item in questions])

    def _validate_answer_facts(self, answer: str, question: str, result: QueryResult) -> None:
        if not result.rows and not any(
            marker in answer for marker in ("未查询到", "没有", "无数据")
        ):
            raise AppError("MODEL_INVALID_RESPONSE", "模型未正确说明空结果", 502)
        if (result.truncated or result.row_count > 100) and not any(
            marker in answer for marker in ("截断", "上限", "部分结果")
        ):
            raise AppError("MODEL_INVALID_RESPONSE", "模型未声明结果截断", 502)
        allowed = self._numbers(question)
        allowed.add(Decimal(0))
        allowed.update({Decimal(2026), Decimal(5), Decimal(31)})
        allowed.add(Decimal(result.row_count))
        allowed.update(Decimal(value) for value in range(1, min(result.row_count, 100) + 1))
        for row in result.rows:
            for value in row.values():
                allowed.update(self._numbers(str(value)))
        numeric_keys = {
            str(column["key"])
            for column in result.columns
            if column.get("dataType") in {"integer", "decimal", "percent"}
        }
        for key in numeric_keys:
            values = [self._decimal(row.get(key)) for row in result.rows]
            numbers = [value for value in values if value is not None]
            if numbers:
                total = sum(numbers, Decimal(0))
                allowed.add(total)
                allowed.add(total / Decimal(len(numbers)))
        for number in self._numbers(answer):
            if not any(
                abs(number - expected) <= max(abs(expected) * Decimal("0.001"), Decimal("0.1"))
                for expected in allowed
            ):
                raise AppError("MODEL_INVALID_RESPONSE", "模型答案包含结果中不存在的数字", 502)

    @staticmethod
    def _decimal(value: Any) -> Decimal | None:
        if isinstance(value, bool) or value is None:
            return None
        try:
            return Decimal(str(value).replace(",", ""))
        except InvalidOperation:
            return None

    def _numbers(self, text: str) -> set[Decimal]:
        values: set[Decimal] = set()
        for token in self._number_pattern.findall(text):
            multiplier = Decimal(1)
            if token.endswith("万"):
                multiplier = Decimal(10_000)
                token = token[:-1]
            elif token.endswith("亿"):
                multiplier = Decimal(100_000_000)
                token = token[:-1]
            try:
                values.add(Decimal(token.replace(",", "")) * multiplier)
            except InvalidOperation:
                continue
        return values

    def _validate_chart(
        self, chart: dict[str, Any], result: QueryResult, generate_chart: bool
    ) -> dict[str, Any]:
        if not isinstance(chart, dict) or set(chart) - self._chart_keys:
            raise AppError("MODEL_INVALID_RESPONSE", "模型返回的图表结构无效", 502)
        chart_type = chart.get("type")
        if chart_type not in {"bar", "line", "pie", "metric", "none"}:
            raise AppError("MODEL_INVALID_RESPONSE", "模型返回了不支持的图表类型", 502)
        if not generate_chart and chart_type != "none":
            raise AppError("MODEL_INVALID_RESPONSE", "模型未遵循禁用图表设置", 502)
        fields = {str(column["key"]) for column in result.columns}
        references: list[str] = []
        if chart_type in {"bar", "line"}:
            x_field = chart.get("xField")
            y_fields = chart.get("yFields")
            if not isinstance(x_field, str) or not isinstance(y_fields, list) or not y_fields:
                raise AppError("MODEL_INVALID_RESPONSE", "模型返回的图表字段不完整", 502)
            if any(not isinstance(field, str) for field in y_fields):
                raise AppError("MODEL_INVALID_RESPONSE", "模型返回的图表字段无效", 502)
            references = [x_field, *y_fields]
        elif chart_type == "pie":
            name_field = chart.get("nameField")
            value_field = chart.get("valueField")
            if not isinstance(name_field, str) or not isinstance(value_field, str):
                raise AppError("MODEL_INVALID_RESPONSE", "模型返回的饼图字段不完整", 502)
            references = [name_field, value_field]
        elif chart_type == "metric":
            value_field = chart.get("valueField")
            if not isinstance(value_field, str):
                raise AppError("MODEL_INVALID_RESPONSE", "模型返回的指标字段不完整", 502)
            references = [value_field]
        if any(field not in fields for field in references):
            raise AppError("MODEL_INVALID_RESPONSE", "模型引用了结果集中不存在的图表字段", 502)
        return chart


class AnswerBuilder:
    """Deterministic answer generator used only by the local/test Fake adapter."""

    def build(self, question: str, result: QueryResult, generate_chart: bool) -> AnswerBundle:
        if not result.rows:
            return AnswerBundle("按当前条件未查询到数据。", {"type": "none"}, [])
        first = result.rows[0]
        if len(first) == 1:
            key, value = next(iter(first.items()))
            answer = f"截至数据日期 2026-05-31，{key}为 {value}。"
        else:
            answer = f"已查询到 {result.row_count} 条结果。排名或趋势以表格中的查询结果为准。"
        if result.truncated:
            answer += " 结果已按安全上限截断。"
        chart = self._chart(question, result) if generate_chart else {"type": "none"}
        followups = ["可以按经营单元进一步拆分吗？", "可以查看同比变化吗？"]
        return AnswerBundle(answer, chart, followups[:3])

    @staticmethod
    def _chart(question: str, result: QueryResult) -> dict[str, object]:
        keys = [column["key"] for column in result.columns]
        if len(keys) == 1:
            return {"type": "metric", "title": question, "valueField": keys[0], "yFields": []}
        if "趋势" in question or "每月" in question or "季度" in question:
            return {"type": "line", "title": question, "xField": keys[0], "yFields": keys[1:]}
        if "占比" in question:
            return {
                "type": "pie",
                "title": question,
                "nameField": keys[0],
                "valueField": keys[1],
                "yFields": [],
            }
        if result.row_count <= 30:
            return {"type": "bar", "title": question, "xField": keys[0], "yFields": keys[1:]}
        return {"type": "none"}
