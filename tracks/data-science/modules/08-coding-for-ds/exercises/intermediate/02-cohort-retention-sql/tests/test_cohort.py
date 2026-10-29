import duckdb
import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)

T = pd.Timestamp
NaT = pd.NaT
CUSTOMERS = pd.DataFrame({
    "customer_id": ["c1a", "c1b", "c1c", "c2a", "c2b", "c3a", "c3b", "c4a", "c4b", "c5a", "c6a"],
    "customer_unique_id": ["u1", "u1", "u1", "u2", "u2", "u3", "u3", "u4", "u4", "u5", "u6"],
})
# Mỗi đơn có customer_id riêng (như Olist): phải gộp khách bằng customer_unique_id
ORDERS = pd.DataFrame(
    [
        ("o1", "c1a", "delivered", T("2018-01-05"), T("2018-01-10")),
        ("o2", "c1b", "delivered", T("2018-02-10"), T("2018-02-15")),
        ("o3", "c1c", "delivered", T("2018-02-20"), T("2018-02-25")),   # cùng tháng với o2: đếm khách một lần
        ("o4", "c2a", "delivered", T("2018-01-15"), T("2018-01-20")),
        ("o5", "c2b", "canceled", T("2018-03-01"), NaT),                # huỷ: không tính
        ("o6", "c3a", "delivered", T("2018-02-03"), T("2018-02-08")),
        ("o7", "c3b", "delivered", T("2018-04-01"), T("2018-04-06")),
        ("o8", "c4a", "delivered", T("2018-02-28"), T("2018-03-05")),
        ("o9", "c4b", "delivered", T("2018-09-02"), T("2018-09-08")),   # sau 2018-08-31: bỏ
        ("o10", "c5a", "delivered", T("2018-03-10"), NaT),              # thiếu ngày giao: chưa giao xong
        ("o11", "c6a", "delivered", T("2018-03-15"), T("2018-03-20")),
    ],
    columns=["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_delivered_customer_date"],
)

EXPECTED_COUNTS = pd.DataFrame({
    "cohort": pd.to_datetime(["2018-01-01", "2018-01-01", "2018-02-01", "2018-02-01", "2018-03-01"]),
    "month_index": [0, 1, 0, 2, 0],
    "customers": [2, 1, 2, 1, 1],
})


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("cohort.ipynb")


def fixture_con():
    con = duckdb.connect()
    con.register("orders_df", ORDERS)
    con.register("customers_df", CUSTOMERS)
    con.execute("CREATE TABLE orders AS SELECT * FROM orders_df")
    con.execute("CREATE TABLE customers AS SELECT * FROM customers_df")
    return con


def test_cohort_counts(nb):
    out = nb.cohort_counts(fixture_con())
    assert list(out.columns) == ["cohort", "month_index", "customers"]
    out = out.sort_values(["cohort", "month_index"]).reset_index(drop=True)
    assert pd.to_datetime(out["cohort"]).tolist() == EXPECTED_COUNTS["cohort"].tolist()
    assert out["month_index"].astype(int).tolist() == [0, 1, 0, 2, 0]
    assert out["customers"].astype(int).tolist() == [2, 1, 2, 1, 1]


def test_retention_matrix_zero_vs_unobserved(nb):
    mat = nb.retention_matrix(EXPECTED_COUNTS, "2018-04-01")
    assert list(mat.columns) == [0, 1, 2, 3]
    assert list(pd.to_datetime(mat.index)) == list(pd.to_datetime(["2018-01-01", "2018-02-01", "2018-03-01"]))
    expected = np.array([
        [1.0, 0.5, 0.0, 0.0],              # 0.0: đã quan sát được tháng đó, không ai quay lại
        [1.0, 0.0, 0.5, np.nan],           # NaN: 2018-02 + 3 tháng = 2018-05, chưa có dữ liệu
        [1.0, 0.0, np.nan, np.nan],
    ])
    np.testing.assert_allclose(mat.to_numpy(dtype=float), expected, equal_nan=True)


def test_average_retention_only_uses_observed_cohorts(nb):
    assert nb.average_retention(EXPECTED_COUNTS, 1, "2018-04-01") == pytest.approx(1 / 5)
    assert nb.average_retention(EXPECTED_COUNTS, 2, "2018-04-01") == pytest.approx(1 / 4)
    assert nb.average_retention(EXPECTED_COUNTS, 3, "2018-04-01") == pytest.approx(0.0)


def test_average_retention_is_weighted_by_cohort_size(nb):
    counts = pd.DataFrame({
        "cohort": pd.to_datetime(["2018-01-01", "2018-01-01", "2018-02-01", "2018-02-01"]),
        "month_index": [0, 1, 0, 1],
        "customers": [100, 10, 900, 9],
    })
    # trung bình có trọng số: 19 / 1000, không phải (10% + 1%) / 2
    assert nb.average_retention(counts, 1, "2018-03-01") == pytest.approx(0.019)


def test_repeat_customer_rate(nb):
    # u1 (3 đơn), u3 (2 đơn) mua lại; u2, u4, u6 chỉ 1 đơn giao xong trong khoảng; u5 không có đơn giao xong
    assert nb.repeat_customer_rate(fixture_con()) == pytest.approx(2 / 5)


def test_real_olist(nb):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    con = duckdb.connect()
    for table in ["orders", "customers"]:
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_csv_auto('{raw / f'olist_{table}_dataset.csv'}')")
    counts = nb.cohort_counts(con)
    counts["cohort"] = pd.to_datetime(counts["cohort"])
    assert counts.loc[counts.month_index == 0, "customers"].sum() == 93350
    nov = counts[counts.cohort == "2017-11-01"].set_index("month_index")["customers"]
    assert nov[0] == 7059 and nov[1] == 40
    assert nb.average_retention(counts, 1, "2018-08-01") == pytest.approx(0.004828, abs=2e-5)
    assert nb.repeat_customer_rate(con) == pytest.approx(0.0300, abs=1e-4)
