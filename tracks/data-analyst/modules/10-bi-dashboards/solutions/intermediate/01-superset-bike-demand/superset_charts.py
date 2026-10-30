"""Dataset ảo, 3 chart và 1 dashboard nhu cầu xe đạp trên Superset, tạo bằng API (lời giải).

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

DATASET_SQL = """
SELECT CAST(dteday AS DATE) AS day,
       hr,
       CASE WHEN workingday = 1 THEN 'Ngày làm việc' ELSE 'Ngày nghỉ' END AS day_type,
       CASE weathersit
            WHEN 1 THEN '1 · Quang, ít mây'
            WHEN 2 THEN '2 · Sương mù, nhiều mây'
            WHEN 3 THEN '3 · Mưa/tuyết nhẹ'
            ELSE '4 · Mưa lớn, bão'
       END AS weather,
       season,
       cnt,
       casual,
       registered
FROM da.bike_hour
""".strip()

METRICS = [
    {"metric_name": "total_rides", "verbose_name": "Tổng lượt thuê", "expression": "SUM(cnt)"},
    {"metric_name": "avg_rides_per_hour", "verbose_name": "Lượt thuê TB mỗi giờ", "expression": "AVG(cnt)"},
    {
        "metric_name": "casual_share",
        "verbose_name": "Tỉ trọng khách vãng lai",
        "expression": "SUM(casual) * 1.0 / NULLIF(SUM(cnt), 0)",
    },
]


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
    """Dataset ảo (virtual dataset) tên `table_name` trong schema `da`, có các saved metric. Trả id."""
    found = session.get("/api/v1/dataset/", params={"q": rison_eq("table_name", table_name)}).json()["result"]
    if found:
        dataset_id = found[0]["id"]
        r = session.put(f"/api/v1/dataset/{dataset_id}", json={"sql": sql})
        r.raise_for_status()
        session.put(f"/api/v1/dataset/{dataset_id}/refresh").raise_for_status()  # đọc lại cột theo SQL mới
    else:
        r = session.post("/api/v1/dataset/", json={"database": database_id, "schema": "da", "table_name": table_name, "sql": sql})
        r.raise_for_status()
        dataset_id = r.json()["id"]
    current = session.get(f"/api/v1/dataset/{dataset_id}").json()["result"]["metrics"]
    ids = {m["metric_name"]: m["id"] for m in current}
    payload = [dict(m, id=ids[m["metric_name"]]) if m["metric_name"] in ids else dict(m) for m in metrics]
    session.put(f"/api/v1/dataset/{dataset_id}", json={"metrics": payload}).raise_for_status()
    return dataset_id


def chart_payloads(dataset_id: int, prefix: str = PREFIX) -> list[dict]:
    """Payload POST /api/v1/chart/ cho 3 chart: line theo giờ, bar theo thời tiết, big number tỉ trọng."""
    specs = [
        (
            f"{prefix}Lượt thuê TB mỗi giờ: ngày làm việc vs ngày nghỉ",
            "echarts_timeseries_line",
            {"x_axis": "hr", "metrics": ["avg_rides_per_hour"], "groupby": ["day_type"]},
            {"columns": ["hr", "day_type"], "metrics": ["avg_rides_per_hour"], "orderby": [["hr", True]]},
        ),
        (
            f"{prefix}Lượt thuê TB mỗi giờ theo thời tiết",
            "echarts_timeseries_bar",
            {"x_axis": "weather", "metrics": ["avg_rides_per_hour"], "groupby": []},
            {"columns": ["weather"], "metrics": ["avg_rides_per_hour"], "orderby": [["weather", True]]},
        ),
        (
            f"{prefix}Tỉ trọng khách vãng lai",
            "big_number_total",
            {"metric": "casual_share", "y_axis_format": ".1%"},
            {"columns": [], "metrics": ["casual_share"]},
        ),
    ]
    out = []
    for name, viz, form, query in specs:
        params = {"viz_type": viz, "datasource": f"{dataset_id}__table", "row_limit": 10000, **form}
        query_context = {
            "datasource": {"id": dataset_id, "type": "table"},
            "queries": [{**query, "row_limit": 10000}],
            "form_data": params,
            "result_format": "json",
            "result_type": "full",
        }
        out.append({
            "slice_name": name,
            "viz_type": viz,
            "datasource_id": dataset_id,
            "datasource_type": "table",
            "params": json.dumps(params, ensure_ascii=False),
            "query_context": json.dumps(query_context, ensure_ascii=False),
        })
    return out


def upsert_chart(session, payload: dict) -> int:
    found = session.get("/api/v1/chart/", params={"q": rison_eq("slice_name", payload["slice_name"])}).json()["result"]
    if found:
        chart_id = found[0]["id"]
        session.put(f"/api/v1/chart/{chart_id}", json=payload).raise_for_status()
        return chart_id
    r = session.post("/api/v1/chart/", json=payload)
    r.raise_for_status()
    return r.json()["id"]


def dashboard_layout(chart_ids: list[int], per_row: int = 2) -> dict:
    """position_json (bản v2) xếp chart thành các hàng, mỗi hàng tối đa `per_row` chart, chia đều 12 cột."""
    width = 12 // per_row
    rows = [chart_ids[i:i + per_row] for i in range(0, len(chart_ids), per_row)]
    pos: dict = {
        "DASHBOARD_VERSION_KEY": "v2",
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "parents": ["ROOT_ID"]},
    }
    for n, row in enumerate(rows, 1):
        row_id = f"ROW-{n}"
        pos["GRID_ID"]["children"].append(row_id)
        pos[row_id] = {"type": "ROW", "id": row_id, "children": [], "parents": ["ROOT_ID", "GRID_ID"],
                       "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        for chart_id in row:
            key = f"CHART-{chart_id}"
            pos[row_id]["children"].append(key)
            pos[key] = {"type": "CHART", "id": key, "children": [], "parents": ["ROOT_ID", "GRID_ID", row_id],
                        "meta": {"chartId": chart_id, "width": width, "height": 50}}
    return pos


def upsert_dashboard(session, title: str, chart_ids: list[int]) -> int:
    found = session.get("/api/v1/dashboard/", params={"q": rison_eq("dashboard_title", title)}).json()["result"]
    if found:
        dashboard_id = found[0]["id"]
    else:
        r = session.post("/api/v1/dashboard/", json={"dashboard_title": title, "published": True})
        r.raise_for_status()
        dashboard_id = r.json()["id"]
    body = {"position_json": json.dumps(dashboard_layout(chart_ids))}
    session.put(f"/api/v1/dashboard/{dashboard_id}", json=body).raise_for_status()
    for chart_id in chart_ids:  # gắn chart vào dashboard (quan hệ nhiều-nhiều nằm ở chart)
        session.put(f"/api/v1/chart/{chart_id}", json={"dashboards": [dashboard_id]}).raise_for_status()
    return dashboard_id


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
