"""Metric layer tối giản: đọc định nghĩa metric từ YAML, sinh SQL trên bảng fct_sales của DuckDB. Không sửa tệp này.

Bảng fct_sales (grain: một dòng hàng hợp lệ):
    line_id, invoice_no, invoice_month (DATE), country, customer_id (NULL = khách vãng lai),
    first_purchase_month (DATE, tháng mua hợp lệ đầu tiên của khách; NULL với khách vãng lai), revenue

Mỗi metric trong YAML có:
    name, label, description, owner, type (sum | count_distinct | ratio), additive_over_time (true/false),
    caveats (danh sách lưu ý, có thể rỗng),
    expr (với sum, count_distinct), filters (tuỳ chọn, danh sách điều kiện SQL trên cột của fct_sales),
    numerator, denominator (với ratio: tên hai metric khác trong tệp).

    query(con, metrics, ["revenue", "aov"], by=["month"])  ->  DataFrame: month, revenue, aov
"""
from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import yaml

TABLE = "fct_sales"
DIMENSIONS = {
    "month": "strftime(invoice_month, '%Y-%m')",
    "country": "country",
    "customer_type": "CASE WHEN customer_id IS NULL THEN 'guest' ELSE 'identified' END",
}
REQUIRED = ("name", "label", "description", "owner", "type", "additive_over_time", "caveats")
TYPES = {"sum", "count_distinct", "ratio"}


def load_metrics(path: str | Path) -> dict[str, dict]:
    """Đọc và kiểm tệp YAML (khoá gốc `metrics`: danh sách). Trả {name: định nghĩa}. ValueError nếu sai."""
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    items = doc.get("metrics") if isinstance(doc, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("Tệp cần khoá gốc `metrics` là danh sách khác rỗng")
    metrics: dict[str, dict] = {}
    for m in items:
        name = m.get("name") if isinstance(m, dict) else None
        for field in REQUIRED:
            value = m.get(field) if isinstance(m, dict) else None
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Metric {name!r}: thiếu trường {field}")
        if not isinstance(m["additive_over_time"], bool):
            raise ValueError(f"Metric {name!r}: additive_over_time phải là true/false")
        if not isinstance(m["caveats"], list):
            raise ValueError(f"Metric {name!r}: caveats phải là danh sách")
        if m["type"] not in TYPES:
            raise ValueError(f"Metric {name!r}: type phải thuộc {sorted(TYPES)}")
        if m["type"] == "ratio":
            if not m.get("numerator") or not m.get("denominator"):
                raise ValueError(f"Metric {name!r}: ratio cần numerator và denominator")
        elif not m.get("expr"):
            raise ValueError(f"Metric {name!r}: cần expr")
        if not isinstance(m.get("filters", []), list):
            raise ValueError(f"Metric {name!r}: filters phải là danh sách")
        if name in metrics:
            raise ValueError(f"Metric {name!r} khai báo hai lần")
        metrics[name] = m
    for m in metrics.values():
        if m["type"] == "ratio":
            for part in (m["numerator"], m["denominator"]):
                if part not in metrics or metrics[part]["type"] == "ratio":
                    raise ValueError(f"Metric {m['name']!r}: {part!r} phải là metric sum/count_distinct trong tệp")
    return metrics


def metric_sql(metrics: dict[str, dict], name: str) -> str:
    """Biểu thức SQL tổng hợp của một metric (dùng trong SELECT ... GROUP BY)."""
    m = metrics[name]
    if m["type"] == "ratio":
        return f"({metric_sql(metrics, m['numerator'])}) / nullif({metric_sql(metrics, m['denominator'])}, 0)"
    agg = f"sum({m['expr']})" if m["type"] == "sum" else f"count(DISTINCT {m['expr']})"
    filters = m.get("filters") or []
    if filters:
        agg += " FILTER (WHERE " + " AND ".join(f"({f})" for f in filters) + ")"
    return agg


def query(con: duckdb.DuckDBPyConnection, metrics: dict[str, dict], names: list[str],
          by: list[str] | tuple[str, ...] = ()) -> pd.DataFrame:
    """Tính các metric theo các dimension (thứ tự giữ nguyên). Không có dimension: một dòng tổng."""
    unknown = [n for n in names if n not in metrics] + [d for d in by if d not in DIMENSIONS]
    if unknown or not names:
        raise ValueError(f"Metric/dimension không có trong định nghĩa: {unknown}")
    cols = [f"{DIMENSIONS[d]} AS {d}" for d in by] + [f"{metric_sql(metrics, n)} AS {n}" for n in names]
    sql = f"SELECT {', '.join(cols)} FROM {TABLE}"
    if by:
        positions = ", ".join(str(i + 1) for i in range(len(by)))
        sql += f" GROUP BY {positions} ORDER BY {positions}"
    df = con.execute(sql).df()
    for n in names:  # count distinct trả int64; ép float cho mọi metric để báo cáo đồng nhất
        df[n] = df[n].astype(float)
    return df
