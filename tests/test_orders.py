import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from products.models import Product, Inventory
from dealers.models import Dealer
from orders.models import Order


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def test_setup(db):
    dealer = Dealer.objects.create(dealer_code="DLR-TEST-1", name="Test Dealer")
    p1 = Product.objects.create(
        sku="TEST-SKU-1",
        name="Test Chain Kit",
        category="Drivetrain",
        brand="Rolon",
        vehicle_fitment="Pulsar 150",
        price=Decimal("1459.50"),
    )
    Inventory.objects.create(product=p1, quantity=10)

    p2 = Product.objects.create(
        sku="TEST-SKU-2",
        name="Test Oil Filter",
        category="Filters",
        brand="Elofic",
        vehicle_fitment="Pulsar 150",
        price=Decimal("123.45"),
    )
    Inventory.objects.create(product=p2, quantity=5)

    return {"dealer": dealer, "p1": p1, "p2": p2}


@pytest.mark.django_db
def test_order_draft_creation_and_gst_rounding(client, test_setup):
    dealer = test_setup["dealer"]
    # Line 1: 1459.50 * 3 = 4378.50. Tax: 4378.50 * 0.18 = 788.13. Total: 5166.63
    # Line 2: 123.45 * 1 = 123.45. Tax: 123.45 * 0.18 = 22.221 -> 22.22. Total: 145.67
    # Subtotal: 4501.95, Tax: 810.35, Grand: 5312.30
    payload = {
        "dealer_id": dealer.id,
        "items": [
            {"sku": "TEST-SKU-1", "quantity": 3},
            {"sku": "TEST-SKU-2", "quantity": 1},
        ],
    }
    res = client.post("/api/orders/", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "DRAFT"
    assert data["subtotal"] == "4501.95"
    assert data["tax_total"] == "810.35"
    assert data["grand_total"] == "5312.30"
    assert data["order_number"].startswith("ORD-")

    # DRAFT does not touch inventory
    p1_stock = Product.objects.get(sku="TEST-SKU-1").inventory.quantity
    assert p1_stock == 10


@pytest.mark.django_db
def test_order_validation_errors(client, test_setup):
    dealer = test_setup["dealer"]

    # Empty items
    res1 = client.post("/api/orders/", {"dealer_id": dealer.id, "items": []}, format="json")
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "VALIDATION_ERROR"

    # Nonexistent SKU
    res2 = client.post("/api/orders/", {"dealer_id": dealer.id, "items": [{"sku": "NONEXISTENT", "quantity": 1}]}, format="json")
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "VALIDATION_ERROR"

    # Duplicate SKU in single order
    res3 = client.post(
        "/api/orders/",
        {"dealer_id": dealer.id, "items": [{"sku": "TEST-SKU-1", "quantity": 1}, {"sku": "TEST-SKU-1", "quantity": 2}]},
        format="json",
    )
    assert res3.status_code == 400
    assert res3.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_order_confirmation_and_stock_deduction(client, test_setup):
    dealer = test_setup["dealer"]
    res = client.post(
        "/api/orders/",
        {"dealer_id": dealer.id, "items": [{"sku": "TEST-SKU-1", "quantity": 4}]},
        format="json",
    )
    order_num = res.json()["order_number"]

    # Confirm order
    res_conf = client.post(f"/api/orders/{order_num}/confirm/")
    assert res_conf.status_code == 200
    assert res_conf.json()["status"] == "CONFIRMED"

    # Stock deducted: 10 - 4 = 6
    assert Product.objects.get(sku="TEST-SKU-1").inventory.quantity == 6


@pytest.mark.django_db
def test_insufficient_stock_error(client, test_setup):
    dealer = test_setup["dealer"]
    res = client.post(
        "/api/orders/",
        {"dealer_id": dealer.id, "items": [{"sku": "TEST-SKU-1", "quantity": 15}]},
        format="json",
    )
    order_num = res.json()["order_number"]

    # Confirm should fail with INSUFFICIENT_STOCK
    res_conf = client.post(f"/api/orders/{order_num}/confirm/")
    assert res_conf.status_code == 409
    err = res_conf.json()["error"]
    assert err["code"] == "INSUFFICIENT_STOCK"
    assert len(err["details"]) == 1
    assert err["details"][0]["sku"] == "TEST-SKU-1"
    assert err["details"][0]["available"] == 10
    assert err["details"][0]["requested"] == 15

    # Stock unchanged
    assert Product.objects.get(sku="TEST-SKU-1").inventory.quantity == 10


@pytest.mark.django_db
def test_cancel_restores_stock_once(client, test_setup):
    dealer = test_setup["dealer"]
    res = client.post(
        "/api/orders/",
        {"dealer_id": dealer.id, "items": [{"sku": "TEST-SKU-1", "quantity": 3}]},
        format="json",
    )
    order_num = res.json()["order_number"]
    client.post(f"/api/orders/{order_num}/confirm/")
    assert Product.objects.get(sku="TEST-SKU-1").inventory.quantity == 7

    # Cancel restored stock
    res_cancel = client.post(f"/api/orders/{order_num}/cancel/")
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"
    assert Product.objects.get(sku="TEST-SKU-1").inventory.quantity == 10

    # Second cancel should fail with INVALID_TRANSITION
    res_cancel2 = client.post(f"/api/orders/{order_num}/cancel/")
    assert res_cancel2.status_code == 409
    assert res_cancel2.json()["error"]["code"] == "INVALID_TRANSITION"
    # Stock remains 10 (restored exactly once)
    assert Product.objects.get(sku="TEST-SKU-1").inventory.quantity == 10


@pytest.mark.django_db
def test_idempotency_key(client, test_setup):
    dealer = test_setup["dealer"]
    payload = {"dealer_id": dealer.id, "items": [{"sku": "TEST-SKU-1", "quantity": 1}]}

    res1 = client.post("/api/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="IDEM-TEST-1")
    assert res1.status_code == 201
    ord1 = res1.json()["order_number"]

    # Same key same body -> returns original order
    res2 = client.post("/api/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="IDEM-TEST-1")
    assert res2.status_code == 201
    assert res2.json()["order_number"] == ord1

    # Same key different body -> 409 IDEMPOTENCY_CONFLICT
    diff_payload = {"dealer_id": dealer.id, "items": [{"sku": "TEST-SKU-2", "quantity": 1}]}
    res3 = client.post("/api/orders/", diff_payload, format="json", HTTP_IDEMPOTENCY_KEY="IDEM-TEST-1")
    assert res3.status_code == 409
    assert res3.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
