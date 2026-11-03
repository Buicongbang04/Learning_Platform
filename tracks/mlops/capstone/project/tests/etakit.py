"""Helper chung của test capstone ETA: thư mục được chấm, import `eta` an toàn, dữ liệu giả."""

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import use_solution

CAPSTONE = Path(__file__).resolve().parents[2]
PROJECT = CAPSTONE / "solutions" / "project" if use_solution() else CAPSTONE / "project"
COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]


def need(module: str, *names: str):
    src = str(PROJECT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    try:
        package = importlib.import_module("eta")
        where = Path(list(package.__path__)[0]).resolve()
        if where != (PROJECT / "src" / "eta").resolve():
            pytest.fail(f"Đang import eta từ {where}, không phải từ {PROJECT / 'src'}", pytrace=False)
        mod = importlib.import_module(f"eta.{module}")
    except ModuleNotFoundError as err:
        pytest.fail(f"Chưa import được eta.{module} từ {PROJECT.relative_to(CAPSTONE.parents[2])}/src: {err}", pytrace=False)
    missing = [n for n in names if not hasattr(mod, n)]
    if missing:
        pytest.fail(f"eta.{module} chưa có {missing}", pytrace=False)
    return mod


def require_file(*parts: str) -> Path:
    path = PROJECT.joinpath(*parts)
    if not path.is_file():
        pytest.fail(f"Chưa có tệp {path.relative_to(CAPSTONE.parents[2])}", pytrace=False)
    return path


def synthetic_month(n: int, month: str = "2019-01", seed: int = 0, extra_columns: bool = True) -> pd.DataFrame:
    """Chuyến giả cho test: thời lượng phụ thuộc khoảng cách, giờ cao điểm và cặp zone, mọi dòng đều sạch."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp(f"{month}-01")
    days = (start + pd.offsets.MonthBegin(1) - start).days
    pickup = start + pd.to_timedelta(np.sort(rng.integers(0, days * 86_400 - 4 * 3600, n)), unit="s")
    pu = rng.choice([132, 138, 161, 162, 230, 236, 237, 48, 79, 186], n)
    do = rng.choice([132, 138, 161, 162, 230, 236, 237, 48, 79, 170], n)
    distance = np.round(rng.gamma(2.0, 1.5, n) + 0.2, 2)
    rush = np.isin(pickup.hour, [8, 9, 17, 18]).astype(float)
    airport = (np.isin(pu, [132, 138]) | np.isin(do, [132, 138])).astype(float)
    duration = 120 + distance * 160 * (1 + 0.4 * rush) + 600 * airport + rng.normal(0, 40, n)
    duration = np.clip(duration, 90, 9000).round()
    frame = pd.DataFrame(
        {
            "VendorID": rng.integers(1, 3, n),
            "tpep_pickup_datetime": pickup.astype("datetime64[us]"),
            "tpep_dropoff_datetime": (pickup + pd.to_timedelta(duration, unit="s")).astype("datetime64[us]"),
            "passenger_count": rng.integers(1, 5, n).astype(float),
            "trip_distance": distance,
            "PULocationID": pu.astype("int64"),
            "DOLocationID": do.astype("int64"),
            "fare_amount": np.round(2.5 + distance * 2.5, 2),
        }
    )
    return frame if extra_columns else frame[COLUMNS]


PREDICTION_LOG_COLUMNS = ["request_id", "ts", "model_version", "variant", "PULocationID", "DOLocationID",
                          "pickup_datetime", "trip_distance", "eta_s"]


def write_months(raw: Path, months: list[str], n: int = 1_500, seed: int = 0) -> Path:
    """Ghi tệp `yellow_tripdata_<month>.parquet` giả cho từng tháng vào `raw`."""
    raw.mkdir(parents=True, exist_ok=True)
    for i, month in enumerate(months):
        synthetic_month(n, month=month, seed=seed + i).to_parquet(raw / f"yellow_tripdata_{month}.parquet", index=False)
    return raw


def write_config(path: Path, raw: Path, months: list[str], mlflow_uri: str, model_name: str, **extra) -> Path:
    """Tệp params.yaml nhỏ cho flow: mẫu 1 200 dòng, model 20 vòng."""
    import yaml

    params = {"data_dir": str(raw), "months": months, "sample_rows": 1_200, "seed": 0,
              "model_params": {"max_iter": 20}, "mlflow_uri": mlflow_uri, "model_name": model_name, **extra}
    path.write_text(yaml.safe_dump(params, sort_keys=False), encoding="utf-8")
    return path


def local_registry(tmp_path: Path, prefix: str = "eta") -> tuple[str, str]:
    """MLflow SQLite trong `tmp_path` và tên model ngẫu nhiên; experiment cùng tên lưu artifact trong `tmp_path`."""
    import uuid

    import mlflow

    import mlopskit

    uri = mlopskit.mlflow_local(tmp_path)
    name = f"{prefix}-{uuid.uuid4().hex[:8]}"
    mlflow.create_experiment(name, artifact_location=(tmp_path / "artifacts" / name).as_uri())
    return uri, name
