import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from rest_framework.test import APIClient
from products.models import Product, Inventory
from supplier.services import sync_supplier_catalogue, is_valid_price, parse_iso_timestamp
from core.exceptions import SupplierUnavailableError


@pytest.fixture
def client():
    return APIClient()


def test_is_valid_price():
    valid, price = is_valid_price("1499.00")
    assert valid is True
    assert price == Decimal("1499.00")

    valid, _ = is_valid_price("0.00")
    assert valid is False

    valid, _ = is_valid_price("-10.00")
    assert valid is False

    valid, _ = is_valid_price("12.345")  # >2 decimal places
    assert valid is False

    valid, _ = is_valid_price("invalid")
    assert valid is False


@pytest.mark.django_db
def test_supplier_sync_does_not_mutate_stock():
    # Create product with existing stock 50
    prod = Product.objects.create(
        sku="TEST-SYNC-1",
        name="Old Name",
        category="Brakes",
        brand="Endurance",
        vehicle_fitment="Pulsar",
        price=Decimal("100.00"),
    )
    inv = Inventory.objects.create(product=prod, quantity=50)

    # Mock supplier API response
    feed_page = {
        "items": [
            {
                "supplier_sku": "SUP-101",
                "sku": "TEST-SYNC-1",
                "name": "Updated Name",
                "category": "Brakes",
                "brand": "Endurance",
                "vehicle_fitment": "Pulsar",
                "description": "Updated description",
                "price": "120.00",
                "supplier_stock": 999,  # Must NOT overwrite our stock!
                "updated_at": "2026-10-10T12:00:00Z",
            }
        ],
        "next_cursor": None,
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = feed_page

    with patch("requests.Session.get", return_value=mock_resp):
        res = sync_supplier_catalogue()

    assert res["updated"] == 1
    prod.refresh_from_db()
    assert prod.name == "Updated Name"
    assert prod.price == Decimal("120.00")

    # Our local stock must STILL be 50!
    inv.refresh_from_db()
    assert inv.quantity == 50


@pytest.mark.django_db
def test_supplier_sync_outage_raises_502():
    mock_resp = MagicMock()
    mock_resp.status_code = 503

    with patch("requests.Session.get", return_value=mock_resp):
        with pytest.raises(SupplierUnavailableError):
            sync_supplier_catalogue()
