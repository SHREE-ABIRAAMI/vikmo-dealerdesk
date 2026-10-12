from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Product, Inventory
from .serializers import (
    ProductSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
)
from core.pagination import StandardResultsSetPagination
from core.exceptions import NotFoundError, ValidationError, DuplicateError


class ProductListCreateView(APIView):
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Product.objects.select_related("inventory").all()

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(sku__icontains=search)
                | Q(name__icontains=search)
                | Q(brand__icontains=search)
            )

        category = request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__iexact=category)

        vehicle = request.query_params.get("vehicle")
        if vehicle:
            queryset = queryset.filter(vehicle_fitment__icontains=vehicle)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ProductSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            # If sku uniqueness failed, raise DuplicateError
            if "sku" in errors:
                for err in errors["sku"]:
                    if "already exists" in str(err).lower():
                        raise DuplicateError(str(err))
            raise ValidationError(message="Validation failed.", details=errors)

        product = serializer.save()
        Inventory.objects.get_or_create(product=product, defaults={"quantity": 0})
        out_serializer = ProductSerializer(product)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class ProductDetailView(APIView):
    def get_object(self, sku):
        try:
            return Product.objects.select_related("inventory").get(sku=sku)
        except Product.DoesNotExist:
            raise NotFoundError(f"Product with SKU '{sku}' not found.")

    def get(self, request, sku):
        product = self.get_object(sku)
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, sku):
        product = self.get_object(sku)
        serializer = ProductUpdateSerializer(product, data=request.data, partial=True)
        if not serializer.is_valid():
            raise ValidationError(message="Validation failed.", details=serializer.errors)

        updated_product = serializer.save()
        out_serializer = ProductSerializer(updated_product)
        return Response(out_serializer.data, status=status.HTTP_200_OK)


class InventoryUpdateView(APIView):
    def put(self, request, sku):
        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            raise NotFoundError(f"Product with SKU '{sku}' not found.")

        if "quantity" not in request.data:
            raise ValidationError("Field 'quantity' is required.")

        raw_qty = request.data.get("quantity")
        if not isinstance(raw_qty, int) or isinstance(raw_qty, bool):
            raise ValidationError("Quantity must be an integer.")

        if raw_qty < 0:
            raise ValidationError("Quantity must be an integer >= 0.")

        inventory, _ = Inventory.objects.get_or_create(
            product=product,
            defaults={"quantity": raw_qty}
        )
        inventory.quantity = raw_qty
        inventory.save(update_fields=["quantity", "updated_at"])

        return Response(
            {"sku": sku, "quantity": raw_qty},
            status=status.HTTP_200_OK
        )
