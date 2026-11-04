"""M01: package `eta` (data, features, train, config, cli). Đề ở capstone/milestones/m01-package.md."""

import json
import sys

import numpy as np
import pandas as pd
import pytest
import yaml
from etakit import COLUMNS, DURATION_S, PROJECT, need, synthetic_month

from testkit import Exercise, ROOT, run_sandboxed

FEATURES = ["PULocationID", "DOLocationID", "pickup_hour", "pickup_dow", "trip_distance"]
METRIC_KEYS = {"mae", "p90_abs_err", "mae_airport"}


def split_by_time(df: pd.DataFrame, test_frac: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    ordered = df.sort_values("tpep_pickup_datetime", kind="mergesort").reset_index(drop=True)
    cut = int(len(ordered) * (1 - test_frac))
    return ordered.iloc[:cut].reset_index(drop=True), ordered.iloc[cut:].reset_index(drop=True)


def zone_pair_median_mae(train_df: pd.DataFrame, test_df: pd.DataFrame) -> float:
    medians = train_df.groupby(["PULocationID", "DOLocationID"])["duration_s"].median().rename("pred")
    pred = test_df.join(medians, on=["PULocationID", "DOLocationID"])["pred"].fillna(train_df["duration_s"].median())
    return float(np.abs(test_df["duration_s"] - pred).mean())


def _spy_column_reads(monkeypatch) -> list[tuple[str, object]]:
    """Ghi lại mọi lần đọc parquet qua pyarrow/pandas cùng đối số `columns` được truyền."""
    import pyarrow.parquet as pq

    calls: list[tuple[str, object]] = []

    def wrap(label, original, positional_index=None):
        def spy(*args, **kwargs):
            columns = kwargs.get("columns")
            if columns is None and positional_index is not None and len(args) > positional_index:
                columns = args[positional_index]
            calls.append((label, columns))
            return original(*args, **kwargs)

        return spy

    monkeypatch.setattr(pq, "read_table", wrap("pyarrow.parquet.read_table", pq.read_table, 1))
    monkeypatch.setattr(pq.ParquetFile, "read", wrap("ParquetFile.read", pq.ParquetFile.read, 1))
    monkeypatch.setattr(pq.ParquetFile, "read_row_group", wrap("ParquetFile.read_row_group", pq.ParquetFile.read_row_group, 2))
    monkeypatch.setattr(pq.ParquetFile, "read_row_groups", wrap("ParquetFile.read_row_groups", pq.ParquetFile.read_row_groups, 2))
    monkeypatch.setattr(pd, "read_parquet", wrap("pandas.read_parquet", pd.read_parquet, 2))
    return calls


def test_m01_load_month_columns_and_sample(project, tiny_parquet, monkeypatch):
    data = need("data", "COLUMNS", "load_month")
    calls = _spy_column_reads(monkeypatch)
    data.load_month(tiny_parquet, 100, 0)
    assert calls, "load_month phải đọc tệp bằng pyarrow.parquet.read_table, ParquetFile.read hoặc pandas.read_parquet"
    for label, columns in calls:
        assert columns is not None, f"{label} đọc cả tệp: phải truyền columns=COLUMNS (tệp thật có 19 cột, 7,7 triệu dòng)"
        assert set(columns) <= set(COLUMNS), f"{label} đọc cột ngoài COLUMNS: {sorted(set(columns) - set(COLUMNS))}"
    assert data.COLUMNS == COLUMNS
    df = data.load_month(tiny_parquet, 100, 0)
    assert list(df.columns) == COLUMNS
    assert len(df) == 100
    assert df.equals(data.load_month(tiny_parquet, 100, 0)), "cùng seed phải ra cùng mẫu"
    assert not df.equals(data.load_month(tiny_parquet, 100, 1)), "seed khác phải ra mẫu khác"
    assert len(data.load_month(tiny_parquet, None, 0)) == 1_000, "sample_rows=None là đọc cả tệp"
    assert len(data.load_month(tiny_parquet, 5_000, 0)) == 1_000, "sample_rows lớn hơn số dòng thì lấy hết"


def test_m01_clean_rules(project, dirty_frame):
    features = need("features", "clean")
    before = dirty_frame.copy()
    out = features.clean(dirty_frame, "2019-01")
    assert dirty_frame.equals(before), "clean() không được sửa DataFrame đầu vào"
    assert len(out) == 5, f"fixture 12 dòng, 5 dòng sạch; còn {len(out)}"
    kept = sorted(out["tpep_pickup_datetime"].astype(str))
    expected = sorted(dirty_frame["tpep_pickup_datetime"].iloc[:5].astype(str))
    assert kept == expected, "giữ sai dòng: xem lại biên (60 s, 10 800 s, 100 dặm, zone 1..263, đầu/cuối tháng)"
    assert out["duration_s"].between(*DURATION_S).all()
    assert set(COLUMNS) <= set(out.columns)


def test_m01_config_env_override(project, tmp_path, monkeypatch):
    config = need("config", "Config", "load_config")
    path = tmp_path / "conf" / "params.yaml"
    path.parent.mkdir()
    path.write_text(
        yaml.safe_dump({"data_dir": "raw", "months": ["2019-01"], "sample_rows": 1000, "seed": 0,
                        "model_params": {"max_iter": 10}, "mlflow_uri": "http://127.0.0.1:25000", "model_name": "eta"}),
        encoding="utf-8",
    )
    cfg = config.load_config(path)
    assert cfg.data_dir.resolve() == (tmp_path / "conf" / "raw").resolve(), "data_dir tương đối tính từ thư mục chứa tệp config"
    assert cfg.months == ["2019-01"] and cfg.sample_rows == 1000 and cfg.model_params == {"max_iter": 10}
    monkeypatch.setenv("ETA_SAMPLE_ROWS", "500")
    monkeypatch.setenv("ETA_SEED", "7")
    monkeypatch.setenv("ETA_MONTHS", "2019-02,2019-03")
    cfg = config.load_config(path)
    assert (cfg.sample_rows, cfg.seed, cfg.months) == (500, 7, ["2019-02", "2019-03"])


def test_m01_train_reproducible(project, synthetic_trips):
    features = need("features", "FEATURES", "build_features")
    train = need("train", "train", "evaluate")
    assert features.FEATURES == FEATURES
    train_df, test_df = split_by_time(synthetic_trips)
    X, y = features.build_features(train_df)
    assert list(X.columns) == FEATURES and len(X) == len(y) == len(train_df)
    X_test, y_test = features.build_features(test_df)
    first = train.evaluate(train.train(X, y, {"max_iter": 50, "random_state": 0}), X_test, y_test)
    second = train.evaluate(train.train(X, y, {"max_iter": 50, "random_state": 0}), X_test, y_test)
    assert set(first) == METRIC_KEYS, f"evaluate() phải trả đúng {sorted(METRIC_KEYS)}"
    assert first == second, "hai lần train cùng dữ liệu, cùng params phải ra metric giống hệt"
    assert all(isinstance(v, float) for v in first.values())
    spread = float(np.abs(y_test - y_test.median()).mean())
    assert first["mae"] < spread, f"MAE {first['mae']:.1f} không tốt hơn đoán trung vị ({spread:.1f})"


def test_m01_cli_train_prints_metrics(project, tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    synthetic_month(3_000, seed=3).to_parquet(raw / "yellow_tripdata_2019-01.parquet", index=False)
    cfg = tmp_path / "params.yaml"
    cfg.write_text(
        yaml.safe_dump({"data_dir": str(raw), "months": ["2019-01"], "sample_rows": 2_000, "seed": 0,
                        "model_params": {"max_iter": 30}, "mlflow_uri": "http://127.0.0.1:9", "model_name": "eta"}),
        encoding="utf-8",
    )
    result = run_sandboxed(
        [sys.executable, "-m", "eta.cli", "train", "--config", cfg],
        writable=[tmp_path], cwd=tmp_path, env={"PYTHONPATH": str(PROJECT / "src")}, timeout=180,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines, f"stdout rỗng. stderr:\n{result.stderr[-2000:]}"
    try:
        metrics = json.loads(lines[-1])
    except json.JSONDecodeError:
        pytest.fail(f"dòng cuối stdout không phải JSON: {lines[-1]!r}", pytrace=False)
    assert METRIC_KEYS <= set(metrics) and metrics["mae"] > 0


def test_m01_real_data_baseline(project):
    path = Exercise.dataset("nyc-tlc") / "yellow_tripdata_2019-01.parquet"
    if not path.is_file():
        pytest.skip(f"Thiếu {path.relative_to(ROOT)}. Chạy: uv run python data/download_dataset.py nyc-tlc")
    data = need("data", "load_month")
    features = need("features", "clean", "build_features")
    train = need("train", "train", "evaluate")
    raw = data.load_month(path, 200_000, 0)
    df = features.clean(raw, "2019-01")
    kept = len(df) / len(raw)
    assert 0.94 <= kept <= 0.98, f"clean() giữ {kept:.1%} mẫu 2019-01; luật đúng giữ khoảng 96–97%"
    train_df, test_df = split_by_time(df)
    X, y = features.build_features(train_df)
    model = train.train(X, y, {"random_state": 0})
    metrics = train.evaluate(model, *features.build_features(test_df))
    baseline = zone_pair_median_mae(train_df, test_df)
    print(f"MAE model {metrics['mae']:.1f} s, baseline trung vị theo cặp zone {baseline:.1f} s, airport {metrics['mae_airport']:.1f} s")
    assert metrics["mae"] < baseline, f"MAE {metrics['mae']:.1f} không thắng baseline trung vị theo cặp zone ({baseline:.1f})"
