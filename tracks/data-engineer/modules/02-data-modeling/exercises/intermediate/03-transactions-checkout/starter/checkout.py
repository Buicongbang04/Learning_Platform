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
    # TODO: kiểm tra đầu vào, rồi làm mọi thao tác ghi trong một transaction
    raise NotImplementedError


def reserve_pg(dsn: str, product_id: str, qty: int) -> bool:
    """Trừ qty khỏi ex_stock nếu đủ hàng (PostgreSQL). True nếu thành công."""
    # TODO: một câu UPDATE có điều kiện, kiểm tra rowcount
    raise NotImplementedError
