"""clean_retail: quy tắc dòng hợp lệ của Online Retail II, trên DataFrame nhỏ (không cần Docker)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "setup" / "bi"))
import load_da  # noqa: E402


def frame(rows):
    return pd.DataFrame(rows, columns=["Invoice", "StockCode", "Quantity", "InvoiceDate", "Price", "Customer ID"])


def test_clean_retail_quy_tac():
    t = pd.Timestamp
    a = frame([
        (1001, "A", 2, t("2010-12-01"), 3.0, 1.0),    # hợp lệ (Invoice số -> str)
        ("C1002", "A", 1, t("2010-12-02"), 3.0, 1.0),  # hoá đơn huỷ
        ("1003", "B", -1, t("2010-12-03"), 2.0, 2.0),  # qty <= 0
        ("1004", "B", 1, t("2010-12-09"), 0.0, 2.0),   # price <= 0
        ("1005", "B", 1, t("2010-12-09"), 5.0, None),  # hợp lệ, không có customer
    ])
    b = frame([
        ("1005", "B", 1, t("2010-12-09"), 5.0, None),  # chồng lấn với sheet đầu
        ("2001", "C", 4, t("2011-01-05"), 2.5, 3.0),
    ])
    out = load_da.clean_retail([a, b])
    assert sorted(out["invoice"]) == ["1001", "1005", "2001"]
    assert out["invoice"].map(type).eq(str).all()
    assert out.loc[out["invoice"] == "2001", "revenue"].iloc[0] == 10.0
    assert out["customer_id"].isna().sum() == 1
