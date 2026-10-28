"""Pipeline ETL idempotent: CSV đơn hàng -> DuckDB, tham số hoá theo ngày `ds`."""

from __future__ import annotations

import duckdb
import pandas as pd

COLUMNS = ["order_id", "customer_id", "order_status", "amount", "ds"]


def extract(csv_path: str) -> pd.DataFrame:
    """Đọc CSV, mọi cột giữ kiểu chuỗi."""
    return pd.read_csv(csv_path, dtype=str, keep_default_na=True)


def transform(df: pd.DataFrame, ds: str) -> pd.DataFrame:
    """Lọc theo ngày ds, bỏ dòng thiếu order_id, chuẩn hoá status/amount, dedup theo order_id."""
    out = df.copy()
    out = out[out["order_id"].notna() & (out["order_id"].str.strip() != "")]
    out = out[out["order_purchase_timestamp"].str[:10] == ds]
    out["order_status"] = out["order_status"].str.strip().str.lower()
    out["amount"] = out["amount"].astype(float)
    out = out.drop_duplicates("order_id", keep="last")
    out["ds"] = ds
    return out[COLUMNS].reset_index(drop=True)


def load(con: duckdb.DuckDBPyConnection, df: pd.DataFrame, ds: str) -> int:
    """Delete-insert partition ds trong một transaction. Trả về số dòng đã chèn."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS fct_orders (
            order_id VARCHAR,
            customer_id VARCHAR,
            order_status VARCHAR,
            amount DOUBLE,
            ds DATE
        )
        """
    )
    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM fct_orders WHERE ds = CAST(? AS DATE)", [ds])
        con.register("incoming", df)
        con.execute(
            """
            INSERT INTO fct_orders
            SELECT order_id, customer_id, order_status, CAST(amount AS DOUBLE), CAST(? AS DATE)
            FROM incoming
            """,
            [ds],
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.unregister("incoming")
    return len(df)


def run(csv_path: str, db_path: str, ds: str) -> int:
    """Chạy extract -> transform -> load cho một ngày."""
    con = duckdb.connect(db_path)
    try:
        return load(con, transform(extract(csv_path), ds), ds)
    finally:
        con.close()
