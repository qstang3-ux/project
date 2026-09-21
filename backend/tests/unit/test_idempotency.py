from uuid import UUID

from app.services.idempotency import canonical_request_fingerprint


def test_canonical_request_fingerprint_is_key_order_independent() -> None:
    resource_id = UUID("00000000-0000-0000-0000-000000000001")
    first = canonical_request_fingerprint(
        {"question": "收入", "resourceId": resource_id, "generateChart": True}
    )
    second = canonical_request_fingerprint(
        {"generateChart": True, "resourceId": str(resource_id), "question": "收入"}
    )
    assert first == second
    assert len(first) == 64


def test_canonical_request_fingerprint_preserves_array_order() -> None:
    first = canonical_request_fingerprint({"contextMessageIds": ["a", "b"]})
    second = canonical_request_fingerprint({"contextMessageIds": ["b", "a"]})
    assert first != second
