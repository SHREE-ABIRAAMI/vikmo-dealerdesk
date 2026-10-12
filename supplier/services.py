import os
import time
from typing import Tuple
import requests
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.db import transaction

from products.models import Product, Inventory
from core.exceptions import SupplierUnavailableError


def parse_iso_timestamp(ts_str: str) -> datetime:
    if not ts_str:
        return datetime.min
    ts_str = ts_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts_str)
    except Exception:
        return datetime.min


def is_valid_price(price_val) -> Tuple[bool, Decimal]:
    try:
        d = Decimal(str(price_val))
    except (InvalidOperation, TypeError, ValueError):
        return False, Decimal("0.00")
    if d <= 0:
        return False, Decimal("0.00")
    if d.as_tuple().exponent < -2:
        return False, Decimal("0.00")
    return True, d


def sync_supplier_catalogue() -> dict:
    supplier_url = getattr(settings, "SUPPLIER_API_URL", "http://127.0.0.1:8099").rstrip("/")
    api_key = getattr(settings, "SUPPLIER_API_KEY", "")

    headers = {"X-Api-Key": api_key}
    cursor = None
    all_raw_items = []
    pages_fetched = 0
    requests_made = 0

    session = requests.Session()

    # Step 1: Fetch every page with bounded retries
    while True:
        url = f"{supplier_url}/v1/products?limit=20"
        if cursor:
            url += f"&cursor={cursor}"

        success = False
        last_error = None

        for attempt in range(1, 6):
            requests_made += 1
            try:
                resp = session.get(url, headers=headers, timeout=20)
            except requests.RequestException as e:
                last_error = str(e)
                if attempt < 5:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                break

            if resp.status_code == 200:
                success = True
                pages_fetched += 1
                data = resp.json()
                items = data.get("items") or []
                all_raw_items.extend(items)
                cursor = data.get("next_cursor")
                break
            elif resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait_secs = max(1, int(retry_after))
                except (ValueError, TypeError):
                    wait_secs = 1
                if attempt < 5:
                    time.sleep(wait_secs)
                    continue
                else:
                    last_error = "Rate limit exceeded (429) after 5 attempts"
                    break
            elif 500 <= resp.status_code <= 599:
                last_error = f"Server error {resp.status_code}"
                if attempt < 5:
                    time.sleep(0.5 * (2 ** (attempt - 1)))
                    continue
                break
            elif resp.status_code == 401:
                # Key rejected
                raise SupplierUnavailableError("Supplier API key invalid (401).")
            else:
                last_error = f"Unexpected status {resp.status_code}"
                break

        if not success:
            raise SupplierUnavailableError(f"Supplier sync failed: {last_error}")

        if not cursor:
            # End of pagination
            break

    # Step 2: Validate items & collect rejected
    valid_items = []
    rejected = []

    for item in all_raw_items:
        supplier_sku = item.get("supplier_sku", "")
        sku = str(item.get("sku", "") or "").strip()
        price_raw = item.get("price")

        if not sku:
            rejected.append({"supplier_sku": supplier_sku, "reason": "missing or empty sku"})
            continue

        valid_p, dec_price = is_valid_price(price_raw)
        if not valid_p:
            rejected.append({"supplier_sku": supplier_sku, "reason": "invalid price"})
            continue

        valid_items.append({
            **item,
            "sku": sku,
            "parsed_price": dec_price,
            "parsed_updated_at": parse_iso_timestamp(item.get("updated_at", "")),
        })

    # Step 3: Deduplicate SKUs using latest updated_at
    sku_map = {}
    for it in valid_items:
        sku = it["sku"]
        if sku not in sku_map:
            sku_map[sku] = it
        else:
            if it["parsed_updated_at"] > sku_map[sku]["parsed_updated_at"]:
                sku_map[sku] = it

    # Step 4: Apply to catalogue inside an atomic database transaction
    created_count = 0
    updated_count = 0
    unchanged_count = 0

    with transaction.atomic():
        # Pre-fetch existing products
        target_skus = list(sku_map.keys())
        existing_products = {
            p.sku: p
            for p in Product.objects.filter(sku__in=target_skus)
        }

        new_products = []
        new_inventories = []

        for sku, sup_item in sku_map.items():
            name = sup_item.get("name", "")
            category = sup_item.get("category", "")
            brand = sup_item.get("brand", "")
            vehicle_fitment = sup_item.get("vehicle_fitment", "")
            description = sup_item.get("description", "")
            price = sup_item["parsed_price"]

            if sku not in existing_products:
                prod = Product(
                    sku=sku,
                    name=name,
                    category=category,
                    brand=brand,
                    vehicle_fitment=vehicle_fitment,
                    price=price,
                    description=description,
                )
                new_products.append(prod)
                new_inventories.append(Inventory(product=prod, quantity=0))
                created_count += 1
            else:
                existing = existing_products[sku]
                changed = (
                    existing.name != name
                    or existing.category != category
                    or existing.brand != brand
                    or existing.vehicle_fitment != vehicle_fitment
                    or existing.description != description
                    or existing.price != price
                )
                if changed:
                    existing.name = name
                    existing.category = category
                    existing.brand = brand
                    existing.vehicle_fitment = vehicle_fitment
                    existing.description = description
                    existing.price = price
                    existing.save(update_fields=[
                        "name",
                        "category",
                        "brand",
                        "vehicle_fitment",
                        "description",
                        "price",
                        "updated_at",
                    ])
                    updated_count += 1
                else:
                    unchanged_count += 1

        if new_products:
            Product.objects.bulk_create(new_products)
            Inventory.objects.bulk_create(new_inventories)

    return {
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "rejected": rejected,
        "pages_fetched": pages_fetched,
        "requests_made": requests_made,
    }
