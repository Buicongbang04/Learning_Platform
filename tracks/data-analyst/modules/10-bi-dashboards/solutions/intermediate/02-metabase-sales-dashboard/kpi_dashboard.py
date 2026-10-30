"""Dashboard doanh số cho Head of Sales trên Metabase: 4 card, bộ lọc Quốc gia, tạo bằng API (lời giải).

    uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/intermediate/02-metabase-sales-dashboard/starter/kpi_dashboard.py

Cần BI đang chạy (setup/SETUP.md mục 11). `session` là requests.Session của setup/bi/clients.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

PREFIX = "DA10 · "
GRID_COLUMNS = 24  # lưới dashboard Metabase rộng 24 cột

# Tháng đủ gần nhất, tính trên TOÀN BỘ dữ liệu (không lọc quốc gia): dữ liệu tới ngày cuối tháng thì tháng đó đủ.
BOUNDS = """
bounds AS (
    SELECT CASE
               WHEN CAST(max(invoicedate) AS DATE)
                    = CAST(date_trunc('month', max(invoicedate)) + INTERVAL '1 month' - INTERVAL '1 day' AS DATE)
               THEN CAST(date_trunc('month', max(invoicedate)) AS DATE)
               ELSE CAST(date_trunc('month', max(invoicedate)) - INTERVAL '1 month' AS DATE)
           END AS last_month
    FROM da.online_retail_ii
)""".strip()

KPI_SQL = f"""
WITH {BOUNDS},
monthly AS (
    SELECT CAST(date_trunc('month', invoicedate) AS DATE) AS month, SUM(revenue) AS revenue
    FROM da.online_retail_ii
    WHERE {{{{country}}}}
    GROUP BY 1
)
SELECT b.last_month AS month,
       ROUND(CAST(COALESCE(cur.revenue, 0) AS NUMERIC(18, 6)), 2) AS revenue,
       ROUND(CAST(COALESCE(cur.revenue, 0) / NULLIF(prev.revenue, 0) - 1 AS NUMERIC(18, 6)), 4) AS mom_pct
FROM bounds b
LEFT JOIN monthly cur ON cur.month = b.last_month
LEFT JOIN monthly prev ON prev.month = CAST(b.last_month - INTERVAL '1 month' AS DATE)
""".strip()

TREND_SQL = f"""
WITH {BOUNDS}
SELECT CAST(date_trunc('month', invoicedate) AS DATE) AS month,
       ROUND(CAST(SUM(revenue) AS NUMERIC(18, 6)), 2) AS revenue
FROM da.online_retail_ii, bounds
WHERE {{{{country}}}}
  AND CAST(date_trunc('month', invoicedate) AS DATE) <= bounds.last_month
GROUP BY 1
ORDER BY 1
""".strip()

TOP_PRODUCTS_SQL = f"""
WITH {BOUNDS}
SELECT stockcode,
       MIN(description) AS description,
       ROUND(CAST(SUM(revenue) AS NUMERIC(18, 6)), 2) AS revenue
FROM da.online_retail_ii, bounds
WHERE {{{{country}}}}
  AND invoicedate >= bounds.last_month
  AND invoicedate < bounds.last_month + INTERVAL '1 month'
  AND LEFT(stockcode, 1) BETWEEN '0' AND '9'
GROUP BY stockcode
ORDER BY revenue DESC, stockcode
LIMIT 10
""".strip()

MONTHLY_TABLE_SQL = f"""
WITH {BOUNDS}
SELECT CAST(date_trunc('month', invoicedate) AS DATE) AS month,
       COUNT(DISTINCT invoice) AS orders,
       COUNT(DISTINCT customer_id) AS customers,
       ROUND(CAST(SUM(revenue) / COUNT(DISTINCT invoice) AS NUMERIC(18, 6)), 2) AS aov
FROM da.online_retail_ii, bounds
WHERE {{{{country}}}}
  AND CAST(date_trunc('month', invoicedate) AS DATE) <= bounds.last_month
GROUP BY 1
ORDER BY 1 DESC
""".strip()

# key -> (tên card, display, SQL)
CARDS = {
    "kpi": ("Doanh thu tháng đủ gần nhất", "scalar", KPI_SQL),
    "trend": ("Doanh thu theo tháng (tháng đủ)", "line", TREND_SQL),
    "top_products": ("Top 10 sản phẩm tháng đủ gần nhất", "row", TOP_PRODUCTS_SQL),
    "monthly_table": ("Đơn, khách, AOV theo tháng", "table", MONTHLY_TABLE_SQL),
}

# key -> (row, col, size_x, size_y): KPI góc trái trên, trend bên phải, breakdown và bảng chi tiết ở dưới
LAYOUT = {
    "kpi": (0, 0, 6, 8),
    "trend": (0, 6, 18, 8),
    "top_products": (8, 0, 12, 9),
    "monthly_table": (8, 12, 12, 9),
}

PARAMETER = {"id": "country", "name": "Quốc gia", "slug": "country", "type": "string/=", "sectionId": "string"}


# ---------- helper có sẵn (đã làm ở bài Basic 02) ----------

def find_ids(session, database: str = "de") -> dict:
    """{"database_id", "country_field_id"} của da.online_retail_ii."""
    dbs = session.get("/api/database").json()
    dbs = dbs["data"] if isinstance(dbs, dict) else dbs
    db_id = next(d["id"] for d in dbs if d["name"] == database)
    meta = session.get(f"/api/database/{db_id}/metadata").json()
    table = next(t for t in meta["tables"] if t["schema"] == "da" and t["name"] == "online_retail_ii")
    return {"database_id": db_id, "country_field_id": next(f["id"] for f in table["fields"] if f["name"] == "country")}


def upsert_card(session, card: dict) -> int:
    existing = [c for c in session.get("/api/card").json() if c["name"] == card["name"] and not c.get("archived")]
    if existing:
        session.put(f"/api/card/{existing[0]['id']}", json=card).raise_for_status()
        return existing[0]["id"]
    r = session.post("/api/card", json=card)
    r.raise_for_status()
    return r.json()["id"]


# ---------- phần bài ----------

def card_payload(key: str, ids: dict, prefix: str = PREFIX) -> dict:
    """Payload POST /api/card cho card `key` trong CARDS: SQL có field filter {{country}} trỏ vào cột country."""
    name, display, sql = CARDS[key]
    return {
        "name": f"{prefix}{name}",
        "display": display,
        "visualization_settings": {},
        "dataset_query": {
            "database": ids["database_id"],
            "type": "native",
            "native": {
                "query": sql,
                "template-tags": {
                    "country": {
                        "id": f"{key}-country",
                        "name": "country",
                        "display-name": "Quốc gia",
                        "type": "dimension",
                        "dimension": ["field", ids["country_field_id"], None],
                        "widget-type": "string/=",
                    }
                },
            },
        },
    }


def dashcards(card_ids: dict[str, int]) -> list[dict]:
    """Danh sách dashcard cho PUT /api/dashboard/<id>: vị trí theo LAYOUT, nối bộ lọc country vào mọi card."""
    out = []
    for n, (key, card_id) in enumerate(card_ids.items(), 1):
        row, col, size_x, size_y = LAYOUT[key]
        out.append({
            "id": -n,  # id âm: dashcard mới
            "card_id": card_id,
            "row": row,
            "col": col,
            "size_x": size_x,
            "size_y": size_y,
            "parameter_mappings": [
                {"parameter_id": PARAMETER["id"], "card_id": card_id, "target": ["dimension", ["template-tag", "country"]]}
            ],
        })
    return out


def validate_layout(cards: list[dict], columns: int = GRID_COLUMNS) -> list[str]:
    """Liệt kê lỗi bố cục: kích thước < 1, tràn lưới (col < 0, row < 0, col + size_x > columns), hai card chồng nhau."""
    problems = []
    for c in cards:
        if c["size_x"] < 1 or c["size_y"] < 1:
            problems.append(f"card {c['card_id']}: kích thước phải >= 1")
        if c["col"] < 0 or c["row"] < 0 or c["col"] + c["size_x"] > columns:
            problems.append(f"card {c['card_id']}: tràn lưới {columns} cột")
    for i, a in enumerate(cards):
        for b in cards[i + 1:]:
            if (a["col"] < b["col"] + b["size_x"] and b["col"] < a["col"] + a["size_x"]
                    and a["row"] < b["row"] + b["size_y"] and b["row"] < a["row"] + a["size_y"]):
                problems.append(f"card {a['card_id']} và {b['card_id']} chồng nhau")
    return problems


def upsert_dashboard(session, name: str, card_ids: dict[str, int]) -> int:
    """Tạo (hoặc tìm theo tên) dashboard có tham số PARAMETER, rồi đặt dashcards. Trả id."""
    found = [d for d in session.get("/api/dashboard").json() if d["name"] == name and not d.get("archived")]
    if found:
        dashboard_id = found[0]["id"]
    else:
        r = session.post("/api/dashboard", json={"name": name, "parameters": [PARAMETER]})
        r.raise_for_status()
        dashboard_id = r.json()["id"]
    cards = dashcards(card_ids)
    problems = validate_layout(cards)
    if problems:
        raise ValueError("; ".join(problems))
    r = session.put(f"/api/dashboard/{dashboard_id}", json={"parameters": [PARAMETER], "dashcards": cards})
    r.raise_for_status()
    return dashboard_id


def publish(session, prefix: str = PREFIX) -> dict:
    ids = find_ids(session)
    card_ids = {key: upsert_card(session, card_payload(key, ids, prefix)) for key in CARDS}
    return {"cards": card_ids, "dashboard": upsert_dashboard(session, f"{prefix}Doanh số cho Head of Sales", card_ids)}


if __name__ == "__main__":
    sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()) / "setup" / "bi"))
    import clients

    result = publish(clients.metabase_session())
    print(result)
    print(f"{clients.base_url('metabase')}/dashboard/{result['dashboard']}")
