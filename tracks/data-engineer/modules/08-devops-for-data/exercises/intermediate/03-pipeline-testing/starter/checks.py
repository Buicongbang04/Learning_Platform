"""Bộ check cho pipeline đơn hàng Olist.

Mỗi hàm check_* nhận `pipeline` (có các hàm clean_orders, revenue_by_state, load_orders)
và dùng `assert` để kiểm tra một hành vi. Đặc tả nằm trong docstring của
tests/fixtures/pipeline.py. Không đặt tên hàm bắt đầu bằng test_ (pytest sẽ tự chạy nhầm).
"""

from __future__ import annotations

import sqlite3

import pandas as pd


def raw_orders() -> pd.DataFrame:
    """Dữ liệu nhỏ viết tay; tự thêm dòng để làm lộ lỗi."""
    return pd.DataFrame(
        {
            "order_id": ["o1", "o2"],
            "customer_id": ["c1", "c2"],
            "order_status": ["delivered", "shipped"],
            "updated_at": ["2018-08-01 10:00", "2018-08-01 11:00"],
        }
    )


# ---------- Unit test cho clean_orders ----------

def check_clean_drops_null_order_id(pipeline):
    # TODO 1: đầu vào có order_id None -> đầu ra không còn dòng đó
    raise NotImplementedError


def check_clean_normalizes_status(pipeline):
    # TODO 2: " Delivered " -> "delivered"
    raise NotImplementedError


def check_clean_keeps_latest_duplicate(pipeline):
    # TODO 3: order_id trùng -> giữ bản updated_at mới nhất (đặt bản mới nhất ở TRƯỚC trong input)
    raise NotImplementedError


# ---------- Functional test cho revenue_by_state ----------

def check_revenue_excludes_canceled(pipeline):
    # TODO 4: đơn canceled không được tính vào doanh thu
    raise NotImplementedError


def check_revenue_sorted_desc(pipeline):
    # TODO 5: bang có doanh thu lớn nhất đứng đầu
    raise NotImplementedError


# ---------- Integration test cho load_orders (SQLite in-memory) ----------

def check_load_is_idempotent(pipeline):
    # TODO 6: load hai lần cùng dữ liệu -> số dòng không đổi
    conn = sqlite3.connect(":memory:")
    raise NotImplementedError


def check_load_upserts_new_values(pipeline):
    # TODO 7: load lần hai với order_status mới -> giá trị trong bảng được cập nhật
    raise NotImplementedError
