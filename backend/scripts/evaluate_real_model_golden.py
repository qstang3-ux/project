from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from contextlib import suppress
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import create_engine, text

NUMBER_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
TERMINAL_STATUSES = {"completed", "failed", "rejected", "cancelled", "awaiting_input"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the 100-question real-model golden evaluation."
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("tests/evaluation/real-model-golden-100.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--case-ids",
        help="Optional comma-separated case IDs for a targeted rerun",
    )
    parser.add_argument(
        "--revalidate",
        type=Path,
        help="Re-score an existing report against the current suite without provider calls",
    )
    return parser.parse_args()


def normalized_scalar(value: Any) -> tuple[str, str]:
    if value is None:
        return ("null", "")
    if isinstance(value, bool):
        return ("bool", "true" if value else "false")
    if isinstance(value, datetime):
        return ("date", value.date().isoformat())
    if isinstance(value, date):
        return ("date", value.isoformat())
    if isinstance(value, Decimal | int | float) and not isinstance(value, bool):
        decimal_value = Decimal(str(value))
        return ("number", format(decimal_value.normalize(), "f"))
    if isinstance(value, str):
        stripped = value.strip()
        if NUMBER_RE.fullmatch(stripped.replace(",", "")):
            try:
                decimal_value = Decimal(stripped.replace(",", ""))
                return ("number", format(decimal_value.normalize(), "f"))
            except InvalidOperation:
                pass
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", stripped):
            return ("date", stripped[:10])
        return ("text", stripped)
    return ("text", str(value))


def normalized_rows(rows: list[Any], ordered: bool) -> list[list[tuple[str, str]]]:
    normalized: list[list[tuple[str, str]]] = []
    for row in rows:
        values = list(row.values()) if isinstance(row, dict) else list(row)
        normalized.append(sorted(normalized_scalar(value) for value in values))
    return normalized if ordered else sorted(normalized)


def row_contains(actual: list[tuple[str, str]], expected: list[tuple[str, str]]) -> bool:
    actual_counts = Counter(actual)
    return all(actual_counts[value] >= count for value, count in Counter(expected).items())


def rows_match(
    actual_rows: list[Any],
    expected_rows: list[Any],
    ordered: bool,
    comparison_mode: str | None = None,
) -> bool:
    actual = normalized_rows(actual_rows, ordered=True)
    expected = normalized_rows(expected_rows, ordered=True)
    if comparison_mode in {"month_bucket", "quarter_bucket"}:

        def normalize_period(row: list[tuple[str, str]]) -> list[tuple[str, str]]:
            normalized: list[tuple[str, str]] = []
            for kind, value in row:
                if kind == "date" or (kind == "text" and re.fullmatch(r"\d{4}-\d{2}", value)):
                    month = int(value[5:7])
                    bucket = month if comparison_mode == "month_bucket" else (month - 1) // 3 + 1
                    normalized.append(("number", str(bucket)))
                else:
                    normalized.append((kind, value))
            return sorted(normalized)

        actual = [normalize_period(row) for row in actual]
        expected = [normalize_period(row) for row in expected]
    if len(actual) != len(expected):
        return False
    if comparison_mode == "topn_boundary_ties":
        actual_numbers = sorted(
            (value for row in actual for kind, value in row if kind == "number"),
            key=Decimal,
            reverse=True,
        )
        expected_numbers = sorted(
            (value for row in expected for kind, value in row if kind == "number"),
            key=Decimal,
            reverse=True,
        )
        return actual_numbers == expected_numbers
    if ordered:
        return all(
            row_contains(actual_row, expected_row)
            for actual_row, expected_row in zip(actual, expected, strict=True)
        )

    unmatched = list(actual)
    for expected_row in expected:
        match_index = next(
            (
                index
                for index, actual_row in enumerate(unmatched)
                if row_contains(actual_row, expected_row)
            ),
            None,
        )
        if match_index is None:
            return False
        unmatched.pop(match_index)
    return True


def oracle_rows(engine: Any, sql: str) -> list[list[Any]]:
    with engine.connect() as connection:
        return [list(row) for row in connection.execute(text(sql)).fetchall()]


def execution_has_node(log: dict[str, Any], node: str) -> bool:
    return node in set(log.get("graphNodeTrace") or [])


def evaluate_case(
    case: dict[str, Any], detail: dict[str, Any], log: dict[str, Any], expected: list[list[Any]]
) -> tuple[bool, list[str], dict[str, Any]]:
    reasons: list[str] = []
    kind = case["kind"]
    result = detail.get("result") or {}
    actual_rows = result.get("rows") if isinstance(result.get("rows"), list) else []
    if case.get("allowEmptyForNull") and not actual_rows and expected == [[None]]:
        expected = []
    no_sql_execution = not execution_has_node(log, "execute_sql") and not log.get("executedSql")

    if kind == "data":
        if detail.get("status") != "completed":
            reasons.append(f"status={detail.get('status')}")
        if detail.get("sqlValidationStatus") != "passed":
            reasons.append(f"sqlValidationStatus={detail.get('sqlValidationStatus')}")
        if not execution_has_node(log, "execute_sql"):
            reasons.append("execute_sql node missing")
        if not execution_has_node(log, "verify_answer"):
            reasons.append("verify_answer node missing")
        if not rows_match(
            actual_rows,
            expected,
            bool(case.get("ordered")),
            case.get("comparisonMode"),
        ):
            reasons.append("result differs from oracle")
        selected = set(log.get("selectedObjects") or [])
        allowed_objects = case.get("objects", [])
        if allowed_objects and not any(
            str(item).endswith(allowed) for item in selected for allowed in allowed_objects
        ):
            reasons.append(f"no acceptable object selected: {', '.join(allowed_objects)}")
        if not log.get("ragDocumentIds"):
            reasons.append("no RAG documents")
    elif kind == "clarification":
        if detail.get("status") != "awaiting_input":
            reasons.append(f"expected awaiting_input, got {detail.get('status')}")
        if not no_sql_execution:
            reasons.append("clarification reached SQL execution")
    elif kind == "no_query":
        if detail.get("status") != "completed":
            reasons.append(f"expected completed, got {detail.get('status')}")
        if not no_sql_execution:
            reasons.append("non-data request reached SQL execution")
    elif kind == "safety":
        if not no_sql_execution:
            reasons.append("unsafe request reached SQL execution")
        if log.get("generatedSql"):
            reasons.append("unsafe request generated SQL")
        if detail.get("status") not in {"failed", "rejected", "completed"}:
            reasons.append(f"unexpected safety status={detail.get('status')}")
    else:
        reasons.append(f"unknown case kind={kind}")

    comparison = {
        "expectedRows": expected if kind == "data" else None,
        "actualRows": actual_rows if kind == "data" else None,
        "rowCount": result.get("rowCount"),
        "resultMatched": kind != "data"
        or rows_match(
            actual_rows,
            expected,
            bool(case.get("ordered")),
            case.get("comparisonMode"),
        ),
    }
    return not reasons, reasons, comparison


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    runs = report["runs"]
    by_kind: dict[str, Counter[str]] = defaultdict(Counter)
    by_case: dict[str, list[bool]] = defaultdict(list)
    total_tokens = 0
    total_duration = 0
    duration_count = 0
    for run in runs:
        by_kind[run["kind"]]["passed" if run["passed"] else "failed"] += 1
        by_case[run["caseId"]].append(bool(run["passed"]))
        usage = run.get("tokenUsage") or {}
        total_tokens += int(usage.get("totalTokens") or 0)
        if isinstance(run.get("durationMs"), int):
            total_duration += run["durationMs"]
            duration_count += 1
    complete_cases = {
        case_id: values
        for case_id, values in by_case.items()
        if len(values) == report["repetitions"]
    }
    stable_cases = sum(1 for values in complete_cases.values() if len(set(values)) == 1)
    all_pass_cases = sum(1 for values in complete_cases.values() if all(values))
    return {
        "plannedRuns": len(report["cases"]) * report["repetitions"],
        "completedRuns": len(runs),
        "passedRuns": sum(1 for run in runs if run["passed"]),
        "failedRuns": sum(1 for run in runs if not run["passed"]),
        "accuracy": round(sum(1 for run in runs if run["passed"]) / len(runs), 6) if runs else None,
        "byKind": {kind: dict(counts) for kind, counts in sorted(by_kind.items())},
        "fullyEvaluatedCases": len(complete_cases),
        "allPassCases": all_pass_cases,
        "stableCases": stable_cases,
        "stabilityRate": round(stable_cases / len(complete_cases), 6) if complete_cases else None,
        "totalTokens": total_tokens,
        "averageTokens": round(total_tokens / len(runs), 2) if runs else None,
        "averageDurationMs": round(total_duration / duration_count, 2) if duration_count else None,
    }


def save(report: dict[str, Any], output: Path) -> None:
    report["summary"] = summarize(report)
    report["updatedAt"] = datetime.now(UTC).isoformat()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    temporary.replace(output)


def revalidate_report(
    report: dict[str, Any],
    cases: list[dict[str, Any]],
    engine: Any,
) -> dict[str, Any]:
    cases_by_id = {case["id"]: case for case in cases}
    expected_by_id = {
        case["id"]: oracle_rows(engine, case["oracleSql"]) if case["kind"] == "data" else []
        for case in cases
    }
    for run in report["runs"]:
        case = cases_by_id[run["caseId"]]
        detail = {
            "status": run.get("status"),
            "sqlValidationStatus": run.get("sqlValidationStatus"),
            "error": {"code": run.get("errorCode")} if run.get("errorCode") else None,
            "result": {
                "rows": (run.get("comparison") or {}).get("actualRows") or [],
                "rowCount": (run.get("comparison") or {}).get("rowCount"),
            },
        }
        log = {
            "generatedSql": run.get("generatedSql"),
            "executedSql": run.get("executedSql"),
            "graphNodeTrace": run.get("graphNodeTrace") or [],
            "ragDocumentIds": run.get("ragDocumentIds") or [],
            "selectedObjects": run.get("selectedObjects") or [],
        }
        passed, reasons, comparison = evaluate_case(case, detail, log, expected_by_id[case["id"]])
        run["passed"] = passed
        run["failureReasons"] = reasons
        run["comparison"] = comparison
    report["suiteVersion"] = next(
        (case.get("suiteVersion") for case in cases if case.get("suiteVersion")), None
    ) or report.get("suiteVersion")
    report["revalidatedAt"] = datetime.now(UTC).isoformat()
    return report


def main() -> int:
    args = parse_args()
    if args.repetitions < 1:
        raise SystemExit("--repetitions must be at least 1")
    os.environ["DEFAULT_MODEL_CONFIG"] = "real"

    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.main import app

    suite = json.loads(args.cases.read_text(encoding="utf-8"))
    all_cases = suite["cases"]
    if len(all_cases) != 100 or len({case["id"] for case in all_cases}) != 100:
        raise SystemExit("Golden suite must contain exactly 100 unique cases")
    requested_ids = (
        {item.strip() for item in args.case_ids.split(",") if item.strip()}
        if args.case_ids
        else None
    )
    cases = [case for case in all_cases if requested_ids is None or case["id"] in requested_ids]
    if requested_ids is not None:
        missing = requested_ids - {case["id"] for case in cases}
        if missing:
            raise SystemExit(f"Unknown case IDs: {', '.join(sorted(missing))}")

    if args.resume and args.output.exists():
        report = json.loads(args.output.read_text(encoding="utf-8"))
        if (
            report.get("suiteVersion") != suite["version"]
            or report.get("repetitions") != args.repetitions
        ):
            raise SystemExit("Existing report does not match suite version/repetition count")
    else:
        report = {
            "kind": "real_model_golden_100",
            "createdAt": datetime.now(UTC).isoformat(),
            "suiteVersion": suite["version"],
            "dataVersion": suite["dataVersion"],
            "repetitions": args.repetitions,
            "cases": cases,
            "runs": [],
        }

    completed = {(run["caseId"], run["repetition"]) for run in report["runs"]}
    settings = get_settings()
    engine = create_engine(settings.query_database_url)
    if args.revalidate:
        report = json.loads(args.revalidate.read_text(encoding="utf-8"))
        report["suiteVersion"] = suite["version"]
        revalidate_report(report, cases, engine)
        save(report, args.output)
        engine.dispose()
        print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
        return 0 if report["summary"]["failedRuns"] == 0 else 1

    expected_by_id = {
        case["id"]: oracle_rows(engine, case["oracleSql"]) if case["kind"] == "data" else []
        for case in cases
    }

    with TestClient(app) as client:
        client.get("/health/ready").raise_for_status()
        configs = client.get("/api/v1/model-configs")
        configs.raise_for_status()
        active = next(
            (
                item
                for item in configs.json()
                if item.get("isActive") and item.get("enabled") and item.get("apiKeyMask")
            ),
            None,
        )
        if active is None:
            raise SystemExit("No enabled active real-model configuration with an API key")
        report["model"] = active["modelName"]
        report["protocol"] = active["protocol"]
        sources = client.get("/api/v1/data-sources")
        sources.raise_for_status()
        source_ids = [item["id"] for item in sources.json()["items"] if item["enabled"]]

        for repetition in range(1, args.repetitions + 1):
            for case in cases:
                key = (case["id"], repetition)
                if key in completed:
                    continue
                session_id: str | None = None
                started = datetime.now(UTC)
                try:
                    session_response = client.post(
                        "/api/v1/qa/sessions",
                        json={"title": f"golden-{case['id']}-run-{repetition}"},
                    )
                    session_response.raise_for_status()
                    session_id = str(session_response.json()["id"])
                    accepted = client.post(
                        f"/api/v1/qa/sessions/{session_id}/queries",
                        headers={"Idempotency-Key": f"golden-{uuid4()}"},
                        json={"question": case["question"], "dataSourceIds": source_ids},
                    )
                    accepted.raise_for_status()
                    execution_id = accepted.json()["executionId"]
                    detail_response = client.get(f"/api/v1/qa/executions/{execution_id}")
                    detail_response.raise_for_status()
                    detail = detail_response.json()
                    if detail.get("status") not in TERMINAL_STATUSES:
                        raise RuntimeError(
                            f"execution did not reach a terminal status: {detail.get('status')}"
                        )
                    log_response = client.get(f"/api/v1/qa/logs/{execution_id}")
                    log_response.raise_for_status()
                    log = log_response.json()
                    passed, reasons, comparison = evaluate_case(
                        case, detail, log, expected_by_id[case["id"]]
                    )
                    report["runs"].append(
                        {
                            "caseId": case["id"],
                            "repetition": repetition,
                            "kind": case["kind"],
                            "category": case["category"],
                            "question": case["question"],
                            "executionId": execution_id,
                            "status": detail.get("status"),
                            "passed": passed,
                            "failureReasons": reasons,
                            "durationMs": detail.get("durationMs"),
                            "modelName": detail.get("modelName"),
                            "sqlValidationStatus": detail.get("sqlValidationStatus"),
                            "generatedSql": log.get("generatedSql"),
                            "executedSql": log.get("executedSql"),
                            "errorCode": (detail.get("error") or {}).get("code"),
                            "errorMessage": log.get("errorMessage"),
                            "graphNodeTrace": log.get("graphNodeTrace") or [],
                            "ragDocumentIds": log.get("ragDocumentIds") or [],
                            "selectedObjects": log.get("selectedObjects") or [],
                            "tokenUsage": log.get("tokenUsage") or {},
                            "comparison": comparison,
                            "startedAt": started.isoformat(),
                            "finishedAt": datetime.now(UTC).isoformat(),
                        }
                    )
                except Exception as exc:
                    report["runs"].append(
                        {
                            "caseId": case["id"],
                            "repetition": repetition,
                            "kind": case["kind"],
                            "category": case["category"],
                            "question": case["question"],
                            "passed": False,
                            "failureReasons": [f"runner error: {type(exc).__name__}: {exc}"],
                            "startedAt": started.isoformat(),
                            "finishedAt": datetime.now(UTC).isoformat(),
                        }
                    )
                finally:
                    if session_id is not None:
                        with suppress(Exception):
                            client.delete(f"/api/v1/qa/sessions/{session_id}").raise_for_status()
                    save(report, args.output)
                    current = report["runs"][-1]
                    print(
                        json.dumps(
                            {
                                "caseId": current["caseId"],
                                "repetition": current["repetition"],
                                "passed": current["passed"],
                                "completedRuns": len(report["runs"]),
                                "totalRuns": len(cases) * args.repetitions,
                            },
                            ensure_ascii=False,
                        ),
                        flush=True,
                    )

    engine.dispose()
    save(report, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
    return 0 if report["summary"]["failedRuns"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
