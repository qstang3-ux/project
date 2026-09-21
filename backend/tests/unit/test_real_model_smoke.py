from scripts.smoke_real_model import (
    CORE_NODE_TRACE,
    core_case_passes,
    core_result_matches,
    dangerous_case_passes,
    execution_report,
    revalidate_report,
    should_retry,
)


def model_call(purpose: str) -> dict[str, object]:
    return {
        "provider": "openai_compatible",
        "model": "gpt-5.6-sol",
        "purpose": purpose,
        "totalTokens": 10,
        "status": "success",
    }


def test_execution_report_contains_agent_audit_evidence() -> None:
    detail = {
        "id": "execution-id",
        "status": "completed",
        "modelName": "gpt-5.6-sol",
        "durationMs": 123,
        "sqlValidationStatus": "passed",
        "sql": "SELECT 1",
        "result": {"rowCount": 1},
        "chart": {"type": "none"},
        "followUpQuestions": [],
        "error": None,
    }
    log = {
        "graphVersion": "langgraph-v1",
        "graphNodeTrace": CORE_NODE_TRACE,
        "checkpointStatus": "completed",
        "ragDocumentIds": ["doc-id"],
        "ragDegraded": False,
        "resultCheckPassed": True,
        "selectedObjects": ["mart.v_sales_performance"],
        "generatedSql": "SELECT 1",
        "executedSql": "SELECT 1 LIMIT 500",
        "errorMessage": None,
        "tokenUsage": {"promptTokens": 7, "completionTokens": 3, "totalTokens": 10},
        "modelCalls": [model_call("sql_generation"), model_call("answer_generation")],
    }

    report = execution_report(detail, log)

    assert report["graphNodeTrace"] == CORE_NODE_TRACE
    assert report["checkpointStatus"] == "completed"
    assert report["ragDocumentIds"] == ["doc-id"]
    assert report["tokenUsage"]["totalTokens"] == 10
    assert report["generatedSql"] == "SELECT 1"
    assert report["executedSql"] == "SELECT 1 LIMIT 500"


def test_core_case_requires_real_sql_and_answer_calls() -> None:
    item = {
        "status": "completed",
        "rowCount": 5,
        "sqlValidationStatus": "passed",
        "graphNodeTrace": CORE_NODE_TRACE,
        "checkpointStatus": "completed",
        "ragDocumentIds": ["doc-id"],
        "ragDegraded": False,
        "resultCheckPassed": True,
        "tokenUsage": {"totalTokens": 20},
        "modelCalls": [model_call("sql_generation"), model_call("answer_generation")],
        "modelName": "gpt-5.6-sol",
    }

    assert core_case_passes(item, 5, "eq")
    item["modelCalls"] = [model_call("sql_generation")]
    assert not core_case_passes(item, 5, "eq")


def test_core_result_check_rejects_zero_high_risk_count() -> None:
    assert not core_result_matches(
        7,
        {
            "rows": [{"high_risk_project_count": 0}],
            "rowCount": 1,
        },
    )
    assert core_result_matches(
        7,
        {
            "rows": [{"high_risk_project_count": 15}],
            "rowCount": 1,
        },
    )


def test_core_result_check_uses_business_unit_name_not_code() -> None:
    rows = [
        {"business_unit_code": code, "business_unit_name": name}
        for code, name in zip(
            ("BU01", "BU02", "BU03", "BU04", "BU05"),
            ("北京代表处", "上海代表处", "浙江代表处", "江苏代表处", "山东代表处"),
            strict=True,
        )
    ]

    assert core_result_matches(1, {"rows": rows, "rowCount": 5})


def test_dangerous_case_does_not_accept_provider_failure() -> None:
    item = {
        "status": "failed",
        "errorCode": "MODEL_UNAVAILABLE",
        "graphNodeTrace": ["load_context", "retrieve_knowledge", "generate_sql"],
        "ragDocumentIds": ["doc-id"],
        "ragDegraded": False,
        "modelCalls": [
            {
                **model_call("sql_generation"),
                "status": "failed",
                "totalTokens": 0,
            }
        ],
        "modelName": "gpt-5.6-sol",
        "steps": [],
    }

    assert not dangerous_case_passes(item)


def test_dangerous_case_accepts_safe_rejection_after_real_model_call() -> None:
    item = {
        "status": "rejected",
        "errorCode": "SQL_VALIDATION_FAILED",
        "graphNodeTrace": [
            "load_context",
            "build_memory",
            "retrieve_knowledge",
            "generate_sql",
            "validate_sql",
        ],
        "ragDocumentIds": ["doc-id"],
        "ragDegraded": False,
        "modelCalls": [model_call("sql_generation")],
        "modelName": "gpt-5.6-sol",
        "steps": [
            {"type": "schema_selection"},
            {"type": "sql_generation"},
        ],
    }

    assert dangerous_case_passes(item)


def test_dangerous_case_accepts_deterministic_unsafe_intent_rejection() -> None:
    item = {
        "status": "rejected",
        "errorCode": "UNSAFE_REQUEST",
        "graphNodeTrace": [
            "load_context",
            "build_memory",
            "classify_intent",
            "persist_non_data_response",
        ],
        "ragDocumentIds": [],
        "ragDegraded": False,
        "modelCalls": [
            {
                **model_call("intent_classification"),
                "model": "deepseek-flash",
            }
        ],
        "modelName": "deepseek-flash",
        "steps": [{"type": "intent_classification"}],
    }

    assert dangerous_case_passes(item)


def test_only_transient_provider_errors_are_retried_once() -> None:
    assert should_retry({"passed": False, "errorCode": "MODEL_UNAVAILABLE"}, 1)
    assert not should_retry({"passed": False, "errorCode": "MODEL_UNAVAILABLE"}, 2)
    assert not should_retry({"passed": False, "errorCode": "SQL_VALIDATION_FAILED"}, 1)
    assert not should_retry({"passed": True, "errorCode": None}, 1)


def test_revalidate_report_updates_stale_graph_expectations() -> None:
    core = {
        "status": "completed",
        "rowCount": 5,
        "sqlValidationStatus": "passed",
        "graphNodeTrace": CORE_NODE_TRACE,
        "checkpointStatus": "completed",
        "ragDocumentIds": ["doc-id"],
        "ragDegraded": False,
        "resultCheckPassed": True,
        "tokenUsage": {"totalTokens": 20},
        "modelCalls": [model_call("sql_generation"), model_call("answer_generation")],
        "modelName": "gpt-5.6-sol",
    }
    report = {
        "model": "gpt-5.6-sol",
        "coreCases": [core],
        "dangerousCases": [],
        "passed": False,
        "failures": ["core-1"],
    }

    revalidated = revalidate_report(report)

    assert revalidated["passed"] is True
    assert revalidated["failures"] == []
