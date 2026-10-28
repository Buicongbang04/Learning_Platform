import csv
import math
import random

import pyarrow.compute as pc
import pyarrow.parquet as pq
import pytest

from testkit import Exercise

ex = Exercise(__file__)
N = 6000
COLUMNS = ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value", "shipping_limit_date"]


@pytest.fixture(scope="module")
def columnar():
    return ex.module("columnar.py")


@pytest.fixture
def csv_path(tmp_path):
    rng = random.Random(42)
    path = tmp_path / "order_items.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        for i in range(N):
            w.writerow([
                f"order_{i // 2:08d}_{'abcdef0123456789' * 2}",
                i % 2 + 1,
                f"product_{rng.randint(1, 50):04d}_{'f' * 20}",
                f"seller_{rng.randint(1, 10):04d}_{'e' * 20}",
                round(rng.uniform(5, 500), 2),
                round(rng.uniform(1, 50), 2),
                f"2024-0{rng.randint(1, 9)}-1{rng.randint(0, 9)} 10:00:00",
            ])
    return path


@pytest.fixture
def parquet_path(columnar, csv_path, tmp_path):
    out = tmp_path / "order_items.parquet"
    columnar.csv_to_parquet(csv_path, out, compression="zstd", row_group_size=1000)
    return out


def test_csv_to_parquet(columnar, csv_path, tmp_path):
    out = tmp_path / "x.parquet"
    assert columnar.csv_to_parquet(csv_path, out, compression="snappy", row_group_size=2500) == N
    meta = pq.ParquetFile(out).metadata
    assert meta.num_rows == N
    assert meta.num_row_groups == math.ceil(N / 2500)
    assert meta.row_group(0).column(0).compression.lower() == "snappy"


def test_read_columns(columnar, parquet_path):
    t = columnar.read_columns(parquet_path, ["price", "order_id"])
    assert t.column_names == ["price", "order_id"]
    assert t.num_rows == N


def test_row_group_stats(columnar, parquet_path):
    stats = columnar.row_group_stats(parquet_path, "price")
    assert len(stats) == 6
    full = pq.read_table(parquet_path, columns=["price"]).column("price").to_pylist()
    for i, (lo, hi) in enumerate(stats):
        chunk = full[i * 1000:(i + 1) * 1000]
        assert lo == pytest.approx(min(chunk))
        assert hi == pytest.approx(max(chunk))


def test_size_ratio(columnar, csv_path, parquet_path):
    ratio = columnar.size_ratio(csv_path, parquet_path)
    assert 0 < ratio < 0.5


def test_read_expensive_items(columnar, parquet_path):
    t = columnar.read_expensive_items(parquet_path, 400.0)
    prices = t.column("price")
    assert t.num_rows > 0
    assert pc.min(prices).as_py() >= 400.0
    expected = pc.sum(pc.greater_equal(pq.read_table(parquet_path).column("price"), 400.0)).as_py()
    assert t.num_rows == expected
