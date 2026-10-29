"""Khi nào nhãn "giao trễ" có mặt, và metric trên cohort chưa chín lệch thế nào."""

from __future__ import annotations

import pandas as pd


def late_label_known_at(orders: pd.DataFrame) -> pd.DataFrame:
    """Chỉ đơn giao xong (delivered + có ngày giao). Index order_id; cột purchase_ts, late (bool), known_at.

    late = order_delivered_customer_date > order_estimated_delivery_date (so nguyên timestamp).
    known_at = ngày hẹn nếu trễ (biết ngay khi quá hẹn), ngày giao thực tế nếu đúng hẹn.
    """
    # TODO
    raise NotImplementedError


def observed_late_rate(labels: pd.DataFrame, as_of) -> tuple[float, float]:
    """(share_known, observed_rate) tại as_of: tỉ lệ đơn có known_at <= as_of, và tỉ lệ trễ trên các đơn đó."""
    # TODO
    raise NotImplementedError


def maturity_days(labels: pd.DataFrame, coverage: float = 0.95) -> float:
    """Quantile `coverage` của số ngày (thực) từ purchase_ts tới known_at."""
    # TODO
    raise NotImplementedError
