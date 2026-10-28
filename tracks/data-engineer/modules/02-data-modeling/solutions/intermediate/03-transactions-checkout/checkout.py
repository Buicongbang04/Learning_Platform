"""Đặt hàng nguyên tử (SQLite) và trừ tồn kho an toàn đồng thời (PostgreSQL)."""

from __future__ import annotations

import sqlite3


class OutOfStock(Exception):
    """Sản phẩm không đủ hàng hoặc không tồn tại."""


def create_schema(con: sqlite3.Connection) -> None:
    """Đã làm sẵn."""
    con.executescript(
        """
        CREATE TABLE stock (product_id TEXT PRIMARY KEY, qty INTEGER NOT NULL CHECK (qty >= 0));
        CREATE TABLE orders (order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, total REAL NOT NULL);
        CREATE TABLE order_items (order_id TEXT NOT NULL, product_id TEXT NOT NULL,
                                  qty INTEGER NOT NULL, price REAL NOT NULL);
        """
    )


def place_order(
    con: sqlite3.Connection,
    order_id: str,
    customer_id: str,
    items: list[tuple[str, int, float]],
) -> float:
    """Trừ kho + tạo đơn + tạo item trong một transaction. Trả về total."""
    if not items:
        raise ValueError("Đơn hàng phải có ít nhất một item")
    for product_id, qty, price in items:
        if qty <= 0 or price < 0:
            raise ValueError(f"qty/price không hợp lệ cho {product_id}")

    total = round(sum(qty * price for _, qty, price in items), 2)

    # `with con`: COMMIT khi khối chạy xong, ROLLBACK khi có bất kỳ exception nào.
    with con:
        for product_id, qty, _ in items:
            cur = con.execute(
                "UPDATE stock SET qty = qty - ? WHERE product_id = ? AND qty >= ?",
                (qty, product_id, qty),
            )
            if cur.rowcount != 1:
                raise OutOfStock(product_id)
        con.execute(
            "INSERT INTO orders (order_id, customer_id, total) VALUES (?, ?, ?)",
            (order_id, customer_id, total),
        )
        con.executemany(
            "INSERT INTO order_items (order_id, product_id, qty, price) VALUES (?, ?, ?, ?)",
            [(order_id, product_id, qty, price) for product_id, qty, price in items],
        )
    return total


def reserve_pg(dsn: str, product_id: str, qty: int) -> bool:
    """Trừ qty khỏi ex_stock nếu đủ hàng (PostgreSQL). True nếu thành công."""
    import psycopg

    with psycopg.connect(dsn) as conn:  # thoát khối: commit (hoặc rollback nếu lỗi)
        cur = conn.execute(
            "UPDATE ex_stock SET qty = qty - %s WHERE product_id = %s AND qty >= %s",
            (qty, product_id, qty),
        )
        return cur.rowcount == 1
