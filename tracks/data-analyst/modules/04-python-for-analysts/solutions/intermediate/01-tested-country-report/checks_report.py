"""Test của người học cho report.py (lời giải mẫu). Mỗi test khoá một định nghĩa."""

import numpy as np
import pandas as pd
import pytest

from report import clean_transactions, compare_periods, country_summary


def make_tx(rows):
    """rows: list of (Invoice, ngày, Quantity, Price, Customer ID, Country)."""
    return pd.DataFrame(rows, columns=["Invoice", "InvoiceDate", "Quantity", "Price", "Customer ID", "Country"]).assign(
        InvoiceDate=lambda d: pd.to_datetime(d["InvoiceDate"], format="ISO8601"))


def test_aov_is_revenue_per_invoice():
    tx = make_tx([
        (1, "2011-01-03", 1, 10.0, 7.0, "France"),
        (1, "2011-01-03", 2, 10.0, 7.0, "France"),
        (2, "2011-01-04", 1, 10.0, 8.0, "France"),
    ])
    out = country_summary(tx, "2011-01-01", "2011-02-01")
    assert out.loc["France", "aov"] == pytest.approx(20.0)


def test_cancellations_and_bad_rows_are_dropped():
    tx = make_tx([
        (1, "2011-01-03", 2, 5.0, 7.0, "France"),
        ("C2", "2011-01-04", -2, 5.0, 7.0, "France"),     # huỷ
        (3, "2011-01-05", 3, 0.0, 7.0, "France"),         # giá 0
        (4, "2011-01-06", -1, 4.0, 7.0, "France"),        # số lượng âm
    ])
    sales = clean_transactions(tx)
    assert sales["Invoice"].tolist() == ["1"]
    assert sales["revenue"].tolist() == [10.0]
    assert country_summary(tx, "2011-01-01", "2011-02-01").loc["France", "revenue"] == pytest.approx(10.0)


def test_orders_and_customers_are_distinct_counts():
    tx = make_tx([
        (1, "2011-01-03", 1, 10.0, 7.0, "Spain"),
        (1, "2011-01-03", 1, 10.0, 7.0, "Spain"),
        (2, "2011-01-04", 1, 10.0, 7.0, "Spain"),
        (3, "2011-01-05", 1, 10.0, np.nan, "Spain"),
    ])
    out = country_summary(tx, "2011-01-01", "2011-02-01")
    assert out.loc["Spain", "orders"] == 3
    assert out.loc["Spain", "customers"] == 1


def test_period_is_half_open():
    tx = make_tx([
        (1, "2011-01-31 23:59", 1, 10.0, 7.0, "Spain"),
        (2, "2011-02-01 00:00", 1, 99.0, 7.0, "Spain"),
    ])
    assert country_summary(tx, "2011-01-01", "2011-02-01").loc["Spain", "revenue"] == pytest.approx(10.0)


def test_compare_keeps_new_and_lost_countries():
    tx = make_tx([
        (1, "2011-01-03", 1, 10.0, 7.0, "Spain"),     # chỉ kỳ trước
        (2, "2011-01-04", 1, 20.0, 8.0, "France"),
        (3, "2011-02-03", 1, 30.0, 8.0, "France"),
        (4, "2011-02-04", 1, 40.0, 9.0, "Japan"),     # chỉ kỳ này
    ])
    out = compare_periods(tx, current=("2011-02-01", "2011-03-01"), previous=("2011-01-01", "2011-02-01"))
    assert set(out.index) == {"Spain", "France", "Japan"}
    assert out.loc["Spain", ["revenue", "revenue_prev", "status"]].tolist() == [0.0, 10.0, "lost"]
    assert out.loc["Japan", "status"] == "new" and np.isnan(out.loc["Japan", "growth"])
    assert out.loc["France", "growth"] == pytest.approx(0.5)
    assert out.loc["France", "change"] == pytest.approx(10.0)


def test_top_other_keeps_total():
    tx = make_tx([(i, "2011-02-03", 1, float(10 * (i + 1)), float(i), c)
                  for i, c in enumerate(["A", "B", "C", "D"])])
    out = compare_periods(tx, current=("2011-02-01", "2011-03-01"), previous=("2011-01-01", "2011-02-01"), top=2)
    assert list(out.index) == ["D", "C", "Other"]
    assert out.loc["Other", "revenue"] == pytest.approx(30.0)
    assert out["revenue"].sum() == pytest.approx(100.0)
