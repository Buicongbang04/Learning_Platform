"""Hai question doanh thu trên Metabase, tạo bằng API (lời giải).

    uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/basic/02-metabase-revenue-questions/starter/metabase_questions.py

Cần BI đang chạy (setup/SETUP.md mục 11). Mở http://localhost:3000 để xem hai question vừa tạo.
"""
from __future__ import annotations

import sys
from pathlib import Path

PREFIX = "DA10 · "

MONTHLY_SQL = """
SELECT CAST(date_trunc('month', invoicedate) AS DATE) AS month,
       ROUND(CAST(SUM(revenue) AS NUMERIC), 2) AS revenue,
       COUNT(DISTINCT invoice) AS orders,
       COUNT(DISTINCT customer_id) AS customers,
       ROUND(CAST(SUM(revenue) / COUNT(DISTINCT invoice) AS NUMERIC), 2) AS aov
FROM da.online_retail_ii
GROUP BY 1
ORDER BY 1
""".strip()


def find_table(session, database: str = "de", schema: str = "da", table: str = "online_retail_ii") -> dict:
    """Tra id database, id bảng và id từng cột của `schema.table` trong Metabase."""
    dbs = session.get("/api/database").json()
    dbs = dbs["data"] if isinstance(dbs, dict) else dbs
    matches = [d for d in dbs if d["name"] == database]
    if not matches:
        raise LookupError(f"Metabase chưa có database `{database}`. Chạy: uv run python setup/bi/init_bi.py")
    db_id = matches[0]["id"]
    meta = session.get(f"/api/database/{db_id}/metadata").json()
    tables = [t for t in meta["tables"] if t["schema"] == schema and t["name"] == table]
    if not tables:
        raise LookupError(f"Không thấy bảng {schema}.{table}. Chạy: uv run python setup/bi/load_da.py")
    return {
        "database_id": db_id,
        "table_id": tables[0]["id"],
        "fields": {f["name"]: f["id"] for f in tables[0]["fields"]},
    }


def monthly_revenue_card(database_id: int, name: str) -> dict:
    """Question SQL (native): doanh thu, số đơn, số khách, AOV theo tháng, vẽ line."""
    return {
        "name": name,
        "display": "line",
        "description": "Doanh thu gộp (dòng hợp lệ) theo tháng. Tháng 12/2011 chỉ có dữ liệu tới ngày 9.",
        "visualization_settings": {"graph.dimensions": ["month"], "graph.metrics": ["revenue"]},
        "dataset_query": {"database": database_id, "type": "native", "native": {"query": MONTHLY_SQL}},
    }


def country_revenue_card(ids: dict, name: str) -> dict:
    """Question dựng bằng query builder (MBQL): 10 nước doanh thu cao nhất, vẽ row chart."""
    fields = ids["fields"]
    return {
        "name": name,
        "display": "row",
        "description": "Tổng doanh thu gộp theo quốc gia, 12/2009-12/2011.",
        "visualization_settings": {},
        "dataset_query": {
            "database": ids["database_id"],
            "type": "query",
            "query": {
                "source-table": ids["table_id"],
                "aggregation": [["sum", ["field", fields["revenue"], None]]],
                "breakout": [["field", fields["country"], None]],
                "order-by": [["desc", ["aggregation", 0]]],
                "limit": 10,
            },
        },
    }


def upsert_card(session, card: dict) -> int:
    """Tạo question nếu chưa có card (chưa archive) cùng tên, có rồi thì cập nhật. Trả id."""
    existing = [c for c in session.get("/api/card").json() if c["name"] == card["name"] and not c.get("archived")]
    if existing:
        card_id = existing[0]["id"]
        r = session.put(f"/api/card/{card_id}", json=card)
        r.raise_for_status()
        return card_id
    r = session.post("/api/card", json=card)
    r.raise_for_status()
    return r.json()["id"]


def publish(session, prefix: str = PREFIX) -> dict[str, int]:
    ids = find_table(session)
    return {
        "monthly": upsert_card(session, monthly_revenue_card(ids["database_id"], f"{prefix}Doanh thu theo tháng")),
        "country": upsert_card(session, country_revenue_card(ids, f"{prefix}Top 10 quốc gia theo doanh thu")),
    }


if __name__ == "__main__":
    sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()) / "setup" / "bi"))
    import clients

    session = clients.metabase_session()
    for key, card_id in publish(session).items():
        print(f"{key}: {clients.base_url('metabase')}/question/{card_id}")
