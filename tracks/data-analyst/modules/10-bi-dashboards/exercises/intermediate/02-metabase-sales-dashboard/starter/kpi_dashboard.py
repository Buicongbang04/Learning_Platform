"""Dashboard doanh số cho Head of Sales trên Metabase: 4 card, bộ lọc Quốc gia, tạo bằng API.

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

# Mọi SQL: một câu SELECT chạy được trên Postgres và DuckDB, đọc da.online_retail_ii (đã là dòng hợp lệ, có cột
# revenue), có field filter `WHERE {{country}}` (hoặc `AND {{country}}`) trên bảng KHÔNG đặt alias, và chỉ dùng
# tháng đủ (`bounds.last_month` ở trên). Làm tròn tiền 2 số, tỉ lệ 4 số: ROUND(CAST(x AS NUMERIC(18, 6)), n).

# TODO 1: một dòng: month (= last_month), revenue (doanh thu tháng đó của nước đang lọc), mom_pct (so với tháng
#   trước; NULL khi tháng trước bằng 0). Gợi ý: CTE `monthly` có WHERE {{country}}, rồi LEFT JOIN vào bounds.
KPI_SQL = "-- TODO"

# TODO 2: month, revenue theo tháng, chỉ các tháng <= last_month, sắp tăng dần.
TREND_SQL = "-- TODO"

# TODO 3: stockcode, description (MIN), revenue của tháng last_month; chỉ mã sản phẩm (ký tự đầu là chữ số, bỏ
#   POST, DOT, M...); sắp revenue giảm dần rồi stockcode; 10 dòng.
TOP_PRODUCTS_SQL = "-- TODO"

# TODO 4: month, orders (hoá đơn khác nhau), customers (khách có mã khác nhau), aov (revenue / orders); chỉ tháng
#   <= last_month; tháng mới nhất lên đầu.
MONTHLY_TABLE_SQL = "-- TODO"

# key -> (tên card, display, SQL)
CARDS = {
    "kpi": ("Doanh thu tháng đủ gần nhất", "scalar", KPI_SQL),
    "trend": ("Doanh thu theo tháng (tháng đủ)", "line", TREND_SQL),
    "top_products": ("Top 10 sản phẩm tháng đủ gần nhất", "row", TOP_PRODUCTS_SQL),
    "monthly_table": ("Đơn, khách, AOV theo tháng", "table", MONTHLY_TABLE_SQL),
}

# TODO 5: key -> (row, col, size_x, size_y) trên lưới 24 cột: KPI ở góc trái trên (row 0, col 0), trend cùng
#   hàng bên phải, top_products và monthly_table ở hàng dưới trend. Không chồng nhau, không tràn lưới.
LAYOUT: dict[str, tuple[int, int, int, int]] = {}

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
    # TODO 6: {"name": prefix + tên, "display", "visualization_settings": {}, "dataset_query": {database, type "native",
    #   native: {query, template-tags: {"country": {id, name "country", display-name, type "dimension",
    #   dimension ["field", country_field_id, None], widget-type "string/="}}}}}
    raise NotImplementedError


def dashcards(card_ids: dict[str, int]) -> list[dict]:
    """Danh sách dashcard cho PUT /api/dashboard/<id>: vị trí theo LAYOUT, nối bộ lọc country vào mọi card."""
    # TODO 7: mỗi card một dict {id (âm: -1, -2...), card_id, row, col, size_x, size_y, parameter_mappings:
    #   [{"parameter_id": "country", "card_id", "target": ["dimension", ["template-tag", "country"]]}]}
    raise NotImplementedError


def validate_layout(cards: list[dict], columns: int = GRID_COLUMNS) -> list[str]:
    """Liệt kê lỗi bố cục: kích thước < 1, tràn lưới (col < 0, row < 0, col + size_x > columns), hai card chồng nhau."""
    # TODO 8: trả list chuỗi mô tả lỗi; bố cục đúng trả []. Hai card chỉ chạm cạnh không tính là chồng.
    raise NotImplementedError


def upsert_dashboard(session, name: str, card_ids: dict[str, int]) -> int:
    """Tạo (hoặc tìm theo tên) dashboard có tham số PARAMETER, rồi đặt dashcards. Trả id."""
    # TODO 9: GET /api/dashboard (tìm theo name, bỏ archived), POST /api/dashboard {"name", "parameters": [PARAMETER]}
    #   nếu chưa có; kiểm validate_layout(dashcards(...)); PUT /api/dashboard/<id> {"parameters", "dashcards"}.
    raise NotImplementedError


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
