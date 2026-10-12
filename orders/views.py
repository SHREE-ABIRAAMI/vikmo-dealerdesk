import hashlib
import json
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Order, IdempotencyRecord
from .serializers import OrderSerializer
from .services import (
    create_draft_order,
    replace_order_items,
    confirm_order,
    dispatch_order,
    deliver_order,
    cancel_order,
)
from core.pagination import StandardResultsSetPagination
from core.exceptions import NotFoundError, ValidationError, IdempotencyConflictError


class OrderListCreateView(APIView):
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Order.objects.prefetch_related("items").select_related("dealer").all()

        dealer_id = request.query_params.get("dealer_id")
        if dealer_id:
            try:
                queryset = queryset.filter(dealer_id=int(dealer_id))
            except ValueError:
                pass

        status_param = request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param.upper())

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = OrderSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        idempotency_key = request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY")
        body_hash = None

        if idempotency_key:
            idempotency_key = idempotency_key.strip()
            body_str = json.dumps(request.data, sort_keys=True)
            body_hash = hashlib.sha256(body_str.encode("utf-8")).hexdigest()

            with transaction.atomic():
                existing = IdempotencyRecord.objects.select_for_update().filter(key=idempotency_key).first()
                if existing:
                    if existing.request_hash == body_hash:
                        return Response(existing.response_body, status=existing.status_code)
                    else:
                        raise IdempotencyConflictError(
                            "Idempotency-Key has already been used with a different request payload."
                        )

        data = request.data
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object.")

        dealer_id = data.get("dealer_id")
        if dealer_id is None:
            raise ValidationError("Field 'dealer_id' is required.")

        items = data.get("items")
        if items is None:
            raise ValidationError("Field 'items' is required.")

        order = create_draft_order(dealer_id=dealer_id, items_data=items)
        serializer = OrderSerializer(order)
        res_data = serializer.data

        if idempotency_key and body_hash:
            IdempotencyRecord.objects.get_or_create(
                key=idempotency_key,
                defaults={
                    "request_hash": body_hash,
                    "order_number": order.order_number,
                    "response_body": res_data,
                    "status_code": 201,
                }
            )

        return Response(res_data, status=status.HTTP_201_CREATED)


class OrderDetailView(APIView):
    def get_order(self, order_number):
        try:
            return Order.objects.prefetch_related("items").select_related("dealer").get(order_number=order_number)
        except Order.DoesNotExist:
            raise NotFoundError(f"Order '{order_number}' not found.")

    def get(self, request, order_number):
        order = self.get_order(order_number)
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, order_number):
        order = self.get_order(order_number)
        items = request.data.get("items")
        if items is None:
            raise ValidationError("Field 'items' is required.")

        updated_order = replace_order_items(order, items)
        serializer = OrderSerializer(updated_order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderConfirmView(APIView):
    def post(self, request, order_number):
        try:
            order = Order.objects.prefetch_related("items").select_related("dealer").get(order_number=order_number)
        except Order.DoesNotExist:
            raise NotFoundError(f"Order '{order_number}' not found.")

        confirmed_order = confirm_order(order)
        serializer = OrderSerializer(confirmed_order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderDispatchView(APIView):
    def post(self, request, order_number):
        try:
            order = Order.objects.prefetch_related("items").select_related("dealer").get(order_number=order_number)
        except Order.DoesNotExist:
            raise NotFoundError(f"Order '{order_number}' not found.")

        dispatched_order = dispatch_order(order)
        serializer = OrderSerializer(dispatched_order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderDeliverView(APIView):
    def post(self, request, order_number):
        try:
            order = Order.objects.prefetch_related("items").select_related("dealer").get(order_number=order_number)
        except Order.DoesNotExist:
            raise NotFoundError(f"Order '{order_number}' not found.")

        delivered_order = deliver_order(order)
        serializer = OrderSerializer(delivered_order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class OrderCancelView(APIView):
    def post(self, request, order_number):
        try:
            order = Order.objects.prefetch_related("items").select_related("dealer").get(order_number=order_number)
        except Order.DoesNotExist:
            raise NotFoundError(f"Order '{order_number}' not found.")

        cancelled_order = cancel_order(order)
        serializer = OrderSerializer(cancelled_order)
        return Response(serializer.data, status=status.HTTP_200_OK)
