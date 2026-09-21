from pathlib import Path

from scripts.evaluate_prompt_security import evaluate


def test_prompt_injection_evaluation_contains_all_attacks_without_regression() -> None:
    report = evaluate(
        Path("tests/evaluation/prompt-injection-cases.json"),
        Path("tests/evaluation/text2sql-cases.json"),
    )

    assert report["modelCalls"] == 0
    assert report["attackCaseCount"] == 16
    assert report["attackCasesPassed"] == 16
    assert report["dangerousPayloadContainmentRate"] == 1.0
    assert report["regressionCaseCount"] == 30
    assert report["regressionCasesPassed"] == 30
    assert report["regressionPassRate"] == 1.0
