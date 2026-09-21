from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    with TestClient(app) as client:
        sources_response = client.get("/api/v1/data-sources")
        sources_response.raise_for_status()
        source_id = sources_response.json()["items"][0]["id"]

        session_response = client.post("/api/v1/qa/sessions", json={"title": "HTTP smoke"})
        session_response.raise_for_status()
        session_id = session_response.json()["id"]

        query_response = client.post(
            f"/api/v1/qa/sessions/{session_id}/queries",
            headers={"Idempotency-Key": f"smoke-{uuid4().hex}"},
            json={
                "question": "2026年商业目标最高的5个经营单元",
                "dataSourceIds": [source_id],
                "generateChart": True,
            },
        )
        query_response.raise_for_status()
        execution_id = query_response.json()["executionId"]

        detail_response = client.get(f"/api/v1/qa/executions/{execution_id}")
        detail_response.raise_for_status()
        detail = detail_response.json()
        assert detail["status"] == "completed", detail
        assert detail["result"]["rowCount"] == 5
        assert [row["经营单元"] for row in detail["result"]["rows"]] == [
            "北京代表处",
            "上海代表处",
            "浙江代表处",
            "江苏代表处",
            "山东代表处",
        ]
        client.delete(f"/api/v1/qa/sessions/{session_id}").raise_for_status()
        print(
            {
                "executionId": execution_id,
                "status": detail["status"],
                "rowCount": detail["result"]["rowCount"],
                "durationMs": detail["durationMs"],
            }
        )


if __name__ == "__main__":
    main()
