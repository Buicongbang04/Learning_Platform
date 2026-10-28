"""Bài nhập môn: hoàn thiện từng hàm rồi chạy pytest."""
from decimal import Decimal


def parse_price(value: str) -> Decimal:
    # TODO: parse, kiểm hữu hạn và không âm; dữ liệu sai raise ValueError.
    raise NotImplementedError


def clean_orders(rows: list[dict]) -> tuple[list[tuple], list[tuple]]:
    # TODO: validate từng dòng, phát hiện trùng, không sửa input.
    raise NotImplementedError


def customer_totals(con) -> list[tuple]:
    # TODO: LEFT JOIN, COUNT khóa đơn, COALESCE và ORDER BY.
    raise NotImplementedError
