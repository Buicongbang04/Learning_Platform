import multiprocessing
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
NEEDS_FORK = pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="Hệ điều hành không có start method \"fork\": hàm định nghĩa trong notebook không gửi được sang tiến trình "
    "con. Chạy bài trên Linux hoặc WSL.",
)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("mapreduce_revenue.ipynb")


def tiny_tx():
    return pd.DataFrame({
        "Invoice":     [1, 1, "C2", 3, 4, 5, 6, 7, 8, 9],
        "Description": ["SET/3 RED BAGS", "red heart", "RED BAG", "Heart  of Wood", None, "bag", "x", "y",
                        "Bag, bag", "LUNCH BAG"],
        "Quantity":    [2, 1, -5, 10, 1, 3, 0, 1, 2, 4],
        "Price":       [5.0, 10.0, 5.0, 1.0, 2.0, 2.0, 1.0, 0.0, 3.0, 1.5],
        "Country":     ["UK", "UK", "UK", "France", "France", "UK", "UK", "Spain", "Spain", "UK"],
    })


def test_valid_lines(nb):
    tx = tiny_tx()
    before = tx.copy()
    out = nb.valid_lines(tx)
    pd.testing.assert_frame_equal(tx, before)
    # bỏ C2, dòng Quantity 0 (hoá đơn 6), dòng Price 0 (hoá đơn 7)
    assert out["Invoice"].astype(str).tolist() == ["1", "1", "3", "4", "5", "8", "9"]
    assert out["revenue"].tolist() == pytest.approx([10.0, 10.0, 10.0, 2.0, 6.0, 6.0, 6.0])


def test_split_chunks(nb):
    df = pd.DataFrame({"a": range(10)})
    chunks = nb.split_chunks(df, 3)
    assert [len(c) for c in chunks] == [4, 3, 3]
    pd.testing.assert_frame_equal(pd.concat(chunks), df)
    assert len(nb.split_chunks(df, 1)) == 1 and len(nb.split_chunks(df, 10)) == 10
    with pytest.raises(ValueError):
        nb.split_chunks(df, 0)


def test_map_revenue(nb):
    out = nb.map_revenue(tiny_tx())
    assert out == pytest.approx({"UK": 32.0, "France": 12.0, "Spain": 6.0})


def test_map_words(nb):
    out = nb.map_words(tiny_tx())
    # dòng hợp lệ: "SET/3 RED BAGS", "red heart", "Heart  of Wood", None, "bag", "Bag, bag", "LUNCH BAG"
    assert out == {"set": 1, "red": 2, "bags": 1, "heart": 2, "of": 1, "wood": 1, "bag": 4, "lunch": 1}


def test_reduce_counts(nb):
    out = nb.reduce_counts([{"a": 1, "b": 2}, {}, {"b": 3, "c": 1.5}])
    assert out == {"a": 1, "b": 5, "c": 1.5}
    assert nb.reduce_counts([]) == {}


@pytest.mark.parametrize("n_workers", [1, pytest.param(3, marks=NEEDS_FORK)])
def test_run_mapreduce_matches_pandas(nb, n_workers):
    tx = tiny_tx()
    assert nb.run_mapreduce(tx, nb.map_revenue, n_workers) == pytest.approx(nb.pandas_revenue(tx))
    assert nb.run_mapreduce(tx, nb.map_words, n_workers) == nb.map_words(tx)


def read_retail_1011() -> pd.DataFrame:
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    stat = xlsx.stat()
    cache = Path(tempfile.gettempdir()) / "da-cache" / f"retail-1011-{stat.st_size}-{int(stat.st_mtime)}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    df = pd.read_excel(xlsx, sheet_name="Year 2010-2011")                     # lần đầu 20-90 giây
    df["Invoice"] = df["Invoice"].astype(str)
    df["StockCode"] = df["StockCode"].astype(str)
    df["Description"] = df["Description"].astype("string")
    cache.parent.mkdir(exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
    df.to_parquet(tmp)
    tmp.replace(cache)
    return df


@pytest.fixture(scope="module")
def retail():
    return read_retail_1011()


@NEEDS_FORK
def test_real_revenue(nb, retail):
    by_pandas = nb.pandas_revenue(retail)
    by_mr = nb.run_mapreduce(retail, nb.map_revenue, 2)
    assert len(by_mr) == 38
    assert by_mr == pytest.approx(by_pandas, rel=1e-9)
    assert sum(by_mr.values()) == pytest.approx(10_666_702.54, abs=0.01)
    assert by_mr["United Kingdom"] == pytest.approx(9_025_222.08, abs=0.01)
    top3 = sorted(by_mr, key=by_mr.get, reverse=True)[:3]
    assert top3 == ["United Kingdom", "Netherlands", "EIRE"]


@NEEDS_FORK
def test_real_words(nb, retail):
    words = nb.run_mapreduce(retail, nb.map_words, 2)
    assert len(words) == 2062
    top = sorted(words, key=words.get, reverse=True)[:5]
    assert top == ["set", "of", "bag", "red", "heart"]
    assert words["set"] == 62760 and words["bag"] == 51186
