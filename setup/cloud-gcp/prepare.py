"""Chuẩn bị Parquet và baseline local cho lab GCP, không gọi cloud API."""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def prepare(raw: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        # Parameter binding tránh ghép đường dẫn vào chuỗi SQL.
        con.execute("""
            CREATE TABLE orders AS
            SELECT order_id, customer_id, order_status,
                   CAST(order_purchase_timestamp AS DATE) AS order_date
            FROM read_csv_auto(?)
        """, [str(raw / "olist_orders_dataset.csv")])
        con.execute("""
            CREATE TABLE items AS
            SELECT order_id, CAST(price AS DECIMAL(18,2)) AS price
            FROM read_csv_auto(?)
        """, [str(raw / "olist_order_items_dataset.csv")])
        con.execute("""
            CREATE TABLE customers AS
            SELECT customer_id, customer_state FROM read_csv_auto(?)
        """, [str(raw / "olist_customers_dataset.csv")])
        con.execute("""
            CREATE TABLE order_totals AS
            SELECT o.order_id, o.order_date, c.customer_state,
                   CAST(SUM(i.price) AS DECIMAL(18,2)) AS item_revenue
            FROM orders o JOIN items i USING(order_id) JOIN customers c USING(customer_id)
            WHERE o.order_status = 'delivered'
            GROUP BY o.order_id, o.order_date, c.customer_state
        """)
        con.execute("COPY order_totals TO ? (FORMAT PARQUET)", [str(out / "orders.parquet")])
        con.execute("""
            COPY (
                SELECT order_date, customer_state, COUNT(*) AS orders,
                       SUM(item_revenue) AS item_revenue
                FROM order_totals GROUP BY 1,2 ORDER BY 1,2
            ) TO ? (HEADER, DELIMITER ',')
        """, [str(out / "expected_daily_revenue.csv")])
        print("orders, item_revenue:", con.execute(
            "SELECT COUNT(*), SUM(item_revenue) FROM order_totals"
        ).fetchone())
        print("Đã ghi:", out / "orders.parquet", out / "expected_daily_revenue.csv")
    finally:
        con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("/tmp/olist-gcp"))
    args = parser.parse_args()
    prepare(args.raw, args.out)
