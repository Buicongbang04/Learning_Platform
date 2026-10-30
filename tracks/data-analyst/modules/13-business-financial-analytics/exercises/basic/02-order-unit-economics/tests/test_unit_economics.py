import os
import tempfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)
A = {"cogs_rate": 0.60, "payment_fee_rate": 0.02, "cost_per_order": 8.0, "cost_per_line": 0.25}


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("unit_economics.ipynb")


def tiny_tx():
    # Invoice trộn int và str như khi đọc từ Excel; một hoá đơn huỷ, một dòng giá 0, một dòng số lượng âm
    return pd.DataFrame({
        "Invoice": [1001, 1001, 1001, "1002", "C1003", 1004, 1004, 1005],
        "StockCode": ["A", "B", "POST", "A", "A", "C", "D", "E"],
        "Quantity": [10, 4, 1, 2, -2, 5, -1, 100],
        "Price": [2.0, 5.0, 15.0, 2.0, 2.0, 4.0, 4.0, 0.0],
        "InvoiceDate": pd.to_datetime(["2011-01-03"] * 8),
        "Customer ID": [1.0, 1.0, 1.0, np.nan, 2.0, 3.0, 3.0, 4.0],
        "Country": ["United Kingdom", "United Kingdom", "United Kingdom", "France", "France", "Germany", "Germany",
                    "Spain"],
    })


def test_order_table(nb):
    tx = tiny_tx()
    before = tx.copy()
    out = nb.order_table(tx)
    pd.testing.assert_frame_equal(tx, before)
    assert list(out.columns) == ["revenue", "lines", "country", "customer_id"]
    assert out.index.name == "Invoice"
    assert list(out.index) == ["1001", "1002", "1004"]
    assert out["revenue"].tolist() == pytest.approx([55.0, 4.0, 20.0])
    assert out["lines"].tolist() == [3, 1, 1]
    assert out["country"].tolist() == ["United Kingdom", "France", "Germany"]
    assert out.loc["1001", "customer_id"] == 1.0 and np.isnan(out.loc["1002", "customer_id"])


def orders():
    return pd.DataFrame({"revenue": [100.0, 20.0, 500.0], "lines": [4, 1, 20], "country": ["UK", "UK", "FR"],
                         "customer_id": [1.0, 2.0, np.nan]},
                        index=pd.Index(["a", "b", "c"], name="Invoice"))


def test_unit_economics(nb):
    o = orders()
    before = o.copy()
    ue = nb.unit_economics(o, A)
    pd.testing.assert_frame_equal(o, before)
    for col in ["revenue", "lines", "cogs", "fees", "fulfilment", "contribution"]:
        assert col in ue.columns
    # đơn a: 100 - 60 - 2 - (8 + 1) = 29; đơn b: 20 - 12 - 0.4 - 8.25 = -0.65; đơn c: 500 - 300 - 10 - 13 = 177
    assert ue["contribution"].tolist() == pytest.approx([29.0, -0.65, 177.0])
    assert ue["fulfilment"].tolist() == pytest.approx([9.0, 8.25, 13.0])


def test_unit_economics_price_change_keeps_cogs(nb):
    ue = nb.unit_economics(orders(), A, price_change=0.10)
    assert ue["revenue"].tolist() == pytest.approx([110.0, 22.0, 550.0])
    assert ue["cogs"].tolist() == pytest.approx([60.0, 12.0, 300.0])
    assert ue["fees"].tolist() == pytest.approx([2.2, 0.44, 11.0])
    assert ue["contribution"].tolist() == pytest.approx([38.8, 1.31, 226.0])


def test_pnl(nb):
    ue = nb.unit_economics(orders(), A)
    p = nb.pnl(ue)
    assert p.name == "pnl"
    assert list(p.index) == ["revenue", "cogs", "gross_profit", "gross_margin", "fees", "fulfilment", "contribution",
                             "contribution_margin", "orders", "contribution_per_order"]
    assert p["revenue"] == pytest.approx(620.0)
    assert p["gross_profit"] == pytest.approx(248.0)
    assert p["gross_margin"] == pytest.approx(0.4)
    assert p["contribution"] == pytest.approx(205.35)
    assert p["contribution_margin"] == pytest.approx(205.35 / 620)
    assert p["orders"] == pytest.approx(3)
    assert p["contribution_per_order"] == pytest.approx(205.35 / 3)
    q = nb.pnl(ue, volume_change=-0.5)
    assert q["revenue"] == pytest.approx(310.0) and q["orders"] == pytest.approx(1.5)
    assert q["contribution_margin"] == pytest.approx(p["contribution_margin"])
    assert q["contribution_per_order"] == pytest.approx(p["contribution_per_order"])


def test_breakeven_order_value(nb):
    assert nb.breakeven_order_value(15, A) == pytest.approx(11.75 / 0.38)
    assert nb.breakeven_order_value(0, {**A, "cogs_rate": 0.5, "payment_fee_rate": 0.0}) == pytest.approx(16.0)


def test_scenario_table(nb):
    o = orders()
    scenarios = {
        "price": {"price_change": 0.10, "volume_change": -0.10},
        "min": {"min_order_value": 25},
        "cogs": {"cogs_rate": 0.65},
    }
    out = nb.scenario_table(o, A, scenarios)
    assert list(out.index) == ["base", "price", "min", "cogs"]
    assert list(out.columns) == ["revenue", "contribution", "contribution_margin", "orders", "delta_contribution"]
    assert out["contribution"].tolist() == pytest.approx([205.35, 0.9 * 266.11, 206.0, 174.35])
    assert out["orders"].tolist() == pytest.approx([3, 2.7, 2, 3])
    assert out["revenue"].tolist() == pytest.approx([620.0, 0.9 * 682.0, 600.0, 620.0])
    assert out.loc["base", "delta_contribution"] == pytest.approx(0.0)
    assert out.loc["cogs", "delta_contribution"] == pytest.approx(-31.0)
    # ngưỡng tính trên doanh thu sau khi đổi giá: +30% đưa đơn b lên 26, không bị bỏ
    mixed = nb.scenario_table(o, A, {"x": {"price_change": 0.30, "min_order_value": 25}})
    assert mixed.loc["x", "orders"] == pytest.approx(3)


def test_breakeven_volume_change(nb):
    # contribution hiện tại 205.35; giá +10%: 266.11
    assert nb.breakeven_volume_change(orders(), A, 0.10) == pytest.approx(205.35 / 266.11 - 1)


# Đọc xlsx bằng pandas mất 30-90 giây mỗi sheet: đọc bằng extension excel của DuckDB (khoảng 7 giây, cho kết quả
# giống hệt pandas), máy không cài được extension thì quay về pandas. Kết quả cache parquet trong thư mục tạm của hệ
# điều hành (không ghi vào data/raw), khoá theo mtime + size của tệp xlsx, ghi atomic. Cache giữ dữ liệu gốc của
# sheet (chưa làm sạch); Invoice, StockCode, Description ép str. Cùng tên tệp cache với notebook.
CACHE_DIR = Path(tempfile.gettempdir()) / "da-cache"


def _excel_extension_missing(exc: Exception) -> bool:
    kinds = (duckdb.CatalogException, duckdb.IOException, duckdb.HTTPException)
    return isinstance(exc, kinds) and "extension" in str(exc).lower()


def read_retail_sheet(sheet: str = "Year 2010-2011") -> pd.DataFrame:
    xlsx = ex.dataset("online-retail-ii") / "online_retail_II.xlsx"
    stat = xlsx.stat()
    cache = CACHE_DIR / f"online_retail_II-{sheet.replace(' ', '_')}-{stat.st_mtime_ns}-{stat.st_size}.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    path = str(xlsx).replace("'", "''")
    try:
        tx = duckdb.sql(f"""
            SELECT Invoice, StockCode, Description, CAST(CAST(Quantity AS DOUBLE) AS BIGINT) AS Quantity,
                   TIMESTAMP '1899-12-30' + to_seconds(CAST(round(CAST(InvoiceDate AS DOUBLE) * 86400) AS BIGINT))
                       AS InvoiceDate,
                   CAST(Price AS DOUBLE) AS Price, CAST("Customer ID" AS DOUBLE) AS "Customer ID", Country
            FROM read_xlsx('{path}', sheet = '{sheet}', all_varchar = true)""").df()
    except duckdb.Error as exc:
        if not _excel_extension_missing(exc):
            raise
        tx = pd.read_excel(xlsx, sheet_name=sheet)
    tx = tx.assign(Invoice=tx["Invoice"].astype(str), StockCode=tx["StockCode"].astype(str),
                   Description=tx["Description"].astype("string"))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_name(f"{cache.name}.{os.getpid()}.tmp")
    tx.to_parquet(tmp, index=False)
    os.replace(tmp, cache)
    return tx


_ORDERS = {}


def real_orders(nb):
    """Bảng đơn tính một lần; gọi trong thân test để starter FAIL chứ không ERROR."""
    if "orders" not in _ORDERS:
        _ORDERS["orders"] = nb.order_table(read_retail_sheet())
    return _ORDERS["orders"]


def test_real_unit_economics(nb):
    real = real_orders(nb)
    assert len(real) == 19_960
    assert real["revenue"].sum() == pytest.approx(10_666_702.54, abs=1)
    ue = nb.unit_economics(real, A)
    p = nb.pnl(ue)
    assert p["contribution"] == pytest.approx(3_761_140.72, abs=1)
    assert p["contribution_margin"] == pytest.approx(0.3526, abs=1e-4)
    negative = ue[ue["contribution"] < 0]
    assert len(negative) == 1_023
    assert negative["contribution"].sum() == pytest.approx(-4_380, abs=1)


def test_real_scenarios(nb):
    real = real_orders(nb)
    out = nb.scenario_table(real, A, {"min25": {"min_order_value": 25}, "price5": {"price_change": 0.05,
                                                                                         "volume_change": -0.08}})
    assert out.loc["min25", "orders"] == pytest.approx(18_896)
    assert out.loc["min25", "delta_contribution"] == pytest.approx(4_338, abs=1)
    assert out.loc["price5", "delta_contribution"] == pytest.approx(179_964, abs=1)
    assert nb.breakeven_volume_change(real, A, 0.05) == pytest.approx(-0.1220, abs=5e-4)
