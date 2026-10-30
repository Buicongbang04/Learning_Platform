"""Định nghĩa metric của báo cáo."""

import pandas as pd


def monthly_country_revenue(sales: pd.DataFrame) -> pd.DataFrame:
    """Từ bảng đã làm sạch: mỗi (tháng, quốc gia) một dòng.

    Cột theo thứ tự: month (Timestamp ngày đầu tháng), Country, revenue, orders (số hoá đơn khác nhau),
    customers (số Customer ID khác nhau). Sắp theo month tăng dần, trong tháng theo revenue giảm dần; index 0..n-1.
    """
    # TODO
    raise NotImplementedError
