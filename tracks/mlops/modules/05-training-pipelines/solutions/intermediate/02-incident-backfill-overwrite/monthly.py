import json
from pathlib import Path

import pandas as pd
from prefect import flow, task
from sklearn.linear_model import LinearRegression

def load_month(month: str, data_dir) -> pd.DataFrame:
    return pd.read_csv(Path(data_dir) / f"trips-{month}.csv")


def month_metrics(month: str, data_dir) -> dict:
    df = load_month(month, data_dir)
    model = LinearRegression().fit(df[["distance_km"]], df["duration_s"])
    mae = float((df["duration_s"] - model.predict(df[["distance_km"]])).abs().mean())
    return {"month": month, "rows": len(df), "mean_duration": float(df["duration_s"].mean()), "mae": mae}


@task
def process_month(month: str, data_dir, results_dir) -> dict:
    metrics = month_metrics(month, data_dir)
    out = Path(results_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{month}.json").write_text(json.dumps(metrics, sort_keys=True), encoding="utf-8")
    return metrics


@flow
def run_months(months: list[str], data_dir, results_dir) -> list[str]:
    for month in months:
        process_month(month, data_dir, results_dir)
    return list(months)
