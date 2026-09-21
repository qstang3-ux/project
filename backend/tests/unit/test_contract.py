from pathlib import Path

import yaml

from app.main import app


def resolve(spec: dict, node: dict | None) -> dict:
    if not node:
        return {}
    if "$ref" in node:
        name = node["$ref"].split("/")[-1]
        return resolve(spec, spec["components"]["schemas"][name])
    return node


def schema_shape(spec: dict, node: dict | None) -> object:
    value = resolve(spec, node)
    if "allOf" in value:
        merged: dict[str, object] = {}
        for part in value["allOf"]:
            shape = schema_shape(spec, part)
            if isinstance(shape, dict):
                merged.update(shape)
        return merged
    if value.get("type") == "array":
        return [schema_shape(spec, value.get("items"))]
    if "properties" in value:
        return {name: schema_shape(spec, child) for name, child in value["properties"].items()}
    if "anyOf" in value or "oneOf" in value:
        options = value.get("anyOf", value.get("oneOf", []))
        shaped = [schema_shape(spec, option) for option in options]
        return next((item for item in shaped if item not in ({}, None)), {})
    return {}


def json_schema(operation: dict, section: str, status: str | None = None) -> dict | None:
    if section == "requestBody":
        return (
            operation.get(section, {}).get("content", {}).get("application/json", {}).get("schema")
        )
    assert status is not None
    return (
        operation.get("responses", {})
        .get(status, {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )


def parameter_set(spec: dict, path_item: dict, operation: dict) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for parameter in path_item.get("parameters", []) + operation.get("parameters", []):
        if "$ref" in parameter:
            parameter = spec["components"]["parameters"][parameter["$ref"].split("/")[-1]]
        result.add((parameter["in"], parameter["name"]))
    return result


def test_openapi_paths_and_methods_match_contract() -> None:
    contract = yaml.safe_load(Path("docs/api/openapi.yaml").read_text(encoding="utf-8"))
    generated = app.openapi()
    generated_paths = {
        path.removeprefix("/api/v1"): value for path, value in generated["paths"].items()
    }
    http_methods = {"get", "post", "put", "patch", "delete"}
    assert set(generated_paths) == set(contract["paths"])
    for path, operations in contract["paths"].items():
        expected = set(operations) & http_methods
        actual = set(generated_paths[path]) & http_methods
        assert actual == expected, path
        for method in expected:
            contract_operation = operations[method]
            generated_operation = generated_paths[path][method]
            assert parameter_set(contract, operations, contract_operation) == parameter_set(
                generated, generated_paths[path], generated_operation
            ), f"{method.upper()} {path} parameters"

            contract_request = json_schema(contract_operation, "requestBody")
            generated_request = json_schema(generated_operation, "requestBody")
            assert schema_shape(contract, contract_request) == schema_shape(
                generated, generated_request
            ), f"{method.upper()} {path} request"

            contract_success = {
                status
                for status in contract_operation.get("responses", {})
                if status.startswith("2")
            }
            generated_success = {
                status
                for status in generated_operation.get("responses", {})
                if status.startswith("2")
            }
            assert contract_success <= generated_success, f"{method.upper()} {path} status"
            for status in contract_success:
                expected_schema = json_schema(contract_operation, "response", status)
                actual_schema = json_schema(generated_operation, "response", status)
                assert schema_shape(contract, expected_schema) == schema_shape(
                    generated, actual_schema
                ), f"{method.upper()} {path} response {status}"

    contract_schemas = contract["components"]["schemas"]
    generated_schemas = generated["components"]["schemas"]
    detail_required = {"sqlValidationStatus", "result", "chart", "error"}
    assert detail_required <= set(contract_schemas["ExecutionDetail"]["required"])
    assert detail_required <= set(generated_schemas["ExecutionDetail"]["required"])
    for field in ("result", "chart", "error"):
        assert contract_schemas["ExecutionDetail"]["properties"][field]["nullable"] is True
        assert {"type": "null"} in generated_schemas["ExecutionDetail"]["properties"][field][
            "anyOf"
        ]

    event_data = contract_schemas["ExecutionEventData"]
    assert event_data["discriminator"]["propertyName"] == "kind"
    assert len(event_data["oneOf"]) == 10
    assert set(event_data["discriminator"]["mapping"]) == {
        "execution.started",
        "clarification.required",
        "schema.selected",
        "sql.generated",
        "sql.validated",
        "query.completed",
        "answer.completed",
        "execution.completed",
        "execution.failed",
        "execution.cancelled",
    }

    assert contract_schemas["FeedbackCreate"]["properties"]["description"]["maxLength"] == 500
    assert (
        contract_schemas["ApplicationConfigUpdate"]["properties"]["recommendedQuestions"]["items"][
            "maxLength"
        ]
        == 100
    )
    assert contract_schemas["ModelConfigCreate"]["properties"]["name"]["maxLength"] == 50
    assert contract_schemas["ModelConfigCreate"]["properties"]["modelName"]["maxLength"] == 100
    assert "userId" in contract_schemas["FeedbackSummary"]["required"]
    assert "userId" in contract_schemas["QaLogSummary"]["required"]
