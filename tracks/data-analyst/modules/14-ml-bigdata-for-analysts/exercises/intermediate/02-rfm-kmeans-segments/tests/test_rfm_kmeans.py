import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
SNAPSHOT = pd.Timestamp("2011-12-10")


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("rfm_kmeans.ipynb")


def tiny_tx():
    nan = np.nan
    return pd.DataFrame({
        "Invoice":     [1, 1, 2, "C3", 4, 5, 6, 7],
        "Quantity":    [2, 1, 5, -1, 3, 1, 4, 2],
        "Price":       [5.0, 10.0, 1.0, 5.0, 2.0, 0.0, 1.0, 3.0],
        "InvoiceDate": pd.to_datetime(["2011-12-01 10:00", "2011-12-01 10:00", "2011-11-10 09:00", "2011-12-09 12:00",
                                       "2011-12-09 12:50", "2011-12-09 13:00", "2011-06-01 08:00", "2011-12-05 08:00"]),
        "Customer ID": [100.0, 100.0, 100.0, 100.0, 200.0, 300.0, 300.0, nan],
    })


def test_rfm_table(nb):
    tx = tiny_tx()
    before = tx.copy()
    out = nb.rfm_table(tx, SNAPSHOT)
    pd.testing.assert_frame_equal(tx, before)
    assert list(out.columns) == ["recency", "frequency", "monetary"]
    assert sorted(out.index) == [100.0, 200.0, 300.0]                 # khách trống bị bỏ
    assert out.loc[100.0].tolist() == pytest.approx([8, 2, 25.0])      # C3 bị bỏ; lần cuối 2011-12-01
    assert out.loc[200.0].tolist() == pytest.approx([0, 1, 6.0])       # 12:50 ngày 09/12 → 0 ngày trọn
    assert out.loc[300.0].tolist() == pytest.approx([191, 1, 4.0])     # dòng giá 0 ngày 09/12 bị bỏ; 08:00 nên thiếu 1 ngày trọn


def test_prepare_features(nb):
    rfm = pd.DataFrame({"recency": [0, 10, 100], "frequency": [1, 3, 9], "monetary": [10.0, 100.0, 1000.0]},
                       index=[7, 8, 9])
    out = nb.prepare_features(rfm)
    assert list(out.columns) == ["recency", "frequency", "monetary"] and list(out.index) == [7, 8, 9]
    assert out.mean().abs().max() < 1e-12
    assert out.std(ddof=0).tolist() == pytest.approx([1, 1, 1])
    z = np.log1p(rfm["monetary"])
    assert out["monetary"].tolist() == pytest.approx(((z - z.mean()) / z.std(ddof=0)).tolist())


def test_fit_kmeans(nb):
    rng = np.random.default_rng(0)
    Z = pd.DataFrame(np.vstack([rng.normal(-5, 0.3, (30, 2)), rng.normal(5, 0.3, (20, 2))]), columns=["a", "b"])
    labels = np.asarray(nb.fit_kmeans(Z, 2))
    assert len(labels) == 50 and len(set(labels[:30])) == 1 and len(set(labels[30:])) == 1
    assert labels[0] != labels[-1]


def test_segment_profile(nb):
    rfm = pd.DataFrame({"recency": [5, 15, 100, 200, 300], "frequency": [10, 6, 2, 1, 1],
                        "monetary": [1000.0, 600.0, 200.0, 100.0, 100.0]})
    out = nb.segment_profile(rfm, [1, 1, 0, 0, 0])
    assert list(out.columns) == ["n", "share", "recency_median", "frequency_median", "monetary_median", "revenue_share"]
    assert out.index.name == "segment" and list(out.index) == [1, 0]   # sắp monetary_median giảm dần
    assert out.loc[1].tolist() == pytest.approx([2, 0.4, 10, 8, 800, 0.8])
    assert out.loc[0].tolist() == pytest.approx([3, 0.6, 200, 1, 100, 0.2])


def test_name_segments(nb):
    rfm = pd.DataFrame({"recency": [10, 20, 30, 40, 50], "frequency": [1, 2, 3, 4, 5], "monetary": [1.0] * 5})
    # median chung: recency 30, frequency 3
    profile = pd.DataFrame({"recency_median": [30, 31, 10, 90], "frequency_median": [4, 4, 3, 1]},
                           index=pd.Index([2, 0, 3, 1], name="segment"))
    out = nb.name_segments(profile, rfm)
    assert out.name == "name" and list(out.index) == [2, 0, 3, 1]
    assert out.tolist() == ["Champions", "At risk", "New / promising", "Hibernating"]


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


def test_real_rfm(nb, retail):
    rfm = nb.rfm_table(retail, SNAPSHOT)
    assert len(rfm) == 4338
    assert rfm.loc[14646.0, "monetary"] == pytest.approx(280_206.02, abs=0.01)
    assert rfm.median().tolist() == pytest.approx([50, 2, 674.485])
    assert rfm["recency"].min() == 0 and rfm["frequency"].max() == 209


def test_real_segments(nb, retail):
    rfm = nb.rfm_table(retail, SNAPSHOT)
    profile = nb.segment_profile(rfm, nb.fit_kmeans(nb.prepare_features(rfm), 4))
    names = nb.name_segments(profile, rfm)
    expected = ["Champions", "At risk", "New / promising", "Hibernating"]
    assert sorted(names) == sorted(expected), f"Cần đúng bốn tên, mỗi cụm một tên; nhận {names.tolist()}"
    assert names.tolist() == expected, (
        f"Đủ bốn tên nhưng sai thứ tự {names.tolist()}: segment_profile phải sắp monetary_median giảm dần"
    )
    assert profile["n"].tolist() == pytest.approx([713, 1187, 812, 1626], abs=20)
    assert profile["revenue_share"].iloc[0] == pytest.approx(0.647, abs=0.01)
