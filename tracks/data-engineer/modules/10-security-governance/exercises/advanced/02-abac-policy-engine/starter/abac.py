"""ABAC policy engine theo tag catalog.

Giữ nguyên tên lớp, hàm, hằng số. Phần thân tự thiết kế.
"""

from __future__ import annotations

from dataclasses import dataclass

CATALOG: dict[str, dict[str, set[str]]] = {
    "customers": {
        "customer_id": {"identifier"},
        "customer_unique_id": {"pii", "identifier"},
        "email": {"pii", "pii:email"},
        "cpf": {"pii", "pii:national_id", "restricted"},
        "customer_zip_code_prefix": {"quasi_identifier"},
        "customer_state": set(),
    },
    "orders": {
        "order_id": set(),
        "customer_id": {"identifier"},
        "order_status": set(),
        "price": set(),
    },
}

TABLE_META: dict[str, dict] = {
    "customers": {"region": "BR", "owner": "crm-team"},
    "orders": {"region": "BR", "owner": "sales-eng"},
}

PURPOSES = {"analytics", "support", "marketing", "fraud"}


@dataclass(frozen=True)
class Decision:
    effect: str  # "allow" | "mask" | "deny"
    rule: str
    reason: str


class PolicyEngine:
    def __init__(self, catalog: dict, table_meta: dict):
        self.catalog = catalog
        self.table_meta = table_meta
        self.audit: list[dict] = []

    def evaluate(self, user: dict, table: str, column: str, purpose: str) -> Decision:
        # TODO: các luật theo thứ tự, ghi audit
        raise NotImplementedError

    def authorize_query(self, user: dict, table: str, columns: list[str], purpose: str) -> dict[str, Decision]:
        # TODO
        raise NotImplementedError


def propagate_tags(catalog: dict, column_lineage: dict) -> dict:
    # TODO: tag propagation theo thứ tự phụ thuộc
    raise NotImplementedError
