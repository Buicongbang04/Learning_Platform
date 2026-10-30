"""Dataset ảo, 3 chart và 1 dashboard nhu cầu xe đạp trên Superset, tạo bằng API.

    uv run python tracks/data-analyst/modules/10-bi-dashboards/exercises/intermediate/01-superset-bike-demand/starter/superset_charts.py

Cần BI đang chạy (setup/SETUP.md mục 11). Mở http://localhost:8088/dashboard/list để xem dashboard.
`session` là requests.Session của setup/bi/clients.py (đã có JWT + CSRF), gọi bằng đường dẫn tương đối.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PREFIX = "DA10 · "

# TODO 1: SQL của virtual dataset trên da.bike_hour, đúng 8 cột theo thứ tự:
#   day (DATE, từ dteday đang là text), hr, day_type ('Ngày làm việc' khi workingday = 1, ngược lại 'Ngày nghỉ'),
#   weather (nhãn theo weathersit: '1 · Quang, ít mây', '2 · Sương mù, nhiều mây', '3 · Mưa/tuyết nhẹ',
#   '4 · Mưa lớn, bão'), season, cnt, casual, registered. Viết SQL chạy được cả trên Postgres và DuckDB.
DATASET_SQL = "-- TODO"

# TODO 2: ba saved metric (dict có metric_name, verbose_name, expression) theo thứ tự:
#   total_rides = tổng cnt; avg_rides_per_hour = trung bình cnt;
#   casual_share = tổng casual / tổng cnt (NULL khi tổng cnt = 0, không chia nguyên).
METRICS: list[dict] = []


# ---------- helper có sẵn ----------

def dataset_name(prefix: str) -> str:
    """Tên bảng của dataset ảo (định danh SQL): "DA10 · " -> "da10_bike_hour_demand"."""
    return re.sub(r"[^a-z0-9]+", "_", prefix.lower()).strip("_") + "_bike_hour_demand"


def rison_eq(column: str, value) -> str:
    """Tham số `q` (rison) lọc danh sách theo `column == value`, ví dụ GET /api/v1/chart/?q=..."""
    if isinstance(value, str):
        value = "'" + value.replace("!", "!!").replace("'", "!'") + "'"
    return f"(filters:!((col:{column},opr:eq,value:{value})),page_size:100)"


def find_database_id(session, name: str = "de") -> int:
    found = session.get("/api/v1/database/", params={"q": rison_eq("database_name", name)}).json()["result"]
    if not found:
        raise LookupError(f"Superset chưa có database `{name}`. Chạy: uv run python setup/bi/init_bi.py")
    return found[0]["id"]


# ---------- phần bài ----------

def upsert_dataset(session, database_id: int, table_name: str, sql: str = DATASET_SQL, metrics=METRICS) -> int:
    """Dataset ảo (virtual dataset) tên `table_name` trong schema `da`, có các saved metric. Trả id.

    Chưa có (tìm theo table_name bằng GET /api/v1/dataset/?q=rison_eq(...)): POST /api/v1/dataset/ với
    database, schema "da", table_name, sql. Có rồi: PUT sql mới rồi PUT /api/v1/dataset/<id>/refresh.
    Sau đó đặt metrics bằng PUT /api/v1/dataset/<id> {"metrics": [...]}: metric đã có cùng tên phải kèm "id"
    (đọc từ GET /api/v1/dataset/<id>, khoá result.metrics), nếu không Superset báo trùng.
    """
    # TODO 3
    raise NotImplementedError


def chart_payloads(dataset_id: int, prefix: str = PREFIX) -> list[dict]:
    """Payload POST /api/v1/chart/ cho 3 chart: line theo giờ, bar theo thời tiết, big number tỉ trọng.

    Mỗi payload: slice_name (bắt đầu bằng prefix), viz_type, datasource_id, datasource_type "table",
    params (chuỗi JSON của form_data: viz_type, datasource "<id>__table", ...) và query_context (chuỗi JSON:
    datasource {"id", "type"}, queries [một query: columns, metrics], form_data, result_format, result_type).
    Xem bảng chart trong đề bài.
    """
    # TODO 4
    raise NotImplementedError


def upsert_chart(session, payload: dict) -> int:
    """Tạo chart theo slice_name nếu chưa có, có rồi thì PUT payload. Trả id."""
    # TODO 5
    raise NotImplementedError


def dashboard_layout(chart_ids: list[int], per_row: int = 2) -> dict:
    """position_json (bản v2) xếp chart thành các hàng, mỗi hàng tối đa `per_row` chart, chia đều 12 cột.

    Cấu trúc: ROOT_ID -> GRID_ID -> các ROW-n -> các CHART-<id> (meta: chartId, width, height). Mỗi phần tử có
    "type", "id", "children"; ROW và CHART có "parents" (đường đi từ ROOT_ID). Xem ví dụ ở phần Superset của lý thuyết.
    """
    # TODO 6
    raise NotImplementedError


def upsert_dashboard(session, title: str, chart_ids: list[int]) -> int:
    """Tạo dashboard theo dashboard_title nếu chưa có (published), đặt position_json = dashboard_layout(chart_ids),
    rồi gắn từng chart vào dashboard bằng PUT /api/v1/chart/<id> {"dashboards": [dashboard_id]}. Trả id.
    """
    # TODO 7
    raise NotImplementedError


def publish(session, prefix: str = PREFIX) -> dict:
    dataset_id = upsert_dataset(session, find_database_id(session), dataset_name(prefix))
    chart_ids = [upsert_chart(session, p) for p in chart_payloads(dataset_id, prefix)]
    dashboard_id = upsert_dashboard(session, f"{prefix}Nhu cầu xe đạp theo giờ", chart_ids)
    return {"dataset": dataset_id, "charts": chart_ids, "dashboard": dashboard_id}


if __name__ == "__main__":
    sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()) / "setup" / "bi"))
    import clients

    ids = publish(clients.superset_session())
    print(ids)
    print(f"{clients.base_url('superset')}/superset/dashboard/{ids['dashboard']}/")
