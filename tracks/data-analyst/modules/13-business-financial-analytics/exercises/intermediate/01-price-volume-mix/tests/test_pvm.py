import os
import tempfile
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from testkit import Exercise

ex = Exercise(__file__)


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("pvm.ipynb")


def tiny_tx():
    # StockCode trộn int và str như khi đọc từ Excel; có đơn huỷ, giá 0, số lượng âm, mã phí, dòng ngoài kỳ
    return pd.DataFrame({
        "Invoice": [1, 1, 2, "C3", 4, 5, 6, 7, 8],
        "StockCode": [10001, "10002", 10001, 10001, "POST", 10003, 10002, "10001", 10004],
        "Quantity": [10, 5, 4, -4, 1, 3, -2, 100, 2],
        "Price": [2.0, 4.0, 1.5, 2.0, 18.0, 0.0, 4.0, 2.0, 7.0],
        "InvoiceDate": pd.to_datetime(["2011-01-03 09:00", "2011-01-03 09:00", "2011-01-20 10:00", "2011-01-21 11:00",
                                       "2011-01-22 12:00", "2011-01-23 13:00", "2011-01-24 14:00", "2011-02-01 00:00",
                                       "2010-12-31 23:59"]),
    })


def test_product_sales(nb):
    tx = tiny_tx()
    before = tx.copy()
    out = nb.product_sales(tx, "2011-01-01", "2011-02-01")
    pd.testing.assert_frame_equal(tx, before)
    assert list(out.columns) == ["revenue", "units", "price"]
    assert out.index.name == "StockCode"
    assert list(out.index) == ["10001", "10002"]
    assert out["revenue"].tolist() == pytest.approx([26.0, 20.0])
    assert out["units"].tolist() == [14, 5]
    assert out["price"].tolist() == pytest.approx([26 / 14, 4.0])


def periods():
    idx = lambda codes: pd.Index(codes, name="StockCode")
    p0 = pd.DataFrame({"revenue": [100.0, 200.0, 50.0, 30.0], "units": [50, 20, 10, 6]},
                      index=idx(["A", "B", "C", "D"]))
    p1 = pd.DataFrame({"revenue": [132.0, 180.0, 60.0, 40.0], "units": [60, 15, 12, 8]},
                      index=idx(["A", "B", "C", "E"]))
    for p in (p0, p1):
        p["price"] = p["revenue"] / p["units"]
    return p0, p1


def test_pvm_bridge(nb):
    p0, p1 = periods()
    out = nb.pvm_bridge(p0, p1)
    assert out.name == "effect"
    assert list(out.index) == ["price", "volume", "mix", "new", "lost"]
    # chung A, B, C: giá kỳ 0 = 2, 10, 5; kỳ 1 = 2.2, 12, 5
    price = 0.2 * 60 + 2 * 15 + 0 * 12
    q0, q1 = 80, 87
    avg0 = (50 * 2 + 20 * 10 + 10 * 5) / q0
    volume = (q1 - q0) * avg0
    mix = q1 * ((60 / 87 - 50 / 80) * 2 + (15 / 87 - 20 / 80) * 10 + (12 / 87 - 10 / 80) * 5)
    assert out.tolist() == pytest.approx([price, volume, mix, 40.0, -30.0])
    assert out.sum() == pytest.approx(p1["revenue"].sum() - p0["revenue"].sum())
    assert out["price"] + out["volume"] + out["mix"] == pytest.approx(372.0 - 350.0)


def test_pvm_bridge_no_change(nb):
    p0, _ = periods()
    out = nb.pvm_bridge(p0, p0.copy())
    assert out.tolist() == pytest.approx([0.0] * 5)


def test_product_effects(nb):
    p0, p1 = periods()
    before = p0.copy(), p1.copy()
    out = nb.product_effects(p0, p1)
    pd.testing.assert_frame_equal(p0, before[0])
    pd.testing.assert_frame_equal(p1, before[1])
    assert list(out.columns) == ["revenue0", "revenue1", "price_effect", "quantity_effect"]
    assert list(out.index) == ["A", "B", "C"]
    assert out["price_effect"].tolist() == pytest.approx([12.0, 30.0, 0.0])
    assert out["quantity_effect"].tolist() == pytest.approx([20.0, -50.0, 10.0])
    bridge = nb.pvm_bridge(p0, p1)
    assert out["price_effect"].sum() == pytest.approx(bridge["price"])
    assert out["quantity_effect"].sum() == pytest.approx(bridge["volume"] + bridge["mix"])


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


_P = {}


def real_periods(nb):
    """Hai kỳ tính một lần; gọi trong thân test để starter FAIL chứ không ERROR."""
    if not _P:
        first, second = read_retail_sheet("Year 2009-2010"), read_retail_sheet("Year 2010-2011")
        tx = pd.concat([first[first.InvoiceDate < "2010-12-01"], second], ignore_index=True)
        _P["p0"] = nb.product_sales(tx, "2010-09-01", "2010-12-01")
        _P["p1"] = nb.product_sales(tx, "2011-09-01", "2011-12-01")
    return _P["p0"], _P["p1"]


def test_real_product_sales(nb):
    p0, p1 = real_periods(nb)
    assert (len(p0), len(p1)) == (3323, 3224)
    assert p0["revenue"].sum() == pytest.approx(3_405_331.84, abs=1)
    assert p1["revenue"].sum() == pytest.approx(3_594_877.55, abs=1)
    assert p1.loc["22065", "price"] == pytest.approx(0.4648, abs=1e-4)


def test_real_bridge(nb):
    p0, p1 = real_periods(nb)
    out = nb.pvm_bridge(p0, p1)
    assert out.tolist() == pytest.approx([-117_398.56, -690_653.87, 82_546.59, 1_180_727.34, -265_675.79], abs=1)
    effects = nb.product_effects(p0, p1)
    assert len(effects) == 2481
    assert effects["price_effect"].idxmin() == "22065"
