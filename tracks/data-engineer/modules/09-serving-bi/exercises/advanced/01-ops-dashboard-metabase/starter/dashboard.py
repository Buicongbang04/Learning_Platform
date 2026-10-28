"""Định nghĩa dashboard vận hành như code và publish lên Metabase qua API."""

from __future__ import annotations

import requests

GRID_WIDTH = 24  # lưới dashboard của Metabase rộng 24 cột


def dashboard_spec() -> dict:
    """Trả spec dashboard:

    {
      "name": "Olist - Vận hành giao hàng",
      "cards": [
        {"name": ..., "sql": ..., "display": "scalar" | "line" | "bar" | "row" | "table" | ...,
         "row": int, "col": int, "size_x": int, "size_y": int},
        ...
      ]
    }

    Yêu cầu tối thiểu (xem README): >= 4 card; hàng đầu (row 0) có ít nhất 2 card 'scalar' (KPI tile);
    có ít nhất một biểu đồ xu hướng ('line') và một bảng hành động ('table') đọc mart_overdue_orders;
    SQL chỉ đọc bảng mart_*; card không chồng lên nhau và không vượt GRID_WIDTH.
    """
    # TODO
    raise NotImplementedError


def publish(spec: dict, base_url: str, username: str, password: str, database_id: int) -> int:
    """Tạo các card (native query) và dashboard trên Metabase, gắn card theo vị trí trong spec.

    Trả id của dashboard. Nên idempotent: chạy lại không tạo dashboard trùng tên (cập nhật hoặc thay thế).
    API tham khảo: POST /api/session, POST /api/card, POST /api/dashboard, PUT /api/dashboard/:id.
    """
    # TODO
    raise NotImplementedError
