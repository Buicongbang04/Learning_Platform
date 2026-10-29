import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)
RAW = ROOT / "data" / "raw"

COLUMNS = ["dtype", "n_missing", "missing_rate", "n_unique", "top_value", "top_share"]

DF = pd.DataFrame({
    "order_id": ["a", "b", "c", "d", "e"],
    "status": ["delivered", "delivered", "canceled", None, "delivered"],
    "price": [10.0, np.nan, np.nan, 30.0, 10.0],
    "empty": [np.nan] * 5,
})


@pytest.fixture(scope="module")
def prof():
    return ex.module("profile.py")


def test_profile_shape_and_order(prof):
    out = prof.profile(DF)
    assert list(out.index) == list(DF.columns)
    assert list(out.columns) == COLUMNS


def test_profile_missing(prof):
    out = prof.profile(DF)
    assert out.loc["status", "n_missing"] == 1
    assert out.loc["price", "n_missing"] == 2
    assert out.loc["price", "missing_rate"] == pytest.approx(0.4)
    assert out.loc["empty", "missing_rate"] == pytest.approx(1.0)
    assert out.loc["order_id", "missing_rate"] == 0


def test_profile_unique_and_top(prof):
    out = prof.profile(DF)
    assert out.loc["status", "n_unique"] == 2              # NaN không phải một giá trị
    assert out.loc["status", "top_value"] == "delivered"
    assert out.loc["status", "top_share"] == pytest.approx(3 / 4)   # trên 4 ô không thiếu
    assert out.loc["price", "top_value"] == 10.0
    assert out.loc["price", "top_share"] == pytest.approx(2 / 3)
    assert out.loc["order_id", "n_unique"] == 5


def test_profile_all_missing_column(prof):
    out = prof.profile(DF)
    assert out.loc["empty", "n_unique"] == 0
    assert out.loc["empty", "top_value"] is None or pd.isna(out.loc["empty", "top_value"])
    assert pd.isna(out.loc["empty", "top_share"])


def test_profile_dtype_is_string(prof):
    out = prof.profile(DF)
    assert out.loc["price", "dtype"] == "float64"
    assert all(isinstance(v, str) for v in out["dtype"])


REVIEWS = pd.DataFrame({
    "review_id": ["r1", "r2", "r2", "r3", "r4", "r4"],
    "order_id": ["o1", "o2", "o3", "o3", "o4", "o4"],
    "review_score": [5, 1, 1, 2, 4, 4],
})


def test_duplicate_report_single_key(prof):
    out = prof.duplicate_report(REVIEWS, ["review_id"])
    assert out == {"n_rows": 6, "n_unique_keys": 4, "n_rows_dup_key": 4, "n_exact_duplicates": 1}


def test_duplicate_report_composite_key(prof):
    out = prof.duplicate_report(REVIEWS, ["review_id", "order_id"])
    assert out["n_unique_keys"] == 5
    assert out["n_rows_dup_key"] == 2          # chỉ cặp (r4, o4) lặp
    out = prof.duplicate_report(REVIEWS, ["order_id"])
    assert out["n_unique_keys"] == 4 and out["n_rows_dup_key"] == 4


def test_iqr_outliers_basic(prof):
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 100, np.nan], index=list("abcdefghij"))
    mask = prof.iqr_outliers(s)
    assert list(mask.index) == list(s.index)
    assert mask.dtype == bool
    assert mask.tolist() == [False] * 8 + [True, False]


def test_iqr_outliers_k_and_lower_tail(prof):
    s = pd.Series([-50.0, 10, 11, 12, 13, 14, 15, 30])
    # Q1 = 10.75, Q3 = 14.25, IQR = 3.5
    assert prof.iqr_outliers(s).tolist() == [True, False, False, False, False, False, False, True]
    assert prof.iqr_outliers(s, k=5).tolist() == [True] + [False] * 7      # 30 < 14.25 + 17.5


def test_iqr_flags_about_one_percent_of_normal(prof):
    rng = np.random.default_rng(0)
    s = pd.Series(rng.normal(size=200_000))
    assert prof.iqr_outliers(s).mean() == pytest.approx(0.007, abs=0.0015)   # lý thuyết 0.70%


def test_real_olist_reviews(prof):
    path = RAW / "olist_order_reviews_dataset.csv"
    if not path.exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    reviews = pd.read_csv(path)
    assert prof.duplicate_report(reviews, ["review_id"]) == {
        "n_rows": 99224, "n_unique_keys": 98410, "n_rows_dup_key": 1603, "n_exact_duplicates": 0}
    assert prof.duplicate_report(reviews, ["review_id", "order_id"])["n_rows_dup_key"] == 0
    out = prof.profile(reviews)
    assert out.loc["review_comment_message", "missing_rate"] == pytest.approx(0.587, abs=0.001)


def test_real_olist_price_outliers(prof):
    path = RAW / "olist_order_items_dataset.csv"
    if not path.exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    price = pd.read_csv(path).price
    assert prof.iqr_outliers(price).sum() == 8427
