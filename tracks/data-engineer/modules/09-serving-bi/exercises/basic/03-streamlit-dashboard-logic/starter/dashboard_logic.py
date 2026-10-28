"""Logic thuần Python cho dashboard vận hành Olist. Không import streamlit ở đây.

DataFrame đầu vào có các cột (grain: một dòng order_items):
    order_id (str), order_date (datetime64, đã bỏ giờ), customer_state (str),
    order_status (str), price (float), is_late (bool, cùng giá trị cho mọi item của một đơn)
"""

from __future__ import annotations

import pandas as pd


def filter_orders(df: pd.DataFrame, start, end, states=None) -> pd.DataFrame:
    """Lọc order_date trong [start, end] (cả hai đầu; start/end là str hoặc date) và theo states.

    states là None hoặc rỗng nghĩa là lấy mọi state. Trả DataFrame mới, index đánh lại từ 0,
    không sửa df gốc.
    """
    # TODO
    raise NotImplementedError


def compute_kpis(df: pd.DataFrame) -> dict:
    """Trả dict:
        orders    -> int, số đơn khác nhau
        revenue   -> float, tổng price, làm tròn 2 chữ số
        aov       -> float, revenue / orders làm tròn 2; 0.0 khi không có đơn
        late_rate -> float làm tròn 4: trong các ĐƠN có order_status == 'delivered', tỉ lệ đơn is_late;
                     None khi không có đơn delivered
    Chú ý: tính theo đơn, không theo dòng item.
    """
    # TODO
    raise NotImplementedError


def pct_change(current, previous):
    """% thay đổi so với kỳ trước, làm tròn 1 chữ số: (current - previous) / |previous| * 100.

    Trả None khi previous là None hoặc 0.
    """
    # TODO
    raise NotImplementedError


def daily_series(df: pd.DataFrame, start, end) -> pd.DataFrame:
    """Chuỗi theo ngày cho biểu đồ line, đủ mọi ngày trong [start, end] (ngày không có đơn điền 0).

    Cột: order_date (datetime64), orders (int), revenue (float). Sắp xếp theo ngày, index từ 0.
    """
    # TODO
    raise NotImplementedError


def format_brl(value) -> str:
    """Định dạng tiền Brazil: 1234.5 -> 'R$ 1.234,50'; -1234.5 -> '-R$ 1.234,50'; None -> 'n/a'."""
    # TODO
    raise NotImplementedError


def kpi_status(value, target, higher_is_better: bool = True, warn_margin: float = 0.1) -> str:
    """Trạng thái màu của KPI tile.

    - 'unknown' nếu value là None.
    - 'ok' nếu đạt target (>= khi higher_is_better, <= khi ngược lại).
    - 'warn' nếu chưa đạt nhưng lệch không quá warn_margin * |target|.
    - 'bad' trong các trường hợp còn lại.
    """
    # TODO
    raise NotImplementedError
