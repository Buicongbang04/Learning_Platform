"""Nhãn "review xấu" và cách chia train/val/test theo thời gian cho Olist."""

from __future__ import annotations

import pandas as pd

TRAIN_END = pd.Timestamp("2018-01-01")   # train: mua trước mốc này
VAL_END = pd.Timestamp("2018-04-01")     # val: từ TRAIN_END tới trước mốc này
TEST_END = pd.Timestamp("2018-09-01")    # test: từ VAL_END tới hết 2018-08-31; sau đó bỏ


def label_orders(orders: pd.DataFrame, reviews: pd.DataFrame) -> pd.DataFrame:
    """Một dòng cho mỗi đơn giao xong có review, kèm review_score và bad_review (0/1).

    Đơn giao xong: order_status == "delivered" và có order_delivered_customer_date.
    Một đơn có thể có nhiều review: giữ review có review_answer_timestamp mới nhất.
    Review xấu: review_score <= 2. Giữ mọi cột của orders. Không sửa DataFrame đầu vào.
    """
    # TODO: lọc đơn giao xong
    # TODO: dedupe review theo order_id, giữ review trả lời sau cùng
    # TODO: ghép, tạo cột bad_review kiểu int
    raise NotImplementedError


def time_split(df: pd.DataFrame, date_col: str = "order_purchase_timestamp") -> dict[str, pd.DataFrame]:
    """Chia theo ngày mua: {"train", "val", "test"} theo các mốc ở đầu tệp.

    Giữ nguyên index gốc của df. Đơn mua từ TEST_END trở đi bị bỏ (đơn còn dở dang).
    """
    # TODO
    raise NotImplementedError


def split_summary(splits: dict[str, pd.DataFrame], target: str = "bad_review",
                  date_col: str = "order_purchase_timestamp") -> pd.DataFrame:
    """Bảng index train/val/test (đúng thứ tự đó), cột n, bad_rate, start, end (ngày mua nhỏ nhất/lớn nhất)."""
    # TODO
    raise NotImplementedError
