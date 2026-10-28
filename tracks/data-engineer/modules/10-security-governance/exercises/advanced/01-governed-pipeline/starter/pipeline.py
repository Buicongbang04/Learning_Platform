"""Governed pipeline: quality gate + PII masking + OpenLineage-style events.

Giữ nguyên chữ ký `run`, các hằng số và lớp lỗi. Phần thân tự thiết kế.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

NAMESPACE = "olist"
JOB_NAME = "build_orders_enriched"
INPUTS = ["raw.orders", "raw.customers"]
OUTPUT = "mart.orders_enriched"
PRODUCER = "https://github.com/your-org/olist-pipeline"
ORDER_STATUSES = {"created", "approved", "invoiced", "processing", "shipped",
                  "delivered", "canceled", "unavailable"}
OUTPUT_COLUMNS = ["order_id", "customer_key", "customer_state", "order_status", "price"]


class QualityGateError(Exception):
    """Tỉ lệ dòng lỗi vượt ngưỡng, không publish."""


def run(orders: pd.DataFrame, customers: pd.DataFrame, key: bytes,
        emit: Callable[[dict], None], run_id: str | None = None,
        max_invalid_ratio: float = 0.1) -> tuple[pd.DataFrame, pd.DataFrame]:
    # TODO: START -> quality gate -> join + mask -> COMPLETE; FAIL khi gate hỏng hoặc có exception
    raise NotImplementedError
