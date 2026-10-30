import duckdb
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
FLAGS = ["total_price_zero", "one_line_per_transaction", "uniform_quantity", "flat_hours", "poisson_like_daily"]
COLUMNS = ("{'SalesID': 'BIGINT', 'SalesPersonID': 'INTEGER', 'CustomerID': 'INTEGER', 'ProductID': 'INTEGER', "
           "'Quantity': 'INTEGER', 'Discount': 'DOUBLE', 'TotalPrice': 'DOUBLE', 'SalesDate': 'TIMESTAMP', "
           "'TransactionNumber': 'VARCHAR'}")


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("grocery_suspicion.ipynb")


def small_con(table="sales"):
    df = pd.DataFrame({
        "SalesID": range(1, 9),
        "SalesPersonID": [1, 2, 1, 3, 2, 1, 3, 2],
        "CustomerID": [10, 11, 10, 12, 13, 14, 10, 11],
        "ProductID": [100, 101, 102, 100, 103, 104, 101, 100],
        "Quantity": [1, 9, 3, 2, 2, 5, 1, 4],
        "Discount": [0.0, 0.1, 0.0, 0.0, 0.2, 0.0, 0.0, 0.0],
        "TotalPrice": [0.0, 0.0, 12.5, 0.0, 0.0, 7.0, 0.0, 0.0],
        "SalesDate": pd.to_datetime(["2018-01-01 08:15", "2018-01-01 08:15", "2018-01-01 17:40", None,
                                     "2018-01-02 03:05", "2018-01-02 17:59", "2018-01-03 08:00", "2018-01-03 12:30"]),
        "TransactionNumber": ["A", "A", "B", "C", "D", "E", "F", "G"],
    })
    con = duckdb.connect()
    con.register("fixture_df", df)
    con.execute(f"CREATE TABLE {table} AS SELECT * FROM fixture_df")
    con.unregister("fixture_df")
    return con


def test_sales_profile(nb):
    out = nb.sales_profile(small_con())
    assert out == {
        "rows": 8, "transactions": 7, "max_lines_per_transaction": 2,
        "total_price_zero_share": pytest.approx(0.75), "missing_date_share": pytest.approx(0.125),
        "quantity_min": 1, "quantity_max": 9,
    }
    for key in ["rows", "transactions", "max_lines_per_transaction", "quantity_min", "quantity_max"]:
        assert isinstance(out[key], int), key
    for key in ["total_price_zero_share", "missing_date_share"]:
        assert isinstance(out[key], float), key


def test_sales_profile_other_table(nb):
    assert nb.sales_profile(small_con("orders"), table="orders")["rows"] == 8


def test_count_by(nb):
    con = small_con()
    q = nb.count_by(con, "Quantity")
    assert isinstance(q, pd.Series)
    assert list(q.index) == [1, 2, 3, 4, 5, 9]
    assert q.tolist() == [2, 2, 1, 1, 1, 1]
    h = nb.count_by(con, "hour(SalesDate)")                       # bỏ khoá NULL (dòng thiếu ngày)
    assert list(h.index) == [3, 8, 12, 17] and h.tolist() == [1, 3, 1, 2]
    d = nb.count_by(con, "CAST(SalesDate AS DATE)")
    assert d.tolist() == [3, 2, 2]


def test_uniformity_test(nb):
    flat = nb.uniformity_test(pd.Series([10, 10, 10, 10]))
    assert set(flat) == {"chi2", "p_value", "max_min_ratio"}
    assert flat["chi2"] == pytest.approx(0.0) and flat["p_value"] == pytest.approx(1.0)
    assert flat["max_min_ratio"] == pytest.approx(1.0)
    skew = nb.uniformity_test(pd.Series([5, 15]))
    assert skew["chi2"] == pytest.approx(5.0)
    assert skew["p_value"] == pytest.approx(0.025347, abs=1e-6)
    assert skew["max_min_ratio"] == pytest.approx(3.0)
    assert all(isinstance(v, float) for v in skew.values())


def test_dispersion_index(nb):
    assert nb.dispersion_index(pd.Series([10, 12, 8, 10])) == pytest.approx(8 / 3 / 10)
    assert isinstance(nb.dispersion_index(pd.Series([1, 2, 3])), float)


def profile(**kw):
    base = {"rows": 100, "transactions": 40, "max_lines_per_transaction": 12, "total_price_zero_share": 0.0,
            "missing_date_share": 0.0, "quantity_min": 1, "quantity_max": 48}
    return {**base, **kw}


def test_red_flags_real_looking(nb):
    q = {"chi2": 900.0, "p_value": 0.0, "max_min_ratio": 40.0}
    h = {"chi2": 5000.0, "p_value": 0.0, "max_min_ratio": 95.0}
    assert nb.red_flags(profile(), q, h, daily_dispersion=380.0) == []


def test_red_flags_each_rule(nb):
    q_ok = {"chi2": 900.0, "p_value": 0.0, "max_min_ratio": 40.0}
    h_ok = {"chi2": 5000.0, "p_value": 0.0, "max_min_ratio": 95.0}
    assert nb.red_flags(profile(total_price_zero_share=0.995), q_ok, h_ok, 380.0) == ["total_price_zero"]
    assert nb.red_flags(profile(total_price_zero_share=0.99), q_ok, h_ok, 380.0) == []      # > 0.99, không phải >=
    assert nb.red_flags(profile(max_lines_per_transaction=1), q_ok, h_ok, 380.0) == ["one_line_per_transaction"]
    assert nb.red_flags(profile(), {**q_ok, "p_value": 0.2}, h_ok, 380.0) == ["uniform_quantity"]
    assert nb.red_flags(profile(), q_ok, {**h_ok, "max_min_ratio": 1.05}, 380.0) == ["flat_hours"]
    assert nb.red_flags(profile(), q_ok, h_ok, 1.4) == ["poisson_like_daily"]


def test_red_flags_order(nb):
    q = {"chi2": 20.0, "p_value": 0.6, "max_min_ratio": 1.01}
    h = {"chi2": 15.0, "p_value": 0.9, "max_min_ratio": 1.01}
    out = nb.red_flags(profile(total_price_zero_share=1.0, max_lines_per_transaction=1), q, h, 0.9)
    assert out == FLAGS


@pytest.fixture(scope="module")
def real_con():
    path = ex.dataset("grocery-sales-synthetic") / "sales.csv"
    con = duckdb.connect()
    con.execute("SET memory_limit = '1GB'")                     # máy 4 GB RAM vẫn chạy được
    con.execute(f"CREATE VIEW sales AS SELECT * FROM read_csv('{path}', header = true, columns = {COLUMNS})")
    return con


def test_real_profile(nb, real_con):
    out = nb.sales_profile(real_con)
    assert out["rows"] == 6_758_125
    assert out["transactions"] == 6_758_125
    assert out["max_lines_per_transaction"] == 1
    assert out["total_price_zero_share"] == pytest.approx(1.0)
    assert out["missing_date_share"] == pytest.approx(67_526 / 6_758_125)
    assert (out["quantity_min"], out["quantity_max"]) == (1, 25)


def test_real_tests_and_flags(nb, real_con):
    q = nb.uniformity_test(nb.count_by(real_con, "Quantity"))
    assert q["chi2"] == pytest.approx(23.19, abs=0.01) and q["p_value"] == pytest.approx(0.509, abs=0.001)
    h = nb.uniformity_test(nb.count_by(real_con, "hour(SalesDate)"))
    assert h["p_value"] == pytest.approx(0.860, abs=0.001) and h["max_min_ratio"] == pytest.approx(1.0059, abs=1e-4)
    daily = nb.dispersion_index(nb.count_by(real_con, "CAST(SalesDate AS DATE)"))
    assert daily == pytest.approx(0.916, abs=0.001)
    assert nb.red_flags(nb.sales_profile(real_con), q, h, daily) == FLAGS
