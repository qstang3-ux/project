import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": "management-star-backend",
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["requestId"] = request_id
        safe_fields = {
            "execution_id": "executionId",
            "provider": "provider",
            "model": "model",
            "protocol": "protocol",
            "purpose": "purpose",
            "durationMs": "durationMs",
            "promptTokens": "promptTokens",
            "completionTokens": "completionTokens",
            "totalTokens": "totalTokens",
            "retryCount": "retryCount",
            "status": "status",
            "errorCode": "errorCode",
            "app_env": "appEnv",
            "model_mode": "modelMode",
            "api_key_mask": "apiKeyMask",
        }
        for source, target in safe_fields.items():
            value = getattr(record, source, None)
            if value is not None:
                payload[target] = value
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
