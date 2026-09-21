from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GOLDEN_PATH = Path("tests/evaluation/real-model-golden-100.json")
OUTPUT_PATH = Path("tests/evaluation/rag-retrieval-100-cases.json")

EXTRA_CASES = [
    ("收入达成目标了吗", "metric.achievement_rate"),
    ("哪些代表处离年度目标还很远", "metric.achievement_rate"),
    ("商解收入完成目标的比例", "metric.solution_target"),
    ("解决方案业务目标缺口", "metric.solution_target"),
    ("销售确认收入按月变化", "metric.revenue"),
    ("本年累计确认的营业收入", "metric.revenue"),
    ("产品线贡献占总收入多少", "metric.product_share"),
    ("三类产品收入结构", "metric.product_share"),
    ("和去年同期相比收入如何", "metric.year_over_year"),
    ("收入同比增幅", "metric.year_over_year"),
    ("还有多少钱应该收但没收", "metric.receivable"),
    ("合同应收余额排行", "metric.receivable"),
    ("项目机会的综合风险", "business_rule.pipeline_risk"),
    ("哪些商机存在签约交付风险", "schema.pipeline_risk"),
    ("项目预计落地时间分布", "schema.pipeline_risk"),
    ("尚未排产项目金额", "schema.pipeline_risk"),
    ("客户合同和收入明细", "schema.sales_performance"),
    ("不同省份的回款表现", "schema.sales_performance"),
    ("各区域年度商业指标", "metric.commercial_target"),
    ("代表处商业目标排行榜", "metric.commercial_target"),
]

RELEVANT_ALTERNATIVES = {
    "T09": ["schema.target_achievement", "metric.commercial_target", "metric.achievement_rate"],
    "T11": ["schema.target_achievement", "metric.commercial_target", "metric.revenue"],
    "S03": ["metric.revenue", "columns.sales_performance.time_amount"],
    "S09": ["schema.sales_performance", "columns.sales_performance.dimensions"],
    "S19": ["metric.revenue", "columns.sales_performance.dimensions", "schema.target_achievement"],
    "S23": ["metric.product_share", "metric.revenue", "columns.sales_performance.dimensions"],
    "S24": ["metric.revenue", "columns.sales_performance.time_amount"],
    "S26": ["metric.revenue", "schema.target_achievement"],
    "S33": ["metric.revenue", "columns.sales_performance.dimensions"],
    "S35": ["metric.revenue", "schema.sales_performance"],
    "S38": ["metric.revenue", "schema.sales_performance"],
    "S39": ["metric.revenue", "columns.sales_performance.time_amount"],
    "S43": ["metric.revenue", "schema.sales_performance"],
    "R10": ["schema.pipeline_risk", "business_rule.pipeline_risk"],
    "R12": ["business_rule.pipeline_risk", "schema.pipeline_risk"],
    "R16": ["metric.project_count", "schema.pipeline_risk"],
}

EXTRA_RELEVANT_ALTERNATIVES = {
    81: ["schema.target_achievement", "metric.revenue", "metric.commercial_target"],
    82: ["schema.target_achievement", "metric.commercial_target"],
    94: ["business_rule.pipeline_risk", "schema.pipeline_risk"],
}


def expected_key(case: dict[str, Any]) -> str:
    case_id = str(case["id"])
    category = str(case["category"])
    if case_id.startswith("T"):
        if case_id in {"T01", "T06", "T07", "T15"}:
            return "metric.commercial_target"
        if case_id in {"T02", "T08", "T12", "T13"}:
            return "metric.solution_target"
        if case_id in {"T03", "T04", "T05", "T10", "T11"}:
            return "metric.achievement_rate"
        return "metric.revenue"
    if case_id == "S14":
        return "metric.product_share"
    if case_id == "S42":
        return "metric.year_over_year"
    if case_id in {"S04", "S29", "S30"}:
        return "metric.receivable"
    if category in {
        "revenue_total",
        "monthly_trend",
        "quarter_trend",
        "unit_group",
        "unit_ranking",
        "month_ranking",
        "month_total",
        "yoy",
    }:
        return "metric.revenue"
    if case_id.startswith("S"):
        return "schema.sales_performance"
    if category.startswith("risk_") or category in {
        "competition_risk",
        "signing_risk",
        "delivery_risk",
    }:
        return "business_rule.pipeline_risk"
    return "schema.pipeline_risk"


def expected_keys(case: dict[str, Any]) -> list[str]:
    primary = expected_key(case)
    return list(dict.fromkeys([primary, *RELEVANT_ALTERNATIVES.get(str(case["id"]), [])]))


def main() -> None:
    suite = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    data_cases = [case for case in suite["cases"] if case["kind"] == "data"]
    rows = [
        {
            "id": f"RAG100-{index:03d}",
            "question": case["question"],
            "expectedStableKeys": expected_keys(case),
            "sourceCaseId": case["id"],
        }
        for index, case in enumerate(data_cases, start=1)
    ]
    rows.extend(
        {
            "id": f"RAG100-{index:03d}",
            "question": question,
            "expectedStableKeys": list(
                dict.fromkeys([key, *EXTRA_RELEVANT_ALTERNATIVES.get(index, [])])
            ),
            "hardParaphrase": True,
        }
        for index, (question, key) in enumerate(EXTRA_CASES, start=81)
    )
    if len(rows) != 100 or len({row["question"] for row in rows}) != 100:
        raise RuntimeError("RAG golden set must contain 100 unique questions")
    OUTPUT_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(rows)} cases to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
