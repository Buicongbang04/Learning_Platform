"""Lời giải: gợi ý "mua cùng" bằng Python thuần và Cypher."""

from __future__ import annotations

from collections import Counter, defaultdict


def co_purchase_counts(purchases: list[dict], product_id: str, k: int = 5) -> list[tuple[str, int]]:
    bought: dict[str, set[str]] = defaultdict(set)
    for row in purchases:
        bought[row["customer_id"]].add(row["product_id"])

    counter: Counter[str] = Counter()
    for products in bought.values():
        if product_id in products:
            counter.update(products - {product_id})

    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:k]


CONSTRAINTS = [
    "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE",
]

LOAD_QUERY = """
UNWIND $rows AS row
MERGE (c:Customer {id: row.customer_id})
MERGE (p:Product {id: row.product_id})
  ON CREATE SET p.category = row.category
MERGE (c)-[:BOUGHT {order_id: row.order_id}]->(p)
"""

COPURCHASE_QUERY = """
MATCH (:Product {id: $pid})<-[:BOUGHT]-(c:Customer)-[:BOUGHT]->(o:Product)
WHERE o.id <> $pid
RETURN o.id AS product_id, count(DISTINCT c) AS customers
ORDER BY customers DESC, product_id ASC
LIMIT $k
"""


def load_purchases(driver, rows: list[dict]) -> None:
    for statement in CONSTRAINTS:
        driver.execute_query(statement)
    driver.execute_query(LOAD_QUERY, {"rows": rows})


def co_purchase(driver, product_id: str, k: int = 5) -> list[tuple[str, int]]:
    records, _, _ = driver.execute_query(COPURCHASE_QUERY, {"pid": product_id, "k": k})
    return [(r["product_id"], r["customers"]) for r in records]
