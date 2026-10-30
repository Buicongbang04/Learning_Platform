"""Test của BẠN cho report.py. Viết ít nhất 4 hàm test_*, mỗi hàm một định nghĩa.

Chạy riêng: uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/intermediate/01-tested-country-report/starter/checks_report.py -q

Bộ chấm chạy file này hai kiểu:
1. Trên report.py của bạn: mọi test phải pass.
2. Trên bốn bản report.py bị cố ý làm hỏng (lỗi hay gặp ngoài đời): mỗi bản hỏng phải làm ít nhất một test fail.
Chỉ dùng dữ liệu nhỏ tự tạo trong file này (không đọc bộ dữ liệu thật), import từ module `report`.
"""

import pandas as pd
import pytest

from report import clean_transactions, compare_periods, country_summary  # noqa: F401


def make_tx(rows):
    """rows: list of (Invoice, ngày, Quantity, Price, Customer ID, Country)."""
    return pd.DataFrame(rows, columns=["Invoice", "InvoiceDate", "Quantity", "Price", "Customer ID", "Country"]).assign(
        InvoiceDate=lambda d: pd.to_datetime(d["InvoiceDate"], format="ISO8601"))


def test_aov_is_revenue_per_invoice():
    # ví dụ mẫu: một hoá đơn hai dòng (30 GBP) và một hoá đơn một dòng (10 GBP) -> AOV = 40 / 2 = 20
    tx = make_tx([
        (1, "2011-01-03", 1, 10.0, 7.0, "France"),
        (1, "2011-01-03", 2, 10.0, 7.0, "France"),
        (2, "2011-01-04", 1, 10.0, 8.0, "France"),
    ])
    out = country_summary(tx, "2011-01-01", "2011-02-01")
    assert out.loc["France", "aov"] == pytest.approx(20.0)


# TODO: viết thêm ít nhất 3 test. Nghĩ xem report.py có thể sai lặng lẽ ở đâu: dòng nào phải bị loại,
# đếm cái gì, nước nào chỉ xuất hiện ở một kỳ, tăng trưởng chia cho cái gì...
