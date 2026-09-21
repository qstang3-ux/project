import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.models import IdempotencyRecord


@dataclass(frozen=True)
class IdempotencyClaim:
    record: IdempotencyRecord
    created: bool


def canonical_request_fingerprint(body: dict[str, Any]) -> str:
    encoded = json.dumps(
        _canonical_value(body),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def claim_idempotency(
    db: Session,
    *,
    idempotency_key: str,
    operation: str,
    resource_id: str,
    request_body: dict[str, Any],
) -> IdempotencyClaim:
    fingerprint = canonical_request_fingerprint(request_body)
    statement = (
        insert(IdempotencyRecord)
        .values(
            idempotency_key=idempotency_key,
            operation=operation,
            resource_id=resource_id,
            request_fingerprint=fingerprint,
        )
        .on_conflict_do_nothing(index_elements=[IdempotencyRecord.idempotency_key])
        .returning(IdempotencyRecord.idempotency_key)
    )
    created = db.scalar(statement) is not None
    record = db.get(IdempotencyRecord, idempotency_key)
    if record is None:
        raise RuntimeError("idempotency claim was not persisted")
    if (
        record.operation != operation
        or record.resource_id != resource_id
        or record.request_fingerprint != fingerprint
    ):
        raise ConflictError(
            "幂等键已绑定到不同请求",
            code="IDEMPOTENCY_KEY_CONFLICT",
        )
    return IdempotencyClaim(record, created)


def _canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
