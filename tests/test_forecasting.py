import csv
import math
import os
import pathlib
import pytest
from rest_framework.test import APIClient
from django.conf import settings
from products.models import Product, Inventory
from forecasting.services import ForecastingService


@pytest.fixture
def client():
    return APIClient()


def test_forecast_csv_file_integrity():
    csv_path = pathlib.Path(settings.BASE_DIR) / "ml" / "forecast.csv"
    assert csv_path.exists(), "ml/forecast.csv must exist"

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 160, f"Expected 160 rows, got {len(reader)}"
    assert list(reader[0].keys()) == ["sku", "week_start", "forecast_units"]

    expected_weeks = {"2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19"}
    weeks_found = {r["week_start"] for r in reader}
    assert weeks_found == expected_weeks

    skus = {r["sku"] for r in reader}
    assert len(skus) == 40, f"Expected 40 unique SKUs, got {len(skus)}"

    for row in reader:
        val = float(row["forecast_units"])
        assert val >= 0.0, f"Forecast units must be non-negative: {val}"


@pytest.mark.django_db
def test_forecast_api_endpoints(client):
    res_sugg = client.get("/api/reorder-suggestions/")
    assert res_sugg.status_code == 200
    results = res_sugg.json().get("results")
    assert isinstance(results, list)
    assert len(results) == 40

    item = results[0]
    required_keys = [
        "sku",
        "current_stock",
        "lead_time_weeks",
        "lead_time_demand",
        "safety_stock",
        "reorder_point",
        "reorder_qty",
    ]
    for k in required_keys:
        assert k in item

    # Test individual SKU forecast endpoint
    test_sku = item["sku"]
    res_sku = client.get(f"/api/forecast/{test_sku}/")
    assert res_sku.status_code == 200
    data = res_sku.json()
    assert data["sku"] == test_sku
    assert len(data["forecast"]) == 4

    # 404 for unknown sku
    res_404 = client.get("/api/forecast/UNKNOWN-SKU/")
    assert res_404.status_code == 404


@pytest.mark.django_db
def test_reorder_math_safety_stock_formula():
    results = ForecastingService.get_reorder_suggestions()
    for r in results:
        L = r["lead_time_weeks"]
        assert 1 <= L <= 4
        # safety_stock is non-negative integer
        assert isinstance(r["safety_stock"], int)
        assert r["safety_stock"] >= 0
        # reorder_point = lead_time_demand + safety_stock
        assert math.isclose(r["reorder_point"], r["lead_time_demand"] + r["safety_stock"], abs_tol=0.1)
        # reorder_qty = max(0, ceil(reorder_point - current_stock))
        expected_qty = max(0, math.ceil(r["reorder_point"] - r["current_stock"]))
        assert r["reorder_qty"] == expected_qty
