import pytest
from decimal import Decimal
from rest_framework.test import APIClient
from products.models import Product, Inventory
from dealers.models import Dealer


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def sample_product(db):
    p = Product.objects.create(
        sku="TEST-001",
        name="Test Brake Pad",
        category="Brakes",
        brand="Endurance",
        vehicle_fitment="Bajaj Pulsar 150",
        price=Decimal("1200.00"),
        description="High performance brake pads.",
    )
    Inventory.objects.create(product=p, quantity=25)
    return p


@pytest.mark.django_db
def test_product_list_and_pagination(client, sample_product):
    res = client.get("/api/products/")
    assert res.status_code == 200
    data = res.json()
    assert "count" in data
    assert "results" in data
    assert any(p["sku"] == "TEST-001" for p in data["results"])


@pytest.mark.django_db
def test_product_filtering(client, sample_product):
    res = client.get("/api/products/?search=Endurance")
    assert res.status_code == 200
    assert any(p["sku"] == "TEST-001" for p in res.json()["results"])

    res2 = client.get("/api/products/?category=Brakes")
    assert res2.status_code == 200
    assert any(p["sku"] == "TEST-001" for p in res2.json()["results"])

    res3 = client.get("/api/products/?vehicle=Pulsar")
    assert res3.status_code == 200
    assert any(p["sku"] == "TEST-001" for p in res3.json()["results"])


@pytest.mark.django_db
def test_product_detail_and_404(client, sample_product):
    res = client.get("/api/products/TEST-001/")
    assert res.status_code == 200
    assert res.json()["sku"] == "TEST-001"
    assert res.json()["stock"] == 25
    assert res.json()["price"] == "1200.00"

    res404 = client.get("/api/products/NONEXISTENT-999/")
    assert res404.status_code == 404
    assert res404.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.django_db
def test_product_create_and_duplicate(client):
    payload = {
        "sku": "NEW-001",
        "name": "New Mirror",
        "category": "Accessories",
        "brand": "Uno Minda",
        "vehicle_fitment": "Universal",
        "price": "450.50",
        "description": "Standard mirror",
    }
    res = client.post("/api/products/", payload, format="json")
    assert res.status_code == 201
    assert res.json()["sku"] == "NEW-001"
    assert res.json()["stock"] == 0

    # Duplicate SKU should return 409 DUPLICATE
    res_dup = client.post("/api/products/", payload, format="json")
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "DUPLICATE"


@pytest.mark.django_db
def test_inventory_update(client, sample_product):
    res = client.put(f"/api/inventory/{sample_product.sku}/", {"quantity": 80, "reason": "Restock"}, format="json")
    assert res.status_code == 200
    assert res.json()["quantity"] == 80

    # Stock in product detail reflects update
    res_p = client.get(f"/api/products/{sample_product.sku}/")
    assert res_p.json()["stock"] == 80

    # Negative quantity fails
    res_neg = client.put(f"/api/inventory/{sample_product.sku}/", {"quantity": -5}, format="json")
    assert res_neg.status_code == 400
    assert res_neg.json()["error"]["code"] == "VALIDATION_ERROR"
