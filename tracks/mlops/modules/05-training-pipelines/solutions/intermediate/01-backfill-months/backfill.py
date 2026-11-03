import hashlib
import json
import re
from pathlib import Path

import joblib
import pandas as pd
from prefect import flow, task
from sklearn.linear_model import LinearRegression

MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def month_range(start: str, end: str) -> list[str]:
    parsed = []
    for value in (start, end):
        match = MONTH.match(value)
        if not match:
            raise ValueError(f"tháng không hợp lệ: {value!r}")
        parsed.append(int(match.group(1)) * 12 + int(match.group(2)) - 1)
    if parsed[0] > parsed[1]:
        raise ValueError(f"start {start} sau end {end}")
    return [f"{index // 12:04d}-{index % 12 + 1:02d}" for index in range(parsed[0], parsed[1] + 1)]


def _outputs(out_dir: Path, month: str) -> tuple[Path, Path]:
    return out_dir / f"model-{month}.joblib", out_dir / f"model-{month}.json"


def train_month(month: str, data_dir, out_dir, seed: int = 0) -> dict:
    source = Path(data_dir) / f"trips-{month}.csv"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(source)
    if df.empty:
        raise ValueError(f"{source.name} không có dòng nào")
    model = LinearRegression().fit(df[["distance_km"]], df["duration_s"])
    mae = float((df["duration_s"] - model.predict(df[["distance_km"]])).abs().mean())
    meta = {"month": month, "rows": len(df), "mae": mae, "data_sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
    model_path, meta_path = _outputs(out_dir, month)
    tmp_model, tmp_meta = model_path.with_suffix(".joblib.tmp"), meta_path.with_suffix(".json.tmp")
    joblib.dump(model, tmp_model)
    tmp_meta.write_text(json.dumps(meta), encoding="utf-8")
    tmp_model.replace(model_path)
    tmp_meta.replace(meta_path)
    return meta


month_task = task(train_month, name="train-month")


@flow
def backfill(start: str, end: str, data_dir, out_dir, overwrite: bool = False) -> dict:
    result = {"done": [], "skipped": [], "failed": {}}
    for month in month_range(start, end):
        model_path, meta_path = _outputs(Path(out_dir), month)
        if not overwrite and model_path.exists() and meta_path.exists():
            result["skipped"].append(month)
            continue
        try:
            month_task(month, data_dir, out_dir)
            result["done"].append(month)
        except Exception as error:
            result["failed"][month] = str(error)
    return result
