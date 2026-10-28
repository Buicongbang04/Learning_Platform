"""Gợi ý "mua cùng": Python thuần và Cypher trên Neo4j."""

from __future__ import annotations

from collections import Counter, defaultdict  # noqa: F401


def co_purchase_counts(purchases: list[dict], product_id: str, k: int = 5) -> list[tuple[str, int]]:
    """[(product_id, số khách distinct)] sort giảm dần theo số khách rồi product_id."""
    # TODO: customer -> set(product); khách đã mua product_id; Counter các sản phẩm khác
    raise NotImplementedError


# TODO: hai câu CREATE CONSTRAINT ... IF NOT EXISTS cho Customer.id và Product.id
CONSTRAINTS: list[str] = []

# TODO: UNWIND $rows AS row, MERGE Customer, MERGE Product (đặt category), MERGE quan hệ BOUGHT {order_id}
LOAD_QUERY = """
// TODO
"""

# TODO: dùng $pid và $k, trả cột product_id và customers
COPURCHASE_QUERY = """
// TODO
"""


def load_purchases(driver, rows: list[dict]) -> None:
    # TODO: chạy từng câu trong CONSTRAINTS, rồi LOAD_QUERY với tham số rows
    raise NotImplementedError


def co_purchase(driver, product_id: str, k: int = 5) -> list[tuple[str, int]]:
    # TODO: chạy COPURCHASE_QUERY, đổi records thành list tuple
    raise NotImplementedError
