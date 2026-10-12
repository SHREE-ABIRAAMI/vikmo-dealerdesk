from django.db.models import Q
from products.models import Product, Inventory
from orders.services import create_draft_order as order_service_create_draft


def tool_search_parts(query: str = "", vehicle: str = None, category: str = None, limit: int = 5):
    """Search catalogue for products matching query, vehicle, and/or category."""
    qs = Product.objects.select_related("inventory").all()

    if vehicle and str(vehicle).strip():
        qs = qs.filter(vehicle_fitment__icontains=str(vehicle).strip())

    if category and str(category).strip():
        qs = qs.filter(category__iexact=str(category).strip())

    if query and str(query).strip():
        terms = str(query).strip().split()
        q_obj = Q()
        for term in terms:
            q_obj |= (
                Q(name__icontains=term)
                | Q(sku__icontains=term)
                | Q(brand__icontains=term)
                | Q(description__icontains=term)
            )
        qs = qs.filter(q_obj)

    results = []
    for p in qs[:limit]:
        stock = p.inventory.quantity if hasattr(p, "inventory") and p.inventory else 0
        results.append({
            "sku": p.sku,
            "name": p.name,
            "brand": p.brand,
            "category": p.category,
            "vehicle_fitment": p.vehicle_fitment,
            "price": f"{p.price:.2f}",
            "stock": stock,
            "description": p.description,
        })
    return results


def tool_check_stock(sku: str):
    """Check live stock and price for a given SKU in PostgreSQL."""
    sku = str(sku).strip()
    try:
        p = Product.objects.select_related("inventory").get(sku=sku)
        stock = p.inventory.quantity if hasattr(p, "inventory") and p.inventory else 0
        return {
            "sku": p.sku,
            "name": p.name,
            "brand": p.brand,
            "vehicle_fitment": p.vehicle_fitment,
            "price": f"{p.price:.2f}",
            "stock": stock,
        }
    except Product.DoesNotExist:
        return {"error": f"Product with SKU '{sku}' not found in catalogue."}


def tool_create_draft_order(dealer_id: int, items: list):
    """Create a DRAFT order for a dealer through the order engine."""
    try:
        order = order_service_create_draft(dealer_id=dealer_id, items_data=items)
        return {
            "order_number": order.order_number,
            "dealer_id": order.dealer_id,
            "status": order.status,
            "subtotal": f"{order.subtotal:.2f}",
            "tax_total": f"{order.tax_total:.2f}",
            "grand_total": f"{order.grand_total:.2f}",
            "items": [
                {
                    "sku": item.sku,
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit_price": f"{item.unit_price:.2f}",
                    "line_total": f"{item.line_total:.2f}",
                }
                for item in order.items.all()
            ],
        }
    except Exception as e:
        return {"error": str(e)}


AVAILABLE_TOOLS = {
    "search_parts": tool_search_parts,
    "check_stock": tool_check_stock,
    "create_draft_order": tool_create_draft_order,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_parts",
            "description": "Search the product catalogue for parts by query, vehicle fitment, or category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term, e.g. 'brake pads', 'oil filter', 'chain kit'.",
                    },
                    "vehicle": {
                        "type": "string",
                        "description": "Vehicle make and model, e.g. 'Bajaj Pulsar 150', 'KTM Duke 390'.",
                    },
                    "category": {
                        "type": "string",
                        "description": "Part category, e.g. 'Brakes', 'Drivetrain', 'Engine & Oils'.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_stock",
            "description": "Check current live inventory stock and price for a specific product SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "Exact product SKU, e.g. 'BRK-1044'.",
                    },
                },
                "required": ["sku"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_draft_order",
            "description": "Create a DRAFT order for the dealer with selected SKUs and quantities. Only creates DRAFT orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dealer_id": {
                        "type": "integer",
                        "description": "ID of the dealer creating the order.",
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string", "description": "Product SKU"},
                                "quantity": {"type": "integer", "description": "Quantity to order, integer >= 1"},
                            },
                            "required": ["sku", "quantity"],
                        },
                        "description": "List of products and quantities to order.",
                    },
                },
                "required": ["dealer_id", "items"],
            },
        },
    },
]
