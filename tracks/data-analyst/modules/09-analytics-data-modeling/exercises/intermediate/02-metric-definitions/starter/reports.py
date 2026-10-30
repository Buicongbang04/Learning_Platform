"""Hai báo cáo dùng chung metric layer: Finance theo tháng, Marketing theo quốc gia."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from metric_layer import load_metrics, query

HERE = Path(__file__).resolve().parent
TOTAL = "Tổng"


def report(con: duckdb.DuckDBPyConnection, metrics: dict, names: list[str], by: str) -> pd.DataFrame:
    """Bảng chi tiết theo một dimension + dòng cuối `Tổng` tính lại từ metric layer (không cộng các dòng).

    Cột: by, rồi các metric theo thứ tự names; index 0..n-1.
    """
    # TODO: chi tiết = query(con, metrics, names, by=[by])
    # TODO: dòng Tổng = query(con, metrics, names) (không dimension), cột `by` mang giá trị TOTAL
    raise NotImplementedError


def finance_monthly(con: duckdb.DuckDBPyConnection, metrics: dict | None = None) -> pd.DataFrame:
    """Cột month, revenue, orders, aov; tháng tăng dần, dòng cuối Tổng."""
    metrics = metrics or load_metrics(HERE / "metrics.yml")
    # TODO
    raise NotImplementedError


def marketing_country(con: duckdb.DuckDBPyConnection, metrics: dict | None = None) -> pd.DataFrame:
    """Cột country, revenue, orders, active_customers, new_customers, aov; sắp revenue giảm dần, dòng cuối Tổng."""
    metrics = metrics or load_metrics(HERE / "metrics.yml")
    # TODO
    raise NotImplementedError
