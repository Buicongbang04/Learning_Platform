"""Quality gate cho bảng orders bằng pandera."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa

ORDER_STATUSES = ["created", "approved", "invoiced", "processing", "shipped",
                  "delivered", "canceled", "unavailable"]
FAILURE_COLUMNS = ["index", "column", "check", "failure_case"]


def build_orders_schema() -> pa.DataFrameSchema:
    # TODO: các cột + check mức DataFrame "delivered_after_purchase"
    raise NotImplementedError


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trả (valid_df, failures)."""
    # TODO: lazy=True, bắt pa.errors.SchemaErrors
    raise NotImplementedError


def quality_report(df: pd.DataFrame) -> dict:
    # TODO: rows, valid_rows, invalid_rows, failed_checks
    raise NotImplementedError
