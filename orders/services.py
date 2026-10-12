import hashlib
import json
import zoneinfo
from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction
from django.utils import timezone

from .models import Order, OrderItem, DailyOrderSequence, IdempotencyRecord
from dealers.models import Dealer
from products.models import Product, Inventory
from core.exceptions import (
    ValidationError,
    NotFoundError,
    InsufficientStockError,
    InvalidTransitionError,
    OrderLockedError,
    IdempotencyConflictError,
)

PAISA = Decimal("0.01")
TAX_RATE = Decimal("0.18")
KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")


def generate_order_number() -> str:
    """Generates unique ORD-YYYYMMDD-NNNN using atomic row-locking on DailyOrderSequence."""
    now_ist = timezone.now().astimezone(KOLKATA_TZ)
    date_str = now_ist.strftime("%Y%m%d")

    with transaction.atomic():
        seq_obj, _ = DailyOrderSequence.objects.select_for_update().get_or_create(
            date_str=date_str,
            defaults={"last_seq": 0}
        )
        seq_obj.last_seq += 1
        seq_obj.save(update_fields=["last_seq"])
        seq_num = seq_obj.last_seq

    return f"ORD-{date_str}-{seq_num:04d}"


def calculate_line_item(unit_price: Decimal, quantity: int):
    line_subtotal = (unit_price * quantity).quantize(PAISA, rounding=ROUND_HALF_UP)
    line_tax = (line_subtotal * TAX_RATE).quantize(PAISA, rounding=ROUND_HALF_UP)
    line_total = (line_subtotal + line_tax).quantize(PAISA, rounding=ROUND_HALF_UP)
    return line_subtotal, line_tax, line_total


def validate_and_prepare_items(items_data: list):
    if not items_data or not isinstance(items_data, list) or len(items_data) == 0:
        raise ValidationError("Order must contain at least one item.")

    seen_skus = set()
    prepared_items = []

    for idx, item in enumerate(items_data):
        if not isinstance(item, dict):
            raise ValidationError(f"Item at index {idx} must be an object.")

        sku = item.get("sku")
        if not sku or not isinstance(sku, str):
            raise ValidationError(f"Item at index {idx} has missing or invalid 'sku'.")
        sku = sku.strip()

        if sku in seen_skus:
            raise ValidationError(f"Duplicate SKU '{sku}' in order items.")
        seen_skus.add(sku)

        quantity = item.get("quantity")
        if quantity is None or not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
            raise ValidationError(f"Quantity for SKU '{sku}' must be an integer >= 1.")

        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            raise ValidationError(f"SKU '{sku}' does not exist in catalogue.")

        prepared_items.append({
            "product": product,
            "sku": product.sku,
            "name": product.name,
            "quantity": quantity,
            "unit_price": product.price,
        })

    return prepared_items


def compute_order_totals(prepared_items: list):
    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")

    enriched_items = []
    for item in prepared_items:
        line_sub, line_tx, line_tot = calculate_line_item(item["unit_price"], item["quantity"])
        subtotal += line_sub
        tax_total += line_tx
        enriched_items.append({
            **item,
            "line_subtotal": line_sub,
            "line_tax": line_tx,
            "line_total": line_tot,
        })

    subtotal = subtotal.quantize(PAISA, rounding=ROUND_HALF_UP)
    tax_total = tax_total.quantize(PAISA, rounding=ROUND_HALF_UP)
    grand_total = (subtotal + tax_total).quantize(PAISA, rounding=ROUND_HALF_UP)

    return enriched_items, subtotal, tax_total, grand_total


def create_draft_order(dealer_id, items_data, idempotency_key: str = None) -> Order:
    try:
        dealer = Dealer.objects.get(id=dealer_id)
    except (Dealer.DoesNotExist, ValueError, TypeError):
        raise ValidationError(f"Dealer with id {dealer_id} does not exist.")

    prepared_items = validate_and_prepare_items(items_data)
    enriched_items, subtotal, tax_total, grand_total = compute_order_totals(prepared_items)

    order_num = generate_order_number()

    with transaction.atomic():
        order = Order.objects.create(
            order_number=order_num,
            dealer=dealer,
            status="DRAFT",
            subtotal=subtotal,
            tax_total=tax_total,
            grand_total=grand_total,
        )

        item_instances = [
            OrderItem(
                order=order,
                product=item["product"],
                sku=item["sku"],
                name=item["name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                line_subtotal=item["line_subtotal"],
                line_tax=item["line_tax"],
                line_total=item["line_total"],
            )
            for item in enriched_items
        ]
        OrderItem.objects.bulk_create(item_instances)

    return order


def replace_order_items(order: Order, items_data: list) -> Order:
    if order.status != "DRAFT":
        raise OrderLockedError("Only DRAFT orders can be edited.")

    prepared_items = validate_and_prepare_items(items_data)
    enriched_items, subtotal, tax_total, grand_total = compute_order_totals(prepared_items)

    with transaction.atomic():
        order.items.all().delete()
        item_instances = [
            OrderItem(
                order=order,
                product=item["product"],
                sku=item["sku"],
                name=item["name"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                line_subtotal=item["line_subtotal"],
                line_tax=item["line_tax"],
                line_total=item["line_total"],
            )
            for item in enriched_items
        ]
        OrderItem.objects.bulk_create(item_instances)

        order.subtotal = subtotal
        order.tax_total = tax_total
        order.grand_total = grand_total
        order.save(update_fields=["subtotal", "tax_total", "grand_total", "updated_at"])

    return order


def confirm_order(order: Order) -> Order:
    if order.status != "DRAFT":
        raise InvalidTransitionError(f"Cannot confirm order from status '{order.status}'.")

    with transaction.atomic():
        items = list(order.items.select_related("product").all())
        skus = [it.sku for it in items]

        # Row-level locking on inventories to prevent overselling under concurrent requests
        inventories = {
            inv.product_id: inv
            for inv in Inventory.objects.select_for_update().filter(product_id__in=skus)
        }

        short_details = []
        short_messages = []

        for item in items:
            inv = inventories.get(item.sku)
            avail = inv.quantity if inv else 0
            if item.quantity > avail:
                short_details.append({
                    "sku": item.sku,
                    "requested": item.quantity,
                    "available": avail,
                })
                short_messages.append(
                    f"Insufficient stock for {item.name}. Available: {avail}, Requested: {item.quantity}"
                )

        if short_details:
            raise InsufficientStockError(
                message=" ".join(short_messages),
                details=short_details,
            )

        # Deduct stock atomically and lock unit prices
        for item in items:
            inv = inventories[item.sku]
            inv.quantity -= item.quantity
            inv.save(update_fields=["quantity", "updated_at"])

        order.status = "CONFIRMED"
        order.save(update_fields=["status", "updated_at"])

    return order


def dispatch_order(order: Order) -> Order:
    if order.status != "CONFIRMED":
        raise InvalidTransitionError(f"Cannot dispatch order from status '{order.status}'.")

    order.status = "DISPATCHED"
    order.save(update_fields=["status", "updated_at"])
    return order


def deliver_order(order: Order) -> Order:
    if order.status != "DISPATCHED":
        raise InvalidTransitionError(f"Cannot deliver order from status '{order.status}'.")

    order.status = "DELIVERED"
    order.save(update_fields=["status", "updated_at"])
    return order


def cancel_order(order: Order) -> Order:
    if order.status not in ("DRAFT", "CONFIRMED"):
        raise InvalidTransitionError(f"Cannot cancel order with status '{order.status}'.")

    with transaction.atomic():
        if order.status == "CONFIRMED":
            # Restore stock atomically with row locking
            items = list(order.items.all())
            skus = [it.sku for it in items]
            inventories = {
                inv.product_id: inv
                for inv in Inventory.objects.select_for_update().filter(product_id__in=skus)
            }
            for item in items:
                inv = inventories.get(item.sku)
                if inv:
                    inv.quantity += item.quantity
                    inv.save(update_fields=["quantity", "updated_at"])

        order.status = "CANCELLED"
        order.save(update_fields=["status", "updated_at"])

    return order
