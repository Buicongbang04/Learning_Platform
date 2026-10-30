"""Hai question doanh thu trên Metabase, tạo bằng API.

    uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/basic/02-metabase-revenue-questions/starter/metabase_questions.py

Cần BI đang chạy (setup/SETUP.md mục 11). Mở http://localhost:3000 để xem hai question vừa tạo.
`session` trong mọi hàm là requests.Session của setup/bi/clients.py: gọi bằng đường dẫn tương đối,
ví dụ `session.get("/api/database").json()`.
"""
from __future__ import annotations

import sys
from pathlib import Path

PREFIX = "DA10 · "


def find_table(session, database: str = "de", schema: str = "da", table: str = "online_retail_ii") -> dict:
    """Tra id database, id bảng và id từng cột của `schema.table` trong Metabase.

    Trả {"database_id": int, "table_id": int, "fields": {tên cột: id cột}}.
    Endpoint: GET /api/database (danh sách nằm trong khoá "data"), GET /api/database/<id>/metadata
    (khoá "tables", mỗi bảng có "schema", "name", "fields").
    """
    # TODO: tìm database theo tên, rồi bảng theo cả schema và tên (cùng tên có thể nằm ở schema khác)
    raise NotImplementedError


def monthly_revenue_card(database_id: int, name: str) -> dict:
    """Payload POST /api/card cho question SQL (native) vẽ line.

    Cột: month (DATE, ngày đầu tháng), revenue (làm tròn 2 số), orders (số hoá đơn khác nhau),
    customers (số khách có mã khác nhau), aov (revenue / orders, làm tròn 2 số). Sắp theo month.
    """
    # TODO: {"name", "display": "line", "visualization_settings", "dataset_query": {database, type "native", native.query}}
    raise NotImplementedError


def country_revenue_card(ids: dict, name: str) -> dict:
    """Payload POST /api/card cho question query builder (MBQL): 10 nước doanh thu cao nhất, display "row".

    `ids` là kết quả của find_table.
    """
    # TODO: dataset_query type "query": source-table, aggregation sum revenue, breakout country,
    #       order-by giảm dần theo aggregation 0, limit 10
    raise NotImplementedError


def upsert_card(session, card: dict) -> int:
    """Tạo question nếu chưa có card (chưa archive) cùng tên, có rồi thì cập nhật. Trả id.

    Endpoint: GET /api/card (danh sách card), POST /api/card, PUT /api/card/<id>.
    """
    # TODO: chạy lại nhiều lần không được sinh card trùng tên
    raise NotImplementedError


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
