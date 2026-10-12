import math
import pathlib
import pandas as pd
import numpy as np
from django.conf import settings
from products.models import Inventory

BASE_DIR = pathlib.Path(settings.BASE_DIR)
DATA_DIR = BASE_DIR / "data"
ML_DIR = BASE_DIR / "ml"

FORECAST_WEEKS = ["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19"]


class ForecastingService:
    _forecast_cache = None
    _lead_times_cache = None
    _sigma_cache = None

    @classmethod
    def load_data(cls, force_reload=False):
        if cls._forecast_cache is not None and not force_reload:
            return

        forecast_path = ML_DIR / "forecast.csv"
        lead_times_path = DATA_DIR / "lead_times.csv"
        sales_history_path = DATA_DIR / "sales_history.csv"

        if not forecast_path.exists():
            raise FileNotFoundError(f"Forecast file not found: {forecast_path}")

        f_df = pd.read_csv(forecast_path)
        forecast_map = {}
        for _, row in f_df.iterrows():
            sku = str(row["sku"]).strip()
            w = str(row["week_start"]).strip()
            u = float(row["forecast_units"])
            if sku not in forecast_map:
                forecast_map[sku] = []
            forecast_map[sku].append({"week_start": w, "forecast_units": u})

        # Sort each SKU's forecast by week_start
        for sku in forecast_map:
            forecast_map[sku] = sorted(forecast_map[sku], key=lambda x: x["week_start"])

        cls._forecast_cache = forecast_map

        # Lead times
        l_df = pd.read_csv(lead_times_path)
        cls._lead_times_cache = {
            str(r["sku"]).strip(): int(r["lead_time_weeks"])
            for _, r in l_df.iterrows()
        }

        # Calculate sigma per SKU over most recent 12 weeks of sales_history.csv
        s_df = pd.read_csv(sales_history_path)
        s_df["week_start"] = pd.to_datetime(s_df["week_start"])
        sigma_map = {}
        for sku, group in s_df.groupby("sku"):
            recent12 = group.sort_values("week_start").tail(12)["units_sold"].values
            if len(recent12) > 1:
                sigma = float(np.std(recent12, ddof=1))
            else:
                sigma = 0.0
            sigma_map[str(sku).strip()] = sigma

        cls._sigma_cache = sigma_map

    @classmethod
    def get_sku_forecast(cls, sku: str):
        cls.load_data()
        sku = sku.strip()
        if sku not in cls._forecast_cache or sku not in cls._lead_times_cache:
            return None
        return cls._forecast_cache.get(sku)

    @classmethod
    def get_reorder_suggestions(cls):
        cls.load_data()

        # Fetch current stock for all forecast SKUs in one query
        forecast_skus = list(cls._lead_times_cache.keys())
        inventories = {
            inv.product_id: inv.quantity
            for inv in Inventory.objects.filter(product_id__in=forecast_skus)
        }

        results = []
        for sku in forecast_skus:
            lead_time_weeks = cls._lead_times_cache[sku]
            current_stock = inventories.get(sku, 0)
            forecast_list = cls._forecast_cache.get(sku, [])

            # lead_time_demand = sum of forecast_units for the first L forecast weeks
            ltd = sum(
                item["forecast_units"]
                for item in forecast_list[:lead_time_weeks]
            )
            lead_time_demand = round(float(ltd), 1)

            # sigma = sample std dev (ddof=1) over recent 12 weeks
            sigma = cls._sigma_cache.get(sku, 0.0)

            # safety_stock = ceil(1.65 * sigma * sqrt(L))
            safety_stock = int(math.ceil(1.65 * sigma * math.sqrt(lead_time_weeks)))

            # reorder_point = lead_time_demand + safety_stock
            reorder_point = round(lead_time_demand + safety_stock, 1)

            # reorder_qty = max(0, ceil(reorder_point - current_stock))
            reorder_qty = max(0, int(math.ceil(reorder_point - current_stock)))

            results.append({
                "sku": sku,
                "current_stock": current_stock,
                "lead_time_weeks": lead_time_weeks,
                "lead_time_demand": lead_time_demand,
                "safety_stock": safety_stock,
                "reorder_point": reorder_point,
                "reorder_qty": reorder_qty,
            })

        return results
