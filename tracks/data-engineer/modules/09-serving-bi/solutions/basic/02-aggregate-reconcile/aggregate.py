"""Lời giải: bảng aggregate agg_daily_sales và reconcile."""

from __future__ import annotations

import duckdb

VALID_STATUS_FILTER = "o.order_status NOT IN ('canceled', 'unavailable')"

DDL = """
CREATE TABLE IF NOT EXISTS agg_daily_sales (
    order_date     DATE,
    customer_state VARCHAR,
    orders         BIGINT,
    items          BIGINT,
    revenue        DOUBLE,
    freight        DOUBLE,
    PRIMARY KEY (order_date, customer_state)
)
"""

SOURCE_BY_DATE_STATE = f"""
SELECT
    CAST(o.order_purchase_timestamp AS DATE) AS order_date,
    c.customer_state,
    COUNT(DISTINCT o.order_id)               AS orders,
    COUNT(*)                                 AS items,
    SUM(oi.price)                            AS revenue,
    SUM(oi.freight_value)                    AS freight
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN customers c ON c.customer_id = o.customer_id
WHERE {VALID_STATUS_FILTER}
  AND CAST(o.order_purchase_timestamp AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
GROUP BY 1, 2
"""


def build_agg_daily_sales(con: duckdb.DuckDBPyConnection, start: str, end: str) -> int:
    con.execute(DDL)
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute(
            "DELETE FROM agg_daily_sales WHERE order_date BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)",
            [start, end],
        )
        con.execute(f"INSERT INTO agg_daily_sales {SOURCE_BY_DATE_STATE}", [start, end])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return con.execute(
        "SELECT COUNT(*) FROM agg_daily_sales WHERE order_date BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)",
        [start, end],
    ).fetchone()[0]


def reconcile(con: duckdb.DuckDBPyConnection, start: str, end: str, tolerance: float = 0.01) -> dict:
    con.execute(DDL)
    src_daily = f"""
        SELECT CAST(o.order_purchase_timestamp AS DATE) AS order_date,
               COUNT(DISTINCT o.order_id) AS orders,
               SUM(oi.price)              AS revenue
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE {VALID_STATUS_FILTER}
          AND CAST(o.order_purchase_timestamp AS DATE) BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
        GROUP BY 1
    """
    agg_daily = """
        SELECT order_date, SUM(orders) AS orders, SUM(revenue) AS revenue
        FROM agg_daily_sales
        WHERE order_date BETWEEN CAST(? AS DATE) AND CAST(? AS DATE)
        GROUP BY 1
    """
    rows = con.execute(
        f"""
        WITH s AS ({src_daily}), a AS ({agg_daily})
        SELECT COALESCE(s.order_date, a.order_date) AS order_date,
               COALESCE(s.orders, 0)  AS src_orders,  COALESCE(a.orders, 0)  AS agg_orders,
               COALESCE(s.revenue, 0) AS src_revenue, COALESCE(a.revenue, 0) AS agg_revenue
        FROM s FULL OUTER JOIN a ON s.order_date = a.order_date
        ORDER BY 1
        """,
        [start, end, start, end],
    ).fetchall()

    mismatched = [
        str(d)
        for d, so, ao, sr, ar in rows
        if so != ao or abs(sr - ar) > tolerance
    ]
    return {
        "ok": not mismatched,
        "agg_revenue": float(sum(r[4] for r in rows)),
        "src_revenue": float(sum(r[3] for r in rows)),
        "agg_orders": int(sum(r[2] for r in rows)),
        "src_orders": int(sum(r[1] for r in rows)),
        "mismatched_dates": mismatched,
    }
