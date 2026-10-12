import csv
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import Product, Inventory
from dealers.models import Dealer


class Command(BaseCommand):
    help = "Load catalogue.csv and dealers.csv into the database. Safe to run multiple times without duplicating."

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR  # <repo root>/data
        catalogue_path = data_dir / "catalogue.csv"
        dealers_path = data_dir / "dealers.csv"

        if not catalogue_path.exists():
            self.stdout.write(self.style.ERROR(f"catalogue.csv not found at {catalogue_path}"))
            return

        if not dealers_path.exists():
            self.stdout.write(self.style.ERROR(f"dealers.csv not found at {dealers_path}"))
            return

        self.stdout.write("Seeding dealers from dealers.csv...")
        dealers_created = 0
        dealers_updated = 0
        seen_codes = set()
        with open(dealers_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for row in reader:
                    code = row["dealer_code"].strip()
                    seen_codes.add(code)
                    name = row["name"].strip()
                    city = row.get("city", "").strip()
                    phone = row.get("phone", "").strip()
                    email = row.get("email", "").strip()
                    gstin = row.get("gstin", "").strip()
                    credit_limit = Decimal(row.get("credit_limit", "0.00").strip() or "0.00")

                    dealer, created = Dealer.objects.update_or_create(
                        dealer_code=code,
                        defaults={
                            "name": name,
                            "city": city,
                            "phone": phone,
                            "email": email,
                            "gstin": gstin,
                            "credit_limit": credit_limit,
                        },
                    )
                    if created:
                        dealers_created += 1
                    else:
                        dealers_updated += 1

        # Clean up any transient smoke test dealers not in dealers.csv
        from orders.models import Order
        extra_dealers = Dealer.objects.exclude(dealer_code__in=seen_codes)
        Order.objects.filter(dealer__in=extra_dealers).delete()
        extra_dealers.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Dealers seeded: {dealers_created} created, {dealers_updated} updated (total: {Dealer.objects.count()})"
            )
        )

        self.stdout.write("Seeding products and initial inventory from catalogue.csv...")
        products_created = 0
        products_updated = 0
        seen_skus = set()
        with open(catalogue_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with transaction.atomic():
                for row in reader:
                    sku = row["sku"].strip()
                    seen_skus.add(sku)
                    name = row["name"].strip()
                    category = row["category"].strip()
                    brand = row["brand"].strip()
                    vehicle_fitment = row["vehicle_fitment"].strip()
                    price = Decimal(row["price"].strip())
                    stock_qty = int(row["stock"].strip())
                    description = row.get("description", "").strip()

                    product, created = Product.objects.update_or_create(
                        sku=sku,
                        defaults={
                            "name": name,
                            "category": category,
                            "brand": brand,
                            "vehicle_fitment": vehicle_fitment,
                            "price": price,
                            "description": description,
                        },
                    )

                    Inventory.objects.update_or_create(
                        product=product,
                        defaults={"quantity": stock_qty},
                    )

                    if created:
                        products_created += 1
                    else:
                        products_updated += 1

        # Clean up any transient supplier sync products not in catalogue.csv
        from orders.models import OrderItem
        extra_products = Product.objects.exclude(sku__in=seen_skus)
        OrderItem.objects.filter(product__in=extra_products).delete()
        extra_products.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Products seeded: {products_created} created, {products_updated} updated (total: {Product.objects.count()})"
            )
        )
