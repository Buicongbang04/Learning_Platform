"""Baseline từ dữ liệu Olist thật để thiết kế thí nghiệm."""

from __future__ import annotations

import pandas as pd


def baseline(orders: pd.DataFrame, reviews: pd.DataFrame) -> dict[str, float]:
    """Các con số nền cho thiết kế thí nghiệm.

    Đơn "giao xong" là order_status == "delivered" và có order_delivered_customer_date.
    Một đơn có thể có nhiều review: giữ review có review_answer_timestamp mới nhất.

    Trả về:
      bad_review_rate      tỉ lệ review_score <= 2 trên các đơn giao xong có review
      late_rate            tỉ lệ giao trễ trên các đơn giao xong: so sánh nguyên timestamp
                           order_delivered_customer_date > order_estimated_delivery_date (giao 15:00
                           đúng ngày hẹn cũng tính là trễ, vì ngày hẹn lưu lúc 00:00)
      bad_review_rate_late như bad_review_rate nhưng chỉ trên đơn giao trễ
      delivered_per_week   trung vị số đơn giao xong theo tuần mua hàng (tuần kết thúc Chủ nhật),
                           bỏ tuần đầu và tuần cuối vì có thể không đủ ngày
    """
    # TODO: lọc đơn giao xong
    # TODO: dedupe review theo order_id, giữ review mới nhất
    # TODO: tính 4 con số
    raise NotImplementedError
