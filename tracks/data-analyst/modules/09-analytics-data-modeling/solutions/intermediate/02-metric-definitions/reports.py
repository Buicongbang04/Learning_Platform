"""Hai báo cáo dùng chung metric layer: Finance theo tháng, Marketing theo quốc gia."""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from metric_layer import load_metrics, query

HERE = Path(__file__).resolve().parent
TOTAL = "Tổng"


def report(con: duckdb.DuckDBPyConnection, metrics: dict, names: list[str], by: str) -> pd.DataFrame:
    """Bảng chi tiết theo một dimension + dòng cuối `Tổng` tính lại từ metric layer (không cộng các dòng)."""
    detail = query(con, metrics, names, by=[by])
    total = query(con, metrics, names).assign(**{by: TOTAL})
    return pd.concat([detail, total[[by, *names]]], ignore_index=True)


def finance_monthly(con: duckdb.DuckDBPyConnection, metrics: dict | None = None) -> pd.DataFrame:
    """Cột month, revenue, orders, aov; tháng tăng dần, dòng cuối Tổng."""
    metrics = metrics or load_metrics(HERE / "metrics.yml")
    return report(con, metrics, ["revenue", "orders", "aov"], "month")


def marketing_country(con: duckdb.DuckDBPyConnection, metrics: dict | None = None) -> pd.DataFrame:
    """Cột country, revenue, orders, active_customers, new_customers, aov; sắp revenue giảm dần, dòng cuối Tổng."""
    metrics = metrics or load_metrics(HERE / "metrics.yml")
    out = report(con, metrics, ["revenue", "orders", "active_customers", "new_customers", "aov"], "country")
    detail = out.iloc[:-1].sort_values(["revenue", "country"], ascending=[False, True])
    return pd.concat([detail, out.iloc[-1:]], ignore_index=True)
