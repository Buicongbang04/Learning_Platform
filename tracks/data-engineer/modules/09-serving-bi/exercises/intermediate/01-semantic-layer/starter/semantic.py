"""Semantic layer tối giản: định nghĩa metric một lần, sinh SQL cho DuckDB.

Phần REGISTRY (MODELS, DIMENSIONS, MEASURES, METRICS) đã viết sẵn. Bạn viết phần biên dịch.
"""

from __future__ import annotations

import duckdb

VALID_ORDERS = "o.order_status NOT IN ('canceled', 'unavailable')"

# Mỗi model là một "bảng logic" ở một grain cố định. Measure chỉ được aggregate trên model của nó,
# nhờ vậy measure ở grain đơn hàng không bị fan-out bởi order_items.
MODELS = {
    "items": f"""
        SELECT o.order_id, o.order_status,
               CAST(o.order_purchase_timestamp AS DATE) AS order_date,
               c.customer_state, oi.price, oi.freight_value
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE {VALID_ORDERS}
    """,
    "orders": f"""
        SELECT o.order_id, o.order_status,
               CAST(o.order_purchase_timestamp AS DATE) AS order_date,
               c.customer_state,
               o.order_delivered_customer_date > o.order_estimated_delivery_date AS is_late
        FROM orders o
        JOIN customers c ON c.customer_id = o.customer_id
        WHERE {VALID_ORDERS}
    """,
}

# Dimension dùng chung cho mọi model (mọi model đều có các cột này).
DIMENSIONS = {
    "order_date": "order_date",
    "order_month": "DATE_TRUNC('month', order_date)",
    "customer_state": "customer_state",
    "order_status": "order_status",
}

MEASURES = {
    "revenue": {"model": "items", "agg": "SUM(price)"},
    "freight": {"model": "items", "agg": "SUM(freight_value)"},
    "items": {"model": "items", "agg": "COUNT(*)"},
    "orders": {"model": "orders", "agg": "COUNT(DISTINCT order_id)"},
    "delivered_orders": {"model": "orders", "agg": "COUNT(DISTINCT CASE WHEN order_status = 'delivered' THEN order_id END)"},
    "late_orders": {"model": "orders", "agg": "COUNT(DISTINCT CASE WHEN is_late THEN order_id END)"},
}

METRICS = {
    "revenue": {"type": "simple", "measure": "revenue"},
    "freight": {"type": "simple", "measure": "freight"},
    "items": {"type": "simple", "measure": "items"},
    "orders": {"type": "simple", "measure": "orders"},
    "late_orders": {"type": "simple", "measure": "late_orders"},
    "aov": {"type": "ratio", "numerator": "revenue", "denominator": "orders"},
    "late_rate": {"type": "ratio", "numerator": "late_orders", "denominator": "delivered_orders"},
}

FILTER_OPS = {"=", "!=", ">", ">=", "<", "<=", "in"}


def validate_request(metrics, dimensions=(), filters=()) -> None:
    """Raise ValueError nếu:
    - metrics rỗng, hoặc có metric không nằm trong METRICS;
    - có dimension không nằm trong DIMENSIONS (đây là lớp chặn SQL injection qua tên cột);
    - filter (dimension, op, value) có dimension lạ, op ngoài FILTER_OPS,
      hoặc op 'in' mà value không phải list/tuple khác rỗng.
    """
    # TODO
    raise NotImplementedError


def compile_query(metrics, dimensions=(), filters=()) -> tuple[str, list]:
    """Sinh (sql, params) cho DuckDB.

    Yêu cầu:
    - Gọi validate_request trước.
    - Xác định các measure cần (ratio cần cả numerator và denominator), nhóm theo model.
    - Mỗi model một CTE: SELECT <dims> , <measures> FROM (<model sql>) WHERE <filters> GROUP BY <dims>.
    - Nối các CTE theo dimension (FULL OUTER JOIN … USING (…)); không có dimension thì CROSS JOIN.
    - SELECT cuối: các dimension (đặt tên đúng như key), rồi từng metric theo thứ tự yêu cầu;
      ratio = numerator / NULLIF(denominator, 0) tính SAU khi aggregate.
    - ORDER BY các dimension theo thứ tự yêu cầu.
    - Giá trị filter đi qua params (dấu ?), không ghép vào chuỗi SQL.
    """
    # TODO
    raise NotImplementedError


def run_query(con: duckdb.DuckDBPyConnection, metrics, dimensions=(), filters=()) -> list[dict]:
    """Biên dịch, chạy và trả list dict {tên cột: giá trị}."""
    # TODO
    raise NotImplementedError
