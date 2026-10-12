from decimal import Decimal
from django.db import models
from dealers.models import Dealer
from products.models import Product


class Order(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "DRAFT"),
        ("CONFIRMED", "CONFIRMED"),
        ("DISPATCHED", "DISPATCHED"),
        ("DELIVERED", "DELIVERED"),
        ("CANCELLED", "CANCELLED"),
    ]

    order_number = models.CharField(max_length=32, unique=True, primary_key=True)
    dealer = models.ForeignKey(Dealer, on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT", db_index=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    tax_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["dealer", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.status}) - Dealer {self.dealer_id}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")
    sku = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_subtotal = models.DecimalField(max_digits=14, decimal_places=2)
    line_tax = models.DecimalField(max_digits=14, decimal_places=2)
    line_total = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.order_id} - {self.sku} x {self.quantity}"


class DailyOrderSequence(models.Model):
    """Guarantees atomic, gapless, concurrent-safe daily order sequences."""
    date_str = models.CharField(max_length=8, unique=True, primary_key=True)  # YYYYMMDD in Asia/Kolkata
    last_seq = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.date_str}: {self.last_seq}"


class IdempotencyRecord(models.Model):
    key = models.CharField(max_length=255, unique=True, primary_key=True)
    request_hash = models.CharField(max_length=64)
    order_number = models.CharField(max_length=32)
    response_body = models.JSONField()
    status_code = models.IntegerField(default=201)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IdempotencyKey({self.key}) -> {self.order_number}"
