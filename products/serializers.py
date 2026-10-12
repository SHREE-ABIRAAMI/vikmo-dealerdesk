from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from .models import Product, Inventory
from core.exceptions import ValidationError, DuplicateError


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "category",
            "brand",
            "vehicle_fitment",
            "price",
            "stock",
            "description",
        ]

    def get_price(self, obj) -> str:
        return f"{obj.price:.2f}"

    def get_stock(self, obj) -> int:
        if hasattr(obj, "inventory") and obj.inventory is not None:
            return obj.inventory.quantity
        return 0


class ProductCreateSerializer(serializers.ModelSerializer):
    price = serializers.CharField()

    class Meta:
        model = Product
        fields = [
            "sku",
            "name",
            "category",
            "brand",
            "vehicle_fitment",
            "price",
            "description",
        ]

    def validate_sku(self, value):
        if not value or not str(value).strip():
            raise ValidationError("SKU cannot be empty.")
        if Product.objects.filter(sku=value.strip()).exists():
            raise DuplicateError(f"Product with SKU '{value}' already exists.")
        return value.strip()

    def validate_price(self, value):
        try:
            d = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("Price must be a valid decimal number.")
        if d <= 0:
            raise ValidationError("Price must be greater than 0.")
        # Check decimal places
        if d.as_tuple().exponent < -2:
            raise ValidationError("Price can have at most 2 decimal places.")
        return d


class ProductUpdateSerializer(serializers.ModelSerializer):
    price = serializers.CharField(required=False)

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "brand",
            "vehicle_fitment",
            "price",
            "description",
        ]

    def validate_price(self, value):
        try:
            d = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("Price must be a valid decimal number.")
        if d <= 0:
            raise ValidationError("Price must be greater than 0.")
        if d.as_tuple().exponent < -2:
            raise ValidationError("Price can have at most 2 decimal places.")
        return d
