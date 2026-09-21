from datetime import date
from typing import cast

from app.seed import DATA_AS_OF, rows_for_seed


def test_seed_is_deterministic_and_has_documented_scale() -> None:
    first = rows_for_seed()
    second = rows_for_seed()
    assert first == second
    assert len(first["business_units"]) == 21
    assert len(first["industries"]) == 8
    assert len(first["product_lines"]) == 3
    assert len(first["customers"]) == 60
    assert len(first["sales_targets"]) == 42
    assert len(first["contracts"]) == 600
    assert len(first["revenue_facts"]) == 1800
    assert len(first["payment_facts"]) == 1200
    assert len(first["project_pipeline"]) == 180
    recognized_dates = [cast(date, row["recognized_at"]) for row in first["revenue_facts"]]
    assert max(recognized_dates) == DATA_AS_OF
