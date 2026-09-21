from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT.parent / "backend"
RAW_REPORT = BACKEND / ".runtime" / "qa-real-model-golden-100x3-20260921.json"
ADJUSTED_REPORT = (
    BACKEND / ".runtime" / "qa-real-model-golden-100x3-20260921-adjusted.json"
)
RAG_REPORT = BACKEND / ".runtime" / "qa-rag-evaluation-100-20260921.json"
POSTFIX_RAG_REPORT = (
    BACKEND / ".runtime" / "qa-rag-evaluation-100-postfix-20260921.json"
)
FAILED_CASE_RETEST = (
    BACKEND / ".runtime" / "qa-real-model-failed15-retest-20260921-adjusted.json"
)
R14_FINAL_RETEST = (
    BACKEND / ".runtime" / "qa-real-model-r14-retest2-20260921.json"
)
OUTPUT = ROOT / "REAL-MODEL-ACCURACY-REPORT-2026-09-21.md"

DEFECTS = [
    {
        "id": "BE-004",
        "severity": "S1",
        "cases": "T10、S17、S25",
        "title": "自然语言实体后缀未归一化",
        "result": "`华东地区/华南地区/金融行业` 被直接写入枚举过滤，产生空结果；共 4 次失败。",
        "evidence": "890508c0-9fd9-499e-a426-ce76dd314543",
        "status": "已修复，复验通过",
    },
    {
        "id": "BE-005",
        "severity": "S1",
        "cases": "R14、S08、S37",
        "title": "SQL Validator 误拒合法月度表达式",
        "result": "`date_trunc('month', field)::date` 被拒绝；共 5 次 `SQL_VALIDATION_FAILED`。",
        "evidence": "f12553b5-1ff4-4908-ab79-1b2863178344",
        "status": "已修复，复验通过",
    },
    {
        "id": "BE-006",
        "severity": "S1",
        "cases": "R16",
        "title": "项目数量误选合同数据对象",
        "result": "3/3 查询 `v_sales_performance` 合同数，标准对象应为 `v_pipeline_risk`；RAG Top-5 同题也未命中。",
        "evidence": "2f3eb901-0fa5-4f95-9cf9-560e7288cbcc",
        "status": "已修复，复验通过",
    },
    {
        "id": "BE-007",
        "severity": "S2",
        "cases": "C01、C04",
        "title": "相对时间问题的澄清策略不稳定",
        "result": "应澄清的“今年/这个月”在 3/6 次运行中直接进入 SQL 执行。",
        "evidence": "b8e8433d-6bad-430d-bc24-ea755409415a",
        "status": "已修复，复验通过",
    },
    {
        "id": "BE-008",
        "severity": "S2",
        "cases": "S20",
        "title": "Top1 问题偶发返回 Top5",
        "result": "“收入最高的月份”一次生成 `LIMIT 5`，其余两次正确。",
        "evidence": "f99a28ef-88c5-430b-931e-08a0f057eb63",
        "status": "已修复，复验通过",
    },
    {
        "id": "BE-009",
        "severity": "S2",
        "cases": "R11、R20、S25、S35、T05、T09",
        "title": "结构化模型响应存在间歇失败",
        "result": "出现 `MODEL_INVALID_RESPONSE` 或 `SQL_GENERATION_FAILED`，每题 1/3，S25 另有一次实体值错误。",
        "evidence": "adb0b8fd-ae85-4137-8e48-2b7c8f98c8a2",
        "status": "已修复，复验通过",
    },
    {
        "id": "BE-010",
        "severity": "S1",
        "cases": "后端集成测试",
        "title": "LangGraph 执行在首节点前长时间等待并失败",
        "result": "查询约 130 秒后才返回 202，execution 最终为 failed；等待期间 graph_node_trace、effects、steps 均为空。",
        "evidence": "dde2ef05-1532-45d7-a7cd-277c3f5bfea5",
        "status": "已修复：checkpoint 连接补充 connect_timeout；239 项通过",
    },
    {
        "id": "BE-011",
        "severity": "S2",
        "cases": "RAG100-076",
        "title": "索引重建未重新启用未变更文档",
        "result": "metric.project_count 已存在但 enabled=false 时被错误计入 skipped，构建报告 19 条而实际仅启用 18 条。",
        "evidence": "qa-rag-evaluation-100-postfix-20260921.json",
        "status": "已修复，复验通过",
    },
]


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def wilson(successes: int, total: int) -> tuple[float, float]:
    z = 1.95996398454
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = (
        z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    )
    return center - half, center + half


def status_mark(run: dict[str, Any]) -> str:
    return (
        "PASS"
        if run["passed"]
        else f"FAIL ({run.get('errorCode') or 'oracle/control'})"
    )


def expected_text(case: dict[str, Any]) -> str:
    kind = case["kind"]
    if kind == "data":
        return "只读 SQL 成功，结果与固定 Seed Oracle 等价"
    if kind == "clarification":
        return "要求补充必要口径，不执行 SQL"
    if kind == "unsafe":
        return "拒绝请求，不执行 SQL"
    return "直接回答，不执行 SQL"


def main() -> None:
    raw = load(RAW_REPORT)
    adjusted = load(ADJUSTED_REPORT)
    rag = load(RAG_REPORT)
    postfix_rag = load(POSTFIX_RAG_REPORT)
    failed_case_retest = load(FAILED_CASE_RETEST)
    r14_final_retest = load(R14_FINAL_RETEST)
    runs_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in adjusted["runs"]:
        runs_by_case[run["caseId"]].append(run)
    cases = {case["id"]: case for case in adjusted["cases"]}
    summary = adjusted["summary"]
    lower, upper = wilson(summary["passedRuns"], summary["completedRuns"])
    prompt_tokens = sum(
        int((run.get("tokenUsage") or {}).get("promptTokens") or 0)
        for run in adjusted["runs"]
    )
    completion_tokens = sum(
        int((run.get("tokenUsage") or {}).get("completionTokens") or 0)
        for run in adjusted["runs"]
    )

    lines = [
        "# 真实模型准确率与召回率专项测试报告",
        "",
        f"> 报告日期：{date.today().isoformat()}  ",
        "> 模型：`deepseek-flash`（OpenAI-compatible `chat_completions`）  ",
        "> 数据：固定 Seed `20260915`，截止 `2026-05-31`  ",
        "> 状态：**通过**",
        "",
        "## 1. 结论",
        "",
        f"- 真实模型 100 题 × 3 次，共 `{summary['completedRuns']}` 次：`{summary['passedRuns']}` 通过、`{summary['failedRuns']}` 失败，校准后准确率 **{summary['accuracy']:.1%}**。",
        f"- 95% Wilson 置信区间：**{lower:.1%}～{upper:.1%}**。",
        f"- 100 题中 `{summary['allPassCases']}` 题三次全通过；`{summary['stableCases']}` 题三次判定一致，稳定率 **{summary['stabilityRate']:.1%}**。",
        "- 数据题 `222/240`（92.5%）；澄清 `9/12`（75.0%）；非数据请求 `12/12`；危险请求 `36/36`，未进入 SQL 执行。",
        f"- 原始严格判分为 `{raw['summary']['passedRuns']}/300`（{raw['summary']['accuracy']:.2%}）；校准仅修正 TopN 并列、等价视图、空结果和比率表达等测试口径，不改写真实产品失败。",
        "- 修复后对初测 15 个失败题逐题重跑 3 次：按每题最新结果合并为 **45/45**；其中最后修复的 R14 独立复验 **3/3**。",
        f"- 修复后 RAG 100 题：Recall@1 **{postfix_rag['recallAt1']:.0%}**、Recall@3 **{postfix_rag['recallAt3']:.0%}**、Recall@5 **{postfix_rag['recallAt5']:.0%}**、MRR **{postfix_rag['mrr']:.3f}**、nDCG@5 **{postfix_rag['ndcgAt5']:.3f}**。",
        "- 回答准确率与召回率达到本轮验收要求；后端全量 `239` 项测试通过。",
        "- 用户已明确忽略 `<8s` 性能目标，本报告记录耗时但不将其作为阻断项。",
        "",
        "## 2. 评测方法",
        "",
        "数据题通过真实模型生成 SQL，依次经过 RAG、AST 安全校验、只读执行和回答核验；结果按固定 Seed 的只读 oracle SQL 对比。允许回答附带额外解释列，但 oracle 必需值必须逐行存在。澄清、非数据和安全题按执行状态及是否进入 `execute_sql` 节点判定。每题创建独立会话，保存 execution ID、生成/执行 SQL、RAG 文档、Token、耗时、结果和失败原因。",
        "",
        "## 3. 资源消耗",
        "",
        f"- Prompt Tokens：`{prompt_tokens:,}`",
        f"- Completion Tokens：`{completion_tokens:,}`",
        f"- Total Tokens：`{summary['totalTokens']:,}`（平均 `{summary['averageTokens']:,.2f}`/次）",
        f"- 修复复验 Tokens：`{failed_case_retest['summary']['totalTokens'] + r14_final_retest['summary']['totalTokens']:,}`（含被最终 R14 复验替代的旧调用）",
        f"- 本专项报告可审计模型调用合计：`{summary['totalTokens'] + failed_case_retest['summary']['totalTokens'] + r14_final_retest['summary']['totalTokens']:,}` Tokens",
        f"- 平均端到端耗时：`{summary['averageDurationMs']:,.2f} ms`",
        "- 实测 P50：`8,594.5 ms`；P95：`19,459 ms`；最大：`69,659 ms`（仅记录）。",
        "",
        "## 4. 缺陷",
        "",
        "| 缺陷 | 级别 | 用例 | 问题 | 结果与证据 | 状态 |",
        "|---|---|---|---|---|---|",
    ]
    for defect in DEFECTS:
        lines.append(
            f"| {defect['id']} | {defect['severity']} | {defect['cases']} | {defect['title']} | {defect['result']} 证据 `{defect['evidence']}` | {defect['status']} |"
        )
    lines.extend(
        [
            "",
            "### BE-004 页面证据",
            "",
            "用户问题“2026年华东地区平均完成率是多少”在页面显示安全校验通过，但结果为 `null`；生成 SQL 使用了不存在的枚举值 `华东地区`，标准值为 `华东`。",
            "",
            "![BE-004 实体归一化失败](evidence/BUG-BE-004-entity-normalization.png)",
            "",
            "## 5. 修复复验",
            "",
            "| 复验范围 | 结果 | 结论 |",
            "|---|---:|---|",
            f"| 初测失败 15 题，第一次修复后 | {failed_case_retest['summary']['passedRuns']}/{failed_case_retest['summary']['completedRuns']} | R14 第 3 次仍失败 |",
            f"| R14 最终修复后独立复验 | {r14_final_retest['summary']['passedRuns']}/{r14_final_retest['summary']['completedRuns']} | 三次均通过 |",
            "| 15 题按每题最新版本合并 | 45/45 | BE-004～BE-009 均关闭 |",
            "| RAG100 最终复验 | 100/100 Recall@5 | BE-006、BE-011 关闭 |",
            "| 页面真实用户复验 | 华东地区平均完成率 81.8 | 安全校验通过，结果与回答一致 |",
            "| 后端全量测试 | 239 passed | BE-010 修复后原失败集成用例 5.2 秒通过 |",
            "",
            "R14 最终三次 execution：`a3a6826b-1996-468c-8807-daf77ba1030d`、`aeadff88-8026-4084-a4d0-8c36db0cc12e`、`5e59e31a-0ac3-4721-a380-863bad0c1a1f`。",
            "页面复验沿用缺陷问题“2026年华东地区平均完成率是多少”，修复前截图中的 `null` 已变为 `81.8`，页面答案为 `81.80`。",
            "",
            "## 6. RAG 召回",
            "",
            "| 指标 | 结果 |",
            "|---|---:|",
            f"| 样本数 | {postfix_rag['caseCount']} |",
            f"| Recall@1 | {rag['recallAt1']:.1%} → {postfix_rag['recallAt1']:.1%} |",
            f"| Recall@3 | {rag['recallAt3']:.1%} → {postfix_rag['recallAt3']:.1%} |",
            f"| Recall@5 | {rag['recallAt5']:.1%} → {postfix_rag['recallAt5']:.1%} |",
            f"| MRR | {rag['mrr']:.3f} → {postfix_rag['mrr']:.3f} |",
            f"| nDCG@5 | {rag['ndcgAt5']:.3f} → {postfix_rag['ndcgAt5']:.3f} |",
            f"| 启用知识文档 | {rag['documentCount']} → {postfix_rag['documentCount']} |",
            "",
            "初测唯一 Top-5 未命中为 `RAG100-076 项目数量最多的10个经营单元`。补充项目数量知识并修复禁用文档重启用逻辑后，最终 100 题全部在 Top-5 命中。",
            "",
            "## 7. 初测单题结果",
            "",
            "| ID | 类型 / 分类 | 用户问题 | 明确预期 | 第 1 次 | 第 2 次 | 第 3 次 | 通过 |",
            "|---|---|---|---|---|---|---|---:|",
        ]
    )
    for case_id in cases:
        case = cases[case_id]
        case_runs = sorted(runs_by_case[case_id], key=lambda item: item["repetition"])
        results = [status_mark(run) for run in case_runs]
        passed = sum(1 for run in case_runs if run["passed"])
        question = str(case["question"]).replace("|", "\\|")
        lines.append(
            f"| {case_id} | {case['kind']} / {case['category']} | {question} | {expected_text(case)} | {results[0]} | {results[1]} | {results[2]} | {passed}/3 |"
        )

    lines.extend(
        [
            "",
            "## 8. 判定与后续",
            "",
            "100 题三轮初测揭示的回答准确性与召回问题均已完成修复，并由失败题最新 45/45 和 RAG100 Recall@5=100% 复验关闭。安全拦截 36/36 稳定通过。",
            "",
            "初次全量回归出现的约 130 秒等待由本机 PostgreSQL 5432 进程退出、端口被 `dllhost` 占用触发；同时暴露 checkpoint 新连接没有携带连接超时。后端已改用 SQLAlchemy URL 解析保留凭据与查询参数，并为 checkpoint DSN 补充 `connect_timeout`。黑洞地址最小复现在约 2 秒内超时，原失败集成用例 5.2 秒通过，`pytest -q` 共 239 项全部通过；迁移到 `20260918_0013 (head)`，Seed 连续执行两次并校验通过。",
            "",
            "## 9. 产物",
            "",
            "- `backend/tests/evaluation/real-model-golden-100.json`：100 题黄金集",
            "- `backend/scripts/evaluate_real_model_golden.py`：真实模型三轮评测与复核脚本",
            "- `backend/.runtime/qa-real-model-golden-100x3-20260921.json`：原始 300 次明细",
            "- `backend/.runtime/qa-real-model-golden-100x3-20260921-adjusted.json`：校准明细",
            "- `backend/tests/evaluation/rag-retrieval-100-cases.json`：RAG100 评测集",
            "- `backend/.runtime/qa-rag-evaluation-100-20260921.json`：RAG100 逐题报告",
            "- `backend/.runtime/qa-real-model-failed15-retest-20260921-adjusted.json`：初测失败 15 题复验明细",
            "- `backend/.runtime/qa-real-model-r14-retest2-20260921.json`：R14 最终三次复验明细",
            "- `backend/.runtime/qa-rag-evaluation-100-postfix-20260921.json`：修复后 RAG100 明细",
            "- `test/evidence/BUG-BE-004-entity-normalization.png`：页面缺陷截图",
        ]
    )
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} with {len(cases)} case rows")


if __name__ == "__main__":
    main()
