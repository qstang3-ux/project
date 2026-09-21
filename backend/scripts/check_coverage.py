import argparse
import json
from pathlib import Path
from typing import Any

OVERALL_MINIMUM = 80.0
SERVICES_MINIMUM = 85.0
VALIDATOR_MINIMUM = 100.0


def _percentage(covered: int, total: int) -> float:
    return 100.0 if total == 0 else covered * 100 / total


def _summary_coverage(summary: dict[str, Any]) -> tuple[int, int]:
    covered = int(summary["covered_lines"]) + int(summary["covered_branches"])
    total = int(summary["num_statements"]) + int(summary["num_branches"])
    return covered, total


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce layered backend coverage thresholds.")
    parser.add_argument(
        "report",
        nargs="?",
        type=Path,
        default=Path(".runtime/coverage.json"),
        help="coverage.py JSON report generated with branch coverage",
    )
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    files: dict[str, dict[str, Any]] = report["files"]

    total_summary: dict[str, Any] = report["totals"]
    overall_covered, overall_total = _summary_coverage(total_summary)

    service_summaries = [
        data["summary"]
        for path, data in files.items()
        if path.replace("\\", "/").startswith("app/services/")
    ]
    if not service_summaries:
        raise RuntimeError("coverage report contains no app/services modules")
    services_covered = sum(_summary_coverage(item)[0] for item in service_summaries)
    services_total = sum(_summary_coverage(item)[1] for item in service_summaries)

    validator = next(
        (
            data["summary"]
            for path, data in files.items()
            if path.replace("\\", "/") == "app/text2sql/validator.py"
        ),
        None,
    )
    if validator is None:
        raise RuntimeError("coverage report contains no SQL validator module")
    validator_covered, validator_total = _summary_coverage(validator)

    results = (
        ("overall", _percentage(overall_covered, overall_total), OVERALL_MINIMUM),
        ("services", _percentage(services_covered, services_total), SERVICES_MINIMUM),
        ("validator", _percentage(validator_covered, validator_total), VALIDATOR_MINIMUM),
    )
    failed = False
    for name, actual, minimum in results:
        status = "PASS" if actual >= minimum else "FAIL"
        print(f"{status} {name}: {actual:.2f}% (required {minimum:.2f}%)")
        failed |= actual < minimum
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
