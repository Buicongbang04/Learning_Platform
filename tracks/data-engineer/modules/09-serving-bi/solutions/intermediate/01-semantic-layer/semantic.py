"""Lời giải: semantic layer tối giản: định nghĩa metric một lần, sinh SQL cho DuckDB.

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
    if not metrics:
        raise ValueError("Cần ít nhất một metric")
    for m in metrics:
        if m not in METRICS:
            raise ValueError(f"Metric không tồn tại: {m!r}")
    for d in dimensions:
        if d not in DIMENSIONS:
            raise ValueError(f"Dimension không tồn tại: {d!r}")
    for f in filters:
        if len(f) != 3:
            raise ValueError(f"Filter phải có dạng (dimension, op, value): {f!r}")
        dim, op, value = f
        if dim not in DIMENSIONS:
            raise ValueError(f"Dimension của filter không tồn tại: {dim!r}")
        if op not in FILTER_OPS:
            raise ValueError(f"Toán tử không hỗ trợ: {op!r}")
        if op == "in" and (not isinstance(value, (list, tuple)) or len(value) == 0):
            raise ValueError("Toán tử 'in' cần list/tuple khác rỗng")


def _required_measures(metrics) -> list[str]:
    needed: list[str] = []
    for m in metrics:
        spec = METRICS[m]
        names = [spec["measure"]] if spec["type"] == "simple" else [spec["numerator"], spec["denominator"]]
        for name in names:
            if name not in needed:
                needed.append(name)
    return needed


def _where(filters) -> tuple[str, list]:
    clauses, params = [], []
    for dim, op, value in filters:
        expr = DIMENSIONS[dim]
        if op == "in":
            clauses.append(f"{expr} IN ({', '.join('?' for _ in value)})")
            params.extend(value)
        else:
            clauses.append(f"{expr} {op} ?")
            params.append(value)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def compile_query(metrics, dimensions=(), filters=()) -> tuple[str, list]:
    validate_request(metrics, dimensions, filters)
    dimensions, filters = list(dimensions), list(filters)

    by_model: dict[str, list[str]] = {}
    for name in _required_measures(metrics):
        by_model.setdefault(MEASURES[name]["model"], []).append(name)

    where_sql, where_params = _where(filters)
    ctes, params = [], []
    for model, measures in by_model.items():
        select = [f"{DIMENSIONS[d]} AS {d}" for d in dimensions]
        select += [f"{MEASURES[m]['agg']} AS {m}" for m in measures]
        group = f" GROUP BY {', '.join(str(i + 1) for i in range(len(dimensions)))}" if dimensions else ""
        ctes.append(f"m_{model} AS (SELECT {', '.join(select)} FROM ({MODELS[model]}) AS base{where_sql}{group})")
        params.extend(where_params)

    names = [f"m_{model}" for model in by_model]
    from_sql = names[0]
    for other in names[1:]:
        if dimensions:
            from_sql += f" FULL OUTER JOIN {other} USING ({', '.join(dimensions)})"
        else:
            from_sql += f" CROSS JOIN {other}"

    select = list(dimensions)
    for m in metrics:
        spec = METRICS[m]
        if spec["type"] == "simple":
            select.append(f"{spec['measure']} AS {m}" if spec["measure"] != m else m)
        else:
            select.append(f"{spec['numerator']} / NULLIF({spec['denominator']}, 0) AS {m}")
    order = f" ORDER BY {', '.join(dimensions)}" if dimensions else ""
    sql = f"WITH {', '.join(ctes)} SELECT {', '.join(select)} FROM {from_sql}{order}"
    return sql, params


def run_query(con: duckdb.DuckDBPyConnection, metrics, dimensions=(), filters=()) -> list[dict]:
    sql, params = compile_query(metrics, dimensions, filters)
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
