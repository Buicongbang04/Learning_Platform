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
    delivered = orders[(orders["order_status"] == "delivered")
                       & orders["order_delivered_customer_date"].notna()]
    latest = (reviews.sort_values("review_answer_timestamp", kind="stable")
              .drop_duplicates("order_id", keep="last"))
    out = delivered.merge(latest[["order_id", "review_score"]], on="order_id", how="inner")
    out["bad_review"] = (out["review_score"] <= 2).astype(int)
    return out


def time_split(df: pd.DataFrame, date_col: str = "order_purchase_timestamp") -> dict[str, pd.DataFrame]:
    """Chia theo ngày mua: {"train", "val", "test"} theo các mốc ở đầu tệp.

    Giữ nguyên index gốc của df. Đơn mua từ TEST_END trở đi bị bỏ (đơn còn dở dang).
    """
    t = df[date_col]
    return {
        "train": df[t < TRAIN_END],
        "val": df[(t >= TRAIN_END) & (t < VAL_END)],
        "test": df[(t >= VAL_END) & (t < TEST_END)],
    }


def split_summary(splits: dict[str, pd.DataFrame], target: str = "bad_review",
                  date_col: str = "order_purchase_timestamp") -> pd.DataFrame:
    """Bảng index train/val/test (đúng thứ tự đó), cột n, bad_rate, start, end (ngày mua nhỏ nhất/lớn nhất)."""
    rows = {
        name: {"n": len(part), "bad_rate": part[target].mean(),
               "start": part[date_col].min(), "end": part[date_col].max()}
        for name, part in ((k, splits[k]) for k in ("train", "val", "test"))
    }
    return pd.DataFrame.from_dict(rows, orient="index")
