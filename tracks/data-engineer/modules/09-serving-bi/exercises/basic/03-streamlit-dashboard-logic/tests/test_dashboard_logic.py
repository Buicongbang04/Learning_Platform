import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture
def logic():
    return ex.module("dashboard_logic.py")


@pytest.fixture
def df():
    return pd.DataFrame({
        "order_id":       ["o1", "o1", "o2", "o3", "o3", "o4", "o5"],
        "order_date":     pd.to_datetime(["2018-08-01", "2018-08-01", "2018-08-01", "2018-08-02",
                                          "2018-08-02", "2018-08-04", "2018-08-04"]),
        "customer_state": ["SP", "SP", "SP", "RJ", "RJ", "MG", "SP"],
        "order_status":   ["delivered", "delivered", "delivered", "delivered", "delivered", "shipped", "delivered"],
        "price":          [100.0, 50.0, 100.0, 200.0, 200.0, 30.0, 49.99],
        "is_late":        [False, False, True, True, True, False, False],
    })


def test_filter_orders(logic, df):
    out = logic.filter_orders(df, "2018-08-01", "2018-08-02")
    assert sorted(out["order_id"].unique()) == ["o1", "o2", "o3"]
    assert list(out.index) == list(range(len(out)))
    out = logic.filter_orders(df, pd.Timestamp("2018-08-01").date(), "2018-08-04", ["SP"])
    assert sorted(out["order_id"].unique()) == ["o1", "o2", "o5"]
    assert len(logic.filter_orders(df, "2018-08-01", "2018-08-04", [])) == len(df)
    assert len(df) == 7  # không sửa df gốc


def test_compute_kpis_by_order_not_item(logic, df):
    k = logic.compute_kpis(df)
    assert k["orders"] == 5
    assert k["revenue"] == pytest.approx(729.99)
    assert k["aov"] == pytest.approx(146.0)
    # 4 đơn delivered (o1, o2, o3, o5), trễ o2, o3 -> 0.5 (tính theo item sẽ ra 3/6)
    assert k["late_rate"] == pytest.approx(0.5)


def test_compute_kpis_empty(logic, df):
    k = logic.compute_kpis(df.iloc[0:0])
    assert k == {"orders": 0, "revenue": 0.0, "aov": 0.0, "late_rate": None}
    only_shipped = df[df["order_status"] == "shipped"]
    assert logic.compute_kpis(only_shipped)["late_rate"] is None


def test_pct_change(logic):
    assert logic.pct_change(110, 100) == 10.0
    assert logic.pct_change(50, 200) == -75.0
    assert logic.pct_change(1, 3) == -66.7
    assert logic.pct_change(5, 0) is None
    assert logic.pct_change(5, None) is None
    assert logic.pct_change(-5, -10) == 50.0


def test_daily_series_fills_gaps(logic, df):
    s = logic.daily_series(df, "2018-07-31", "2018-08-04")
    assert list(s.columns) == ["order_date", "orders", "revenue"]
    assert [d.strftime("%Y-%m-%d") for d in s["order_date"]] == [
        "2018-07-31", "2018-08-01", "2018-08-02", "2018-08-03", "2018-08-04"]
    assert s["orders"].tolist() == [0, 2, 1, 0, 2]
    assert s["revenue"].round(2).tolist() == [0.0, 250.0, 400.0, 0.0, 79.99]
    assert list(s.index) == list(range(5))


def test_format_brl(logic):
    assert logic.format_brl(1234.5) == "R$ 1.234,50"
    assert logic.format_brl(0) == "R$ 0,00"
    assert logic.format_brl(1234567.891) == "R$ 1.234.567,89"
    assert logic.format_brl(-1234.5) == "-R$ 1.234,50"
    assert logic.format_brl(None) == "n/a"


def test_kpi_status(logic):
    assert logic.kpi_status(None, 0.05) == "unknown"
    assert logic.kpi_status(120, 100) == "ok"
    assert logic.kpi_status(95, 100) == "warn"
    assert logic.kpi_status(80, 100) == "bad"
    assert logic.kpi_status(0.04, 0.05, higher_is_better=False) == "ok"
    assert logic.kpi_status(0.054, 0.05, higher_is_better=False) == "warn"
    assert logic.kpi_status(0.08, 0.05, higher_is_better=False) == "bad"
