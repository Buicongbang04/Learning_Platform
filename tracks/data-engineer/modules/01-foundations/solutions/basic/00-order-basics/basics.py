"""Lời giải: tiền chính xác, từ chối dòng lỗi và giữ khách chưa có đơn."""
from decimal import Decimal, InvalidOperation


def parse_price(value: str) -> Decimal:
    try:
        if not isinstance(value, str):
            raise ValueError("Giá phải là chuỗi")
        price = Decimal(value.strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Giá phải là chuỗi số thập phân hợp lệ") from exc
    if not price.is_finite() or price < 0:
        raise ValueError("Giá phải hữu hạn và không âm")
    return price


def clean_orders(rows: list[dict]) -> tuple[list[tuple], list[tuple]]:
    valid, rejected, seen = [], [], set()
    for number, row in enumerate(rows, 1):
        try:
            order_id = row.get("order_id")
            if not isinstance(order_id, str) or not order_id.strip():
                raise ValueError("Thiếu mã đơn")
            order_id = order_id.strip()
            price = parse_price(row.get("price"))
            if order_id in seen:
                raise ValueError("Mã đơn trùng")
        except ValueError as exc:
            rejected.append((number, str(exc)))
            continue
        seen.add(order_id)
        valid.append((order_id, price))
    return valid, rejected


def customer_totals(con) -> list[tuple]:
    return con.execute("""
        SELECT c.customer_id, COUNT(o.order_id), COALESCE(SUM(o.amount_cents), 0)
        FROM customers c LEFT JOIN orders o USING (customer_id)
        GROUP BY c.customer_id ORDER BY c.customer_id
    """).fetchall()
