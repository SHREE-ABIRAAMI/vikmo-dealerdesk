from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from .models import Dealer
from core.exceptions import ValidationError, DuplicateError


class DealerSerializer(serializers.ModelSerializer):
    credit_limit = serializers.SerializerMethodField()

    class Meta:
        model = Dealer
        fields = [
            "id",
            "dealer_code",
            "name",
            "city",
            "phone",
            "email",
            "gstin",
            "credit_limit",
        ]

    def get_credit_limit(self, obj) -> str:
        return f"{obj.credit_limit:.2f}"


class DealerCreateSerializer(serializers.ModelSerializer):
    credit_limit = serializers.CharField(required=False, default="0.00")

    class Meta:
        model = Dealer
        fields = [
            "dealer_code",
            "name",
            "city",
            "phone",
            "email",
            "gstin",
            "credit_limit",
        ]

    def validate_dealer_code(self, value):
        if not value or not str(value).strip():
            raise ValidationError("dealer_code cannot be empty.")
        val = str(value).strip()
        if Dealer.objects.filter(dealer_code=val).exists():
            raise DuplicateError(f"Dealer with dealer_code '{val}' already exists.")
        return val

    def validate_name(self, value):
        if not value or not str(value).strip():
            raise ValidationError("name cannot be empty.")
        return str(value).strip()

    def validate_credit_limit(self, value):
        try:
            d = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("credit_limit must be a valid decimal number.")
        if d < 0:
            raise ValidationError("credit_limit must be >= 0.")
        return d
