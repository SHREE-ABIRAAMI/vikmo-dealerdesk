"""VIKMO DealerDesk ML Forecasting Pipeline.

Generates ml/forecast.csv for 40 target SKUs across 4 forecast weeks.
Features:
- SKU historical baseline (recent non-promo demand)
- SKU and global promotional uplift factor
- Dynamic festival proximity model (weeks-to-Diwali demand ramp)
- Autoregressive lags and rolling statistics via Gradient Boosted Decision Trees
- Ensemble blend combining domain decomposition and HistGradientBoostingRegressor
- Zero future data leakage
"""
import os
import pathlib
import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ML_DIR = BASE_DIR / "ml"

TARGET_WEEKS = ["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19"]
DIWALI_DATES = {
    2024: pd.Timestamp("2024-11-01"),
    2025: pd.Timestamp("2025-10-21"),
    2026: pd.Timestamp("2026-11-08"),
}


def get_festive_factor(weeks_to_diwali: int) -> float:
    # Empirical pre-Diwali demand multiplier curve
    multipliers = {0: 1.85, 1: 1.75, 2: 1.60, 3: 1.45, 4: 1.30, 5: 1.15}
    return multipliers.get(weeks_to_diwali, 1.0)


def generate_forecast():
    lead_times_path = DATA_DIR / "lead_times.csv"
    sales_history_path = DATA_DIR / "sales_history.csv"
    promo_calendar_path = DATA_DIR / "promo_calendar.csv"
    festival_calendar_path = DATA_DIR / "festival_calendar.csv"
    output_path = ML_DIR / "forecast.csv"

    lead_df = pd.read_csv(lead_times_path)
    target_skus = sorted(lead_df["sku"].unique().tolist())
    assert len(target_skus) == 40, f"Expected 40 SKUs, got {len(target_skus)}"

    sales_df = pd.read_csv(sales_history_path)
    sales_df["week_start"] = pd.to_datetime(sales_df["week_start"])
    sales_df = sales_df.sort_values(["sku", "week_start"]).reset_index(drop=True)

    promo_df = pd.read_csv(promo_calendar_path)
    promo_df["week_start"] = pd.to_datetime(promo_df["week_start"])
    promo_lookup = promo_df.set_index(["sku", "week_start"])["promo_flag"].to_dict()

    # 1. Domain Decomposed Model
    # Calculate non-promo baseline for each SKU
    non_promo_sales = sales_df[sales_df["promo_flag"] == 0]
    global_promo_ratio = (
        sales_df[sales_df["promo_flag"] == 1]["units_sold"].mean()
        / max(1.0, non_promo_sales["units_sold"].mean())
    )

    sku_baselines = {}
    sku_promo_factors = {}

    for sku in target_skus:
        sku_data = sales_df[sales_df["sku"] == sku]
        sku_np = sku_data[sku_data["promo_flag"] == 0]
        if len(sku_np) >= 4:
            base = sku_np.tail(8)["units_sold"].mean()
        elif len(sku_data) > 0:
            base = sku_data["units_sold"].mean()
        else:
            base = 15.0
        sku_baselines[sku] = max(0.5, base)

        sku_p = sku_data[sku_data["promo_flag"] == 1]["units_sold"]
        if len(sku_p) >= 2 and len(sku_np) >= 4:
            sku_promo_factors[sku] = float(sku_p.mean()) / max(1.0, float(sku_np["units_sold"].mean()))
        else:
            sku_promo_factors[sku] = float(global_promo_ratio)

    # 2. Build feature matrix for ML Model (HistGradientBoostingRegressor)
    records = []
    for sku, group in sales_df.groupby("sku"):
        g = group.sort_values("week_start").reset_index(drop=True)
        for i in range(len(g)):
            row = g.iloc[i]
            w = row["week_start"]
            past = g.iloc[:i]
            lag1 = past.iloc[-1]["units_sold"] if len(past) > 0 else 0
            ma4 = past.tail(4)["units_sold"].mean() if len(past) >= 4 else (past["units_sold"].mean() if len(past) > 0 else 0)
            past_np = past[past["promo_flag"] == 0]
            base_np = past_np.tail(8)["units_sold"].mean() if len(past_np) > 0 else ma4
            records.append({
                "sku": sku,
                "week_start": w,
                "units_sold": row["units_sold"],
                "promo_flag": row["promo_flag"],
                "weeks_to_diwali": (DIWALI_DATES[w.year] - w).days // 7,
                "lag1": lag1,
                "ma4": ma4,
                "base_np": base_np,
            })

    feat_df = pd.DataFrame(records)
    feat_df["sku_cat"] = feat_df["sku"].astype("category")
    features = ["promo_flag", "weeks_to_diwali", "lag1", "ma4", "base_np", "sku_cat"]

    gbrt = HistGradientBoostingRegressor(
        categorical_features=["sku_cat"],
        max_iter=100,
        random_state=42
    )
    gbrt.fit(feat_df[features], feat_df["units_sold"])

    # 3. Predict the 4 future weeks sequentially
    forecast_rows = []

    # Keep a running history for autoregressive features
    running_history = sales_df.copy()

    for w_str in TARGET_WEEKS:
        w = pd.Timestamp(w_str)
        w2d = (DIWALI_DATES[w.year] - w).days // 7
        fest_factor = get_festive_factor(w2d)

        for sku in target_skus:
            is_promo = promo_lookup.get((sku, w), 0)

            # Domain prediction
            p_domain = sku_baselines[sku] * fest_factor
            if is_promo:
                p_domain *= sku_promo_factors[sku]

            # GBRT prediction
            past_sku = running_history[running_history["sku"] == sku]
            lag1 = past_sku.iloc[-1]["units_sold"] if len(past_sku) > 0 else sku_baselines[sku]
            ma4 = past_sku.tail(4)["units_sold"].mean() if len(past_sku) >= 4 else sku_baselines[sku]
            past_np = past_sku[past_sku["promo_flag"] == 0]
            base_np = past_np.tail(8)["units_sold"].mean() if len(past_np) > 0 else ma4

            row_feat = pd.DataFrame([{
                "promo_flag": is_promo,
                "weeks_to_diwali": w2d,
                "lag1": lag1,
                "ma4": ma4,
                "base_np": base_np,
                "sku_cat": sku,
            }])
            row_feat["sku_cat"] = pd.Categorical(row_feat["sku_cat"], categories=feat_df["sku_cat"].cat.categories)

            p_gbrt = float(gbrt.predict(row_feat[features])[0])
            p_gbrt = max(0.0, p_gbrt)

            # Ensemble blend
            final_pred = 0.5 * p_domain + 0.5 * p_gbrt
            final_pred = round(max(0.0, final_pred), 1)

            forecast_rows.append({
                "sku": sku,
                "week_start": w_str,
                "forecast_units": final_pred,
            })

            # Append synthetic row to running history for subsequent lag calculation
            running_history = pd.concat([
                running_history,
                pd.DataFrame([{"sku": sku, "week_start": w, "units_sold": final_pred, "promo_flag": is_promo}])
            ], ignore_index=True)

    out_df = pd.DataFrame(forecast_rows)
    # Ensure exact column order
    out_df = out_df[["sku", "week_start", "forecast_units"]]
    out_df.to_csv(output_path, index=False)
    print(f"Successfully generated {output_path} with {len(out_df)} rows.")
    return out_df


if __name__ == "__main__":
    generate_forecast()
