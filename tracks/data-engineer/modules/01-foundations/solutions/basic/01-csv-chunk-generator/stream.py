"""Đọc order_items CSV theo lô bằng generator và tổng hợp doanh thu theo seller."""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable, Iterator
from decimal import Decimal, InvalidOperation
from itertools import islice
from typing import Any, TypeVar

T = TypeVar("T")


def read_rows(path: str) -> Iterator[dict[str, str]]:
    """Generator trả từng dòng CSV dạng dict."""
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def batched(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Gom phần tử thành list tối đa `size` phần tử; lô cuối có thể ngắn hơn."""
    if size < 1:
        raise ValueError("size phải >= 1")
    it = iter(iterable)
    while batch := list(islice(it, size)):
        yield batch


def _money(value: str | None, field: str) -> Decimal:
    try:
        amount = Decimal((value or "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"{field} không phải số: {value!r}") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{field} không hợp lệ: {value!r}")
    return amount


def parse_item(row: dict[str, str]) -> tuple[str, Decimal]:
    """Trả (seller_id, price + freight_value). Raise ValueError nếu dòng không hợp lệ."""
    seller_id = (row.get("seller_id") or "").strip()
    if not seller_id:
        raise ValueError("thiếu seller_id")
    price = _money(row.get("price"), "price")
    freight = _money(row.get("freight_value"), "freight_value")
    return seller_id, price + freight


def revenue_by_seller(path: str, batch_size: int = 1000) -> dict[str, Any]:
    """Trả {"rows", "bad_rows", "batches", "revenue"}."""
    revenue: defaultdict[str, Decimal] = defaultdict(Decimal)
    rows = bad_rows = batches = 0
    for batch in batched(read_rows(path), batch_size):
        batches += 1
        for row in batch:
            rows += 1
            try:
                seller_id, amount = parse_item(row)
            except ValueError:
                bad_rows += 1
                continue
            revenue[seller_id] += amount
    return {"rows": rows, "bad_rows": bad_rows, "batches": batches, "revenue": dict(revenue)}
