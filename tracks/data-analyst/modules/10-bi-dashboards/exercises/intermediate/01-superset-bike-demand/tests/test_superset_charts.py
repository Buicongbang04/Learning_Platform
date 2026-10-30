import json
import re
import sys
import uuid

import duckdb
import pytest

import testkit
from testkit import Exercise

ex = Exercise(__file__)
sys.path.insert(0, str(testkit.ROOT / "setup" / "bi"))

BI_START = (
    "docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase superset "
    "&& uv run python setup/bi/load_da.py && uv run python setup/bi/init_bi.py"
)


@pytest.fixture
def sc():
    return ex.module("superset_charts.py")


# ---------- SQL và metric: chạy trên DuckDB, bảng da.bike_hour nhỏ cùng schema với Postgres ----------

def tiny_db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE SCHEMA da")
    con.execute(
        "CREATE TABLE da.bike_hour (instant BIGINT, dteday VARCHAR, season BIGINT, yr BIGINT, mnth BIGINT, hr BIGINT, "
        "holiday BIGINT, weekday BIGINT, workingday BIGINT, weathersit BIGINT, temp DOUBLE, atemp DOUBLE, hum DOUBLE, "
        "windspeed DOUBLE, casual BIGINT, registered BIGINT, cnt BIGINT)"
    )
    rows = [  # dteday, hr, workingday, weathersit, casual, registered
        ("2011-01-03", 8, 1, 1, 5, 95), ("2011-01-03", 17, 1, 2, 10, 190), ("2011-01-08", 8, 0, 1, 30, 30),
        ("2011-01-08", 13, 0, 3, 40, 0), ("2011-01-09", 13, 0, 4, 0, 0),
    ]
    con.executemany(
        "INSERT INTO da.bike_hour VALUES (?, ?, 1, 0, 1, ?, 0, 1, ?, ?, 0.2, 0.2, 0.5, 0.1, ?, ?, ?)",
        [(i, d, hr, wd, ws, c, r, c + r) for i, (d, hr, wd, ws, c, r) in enumerate(rows, 1)],
    )
    return con


def test_dataset_sql(sc):
    rel = tiny_db().execute(f"SELECT * FROM ({sc.DATASET_SQL}) t ORDER BY day, hr")
    cols = [d[0] for d in rel.description]
    assert cols == ["day", "hr", "day_type", "weather", "season", "cnt", "casual", "registered"]
    rows = rel.fetchall()
    assert str(rows[0][0]) == "2011-01-03", "day là kiểu DATE (dteday trong Postgres đang là text)"
    assert [r[2] for r in rows] == ["Ngày làm việc", "Ngày làm việc", "Ngày nghỉ", "Ngày nghỉ", "Ngày nghỉ"]
    assert [r[3] for r in rows] == ["1 · Quang, ít mây", "2 · Sương mù, nhiều mây", "1 · Quang, ít mây",
                                    "3 · Mưa/tuyết nhẹ", "4 · Mưa lớn, bão"]


def test_metrics(sc):
    names = [m["metric_name"] for m in sc.METRICS]
    assert names == ["total_rides", "avg_rides_per_hour", "casual_share"]
    con = tiny_db()
    got = [con.execute(f"SELECT {m['expression']} FROM ({sc.DATASET_SQL}) t").fetchone()[0] for m in sc.METRICS]
    assert got[0] == 400 and got[1] == pytest.approx(80.0)
    assert got[2] == pytest.approx(85 / 400), "Tỉ trọng = tổng casual / tổng cnt (nhân 1.0 để không chia nguyên)"
    zero = con.execute(f"SELECT {sc.METRICS[2]['expression']} FROM ({sc.DATASET_SQL}) t WHERE cnt = 0").fetchone()[0]
    assert zero is None, "Không có lượt thuê nào thì tỉ trọng là NULL, không lỗi chia cho 0"


def test_chart_payloads(sc):
    charts = sc.chart_payloads(7, prefix="X · ")
    assert [c["viz_type"] for c in charts] == ["echarts_timeseries_line", "echarts_timeseries_bar", "big_number_total"]
    metric_names = {m["metric_name"] for m in sc.METRICS}
    for c in charts:
        assert c["slice_name"].startswith("X · ")
        assert (c["datasource_id"], c["datasource_type"]) == (7, "table")
        params, qc = json.loads(c["params"]), json.loads(c["query_context"])
        assert params["viz_type"] == c["viz_type"] and params["datasource"] == "7__table"
        assert qc["datasource"] == {"id": 7, "type": "table"} and len(qc["queries"]) == 1
        assert set(qc["queries"][0]["metrics"]) <= metric_names, "Chart dùng saved metric của dataset, theo tên"
    line, bar, big = (json.loads(c["params"]) for c in charts)
    assert line["x_axis"] == "hr" and line["groupby"] == ["day_type"] and line["metrics"] == ["avg_rides_per_hour"]
    assert bar["x_axis"] == "weather" and bar["metrics"] == ["avg_rides_per_hour"]
    assert big["metric"] == "casual_share"
    line_q = json.loads(charts[0]["query_context"])["queries"][0]
    assert set(line_q["columns"]) == {"hr", "day_type"}


def test_dashboard_layout(sc):
    pos = sc.dashboard_layout([11, 12, 13], per_row=2)
    assert pos["DASHBOARD_VERSION_KEY"] == "v2" and pos["ROOT_ID"]["children"] == ["GRID_ID"]
    rows = pos["GRID_ID"]["children"]
    assert len(rows) == 2, "3 chart, tối đa 2 chart mỗi hàng: 2 hàng"
    seen = []
    for row_id in rows:
        row = pos[row_id]
        assert row["type"] == "ROW"
        assert sum(pos[k]["meta"]["width"] for k in row["children"]) <= 12, "Lưới Superset rộng 12 cột"
        for key in row["children"]:
            assert pos[key]["type"] == "CHART" and pos[key]["parents"][-1] == row_id
            seen.append(pos[key]["meta"]["chartId"])
    assert seen == [11, 12, 13], "Mỗi chart xuất hiện đúng một lần, theo thứ tự"


# ---------- Superset giả trong bộ nhớ ----------

class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code, self._payload, self.ok = status_code, payload, status_code < 400

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSuperset:
    KEY = {"chart": "slice_name", "dashboard": "dashboard_title", "dataset": "table_name", "database": "database_name"}

    def __init__(self):
        self.store = {"database": {1: {"id": 1, "database_name": "examples"}, 4: {"id": 4, "database_name": "de"}},
                      "dataset": {}, "chart": {9: {"id": 9, "slice_name": "Chart của người khác", "dashboards": []}},
                      "dashboard": {}}
        self.next_id = 20

    def _parse(self, url):
        m = re.fullmatch(r"/api/v1/(\w+)/(?:(\d+)(?:/(\w+))?)?/?", url)
        assert m, f"endpoint không có trong bài: {url}"
        return m.group(1), (int(m.group(2)) if m.group(2) else None), m.group(3)

    def get(self, url, params=None, **kwargs):
        kind, obj_id, sub = self._parse(url)
        if obj_id is not None:
            return FakeResponse(200, {"result": self.store[kind][obj_id]})
        items = list(self.store[kind].values())
        q = (params or {}).get("q", "")
        m = re.search(r"col:(\w+),opr:eq,value:(?:'((?:[^'!]|!.)*)'|(\d+))", q)
        if m:
            value = re.sub(r"!(.)", r"\1", m.group(2)) if m.group(2) is not None else int(m.group(3))
            items = [i for i in items if i.get(m.group(1)) == value]
        return FakeResponse(200, {"count": len(items), "result": items})

    def post(self, url, json=None, **kwargs):
        kind, _, _ = self._parse(url)
        obj = dict(json, id=self.next_id)
        if kind == "dataset":
            obj.setdefault("metrics", [{"id": 1000 + self.next_id, "metric_name": "count", "expression": "COUNT(*)"}])
        self.store[kind][self.next_id] = obj
        self.next_id += 1
        return FakeResponse(201, {"id": obj["id"], "result": json})

    def put(self, url, json=None, **kwargs):
        kind, obj_id, sub = self._parse(url)
        if sub == "refresh":
            return FakeResponse(200, {"message": "OK"})
        obj = self.store[kind][obj_id]
        json = dict(json or {})
        if kind == "dataset" and "metrics" in json:
            names = [m["metric_name"] for m in json["metrics"]]
            assert len(names) == len(set(names))
            for m in json["metrics"]:
                if "id" not in m and any(x["metric_name"] == m["metric_name"] for x in obj["metrics"]):
                    return FakeResponse(422, {"message": f"metric {m['metric_name']} đã có (thiếu id khi cập nhật)"})
            json["metrics"] = [dict(m, id=m.get("id", 5000 + i)) for i, m in enumerate(json["metrics"])]
        obj.update(json)
        return FakeResponse(200, {"id": obj_id, "result": json})


def test_publish_offline_idempotent(sc):
    fake = FakeSuperset()
    first = sc.publish(fake, prefix="T · ")
    second = sc.publish(fake, prefix="T · ")
    assert first == second, "Chạy lại không tạo thêm dataset/chart/dashboard"
    ds = fake.store["dataset"][first["dataset"]]
    assert ds["table_name"] == "t_bike_hour_demand" and ds["database"] == 4 and ds["schema"] == "da"
    assert "da.bike_hour" in ds["sql"]
    assert sorted(m["metric_name"] for m in ds["metrics"]) == ["avg_rides_per_hour", "casual_share", "total_rides"]
    assert len(first["charts"]) == 3 and len(fake.store["chart"]) == 4
    for chart_id in first["charts"]:
        assert fake.store["chart"][chart_id]["dashboards"] == [first["dashboard"]], "Mỗi chart được gắn vào dashboard"
    dash = fake.store["dashboard"][first["dashboard"]]
    assert dash["dashboard_title"] == "T · Nhu cầu xe đạp theo giờ"
    assert json.loads(dash["position_json"]) == sc.dashboard_layout(first["charts"])
    assert fake.store["chart"][9]["dashboards"] == [], "Không đụng chart khác"


# ---------- Superset thật ----------

@pytest.fixture(scope="module")
def superset():
    for name in ("postgres", "superset"):
        if not testkit.service_up(name):
            pytest.skip(f"Dịch vụ {name} chưa chạy. Bật BI bằng: {BI_START}")
        ex.require_service(name)
    import clients

    return clients.superset_session()


def _all(session, kind):
    out, page = [], 0
    while True:
        res = session.get(f"/api/v1/{kind}/", params={"q": f"(page:{page},page_size:100)"}).json()
        out += res["result"]
        if len(out) >= res["count"] or not res["result"]:
            return out
        page += 1


@pytest.fixture(scope="module")
def run(superset):
    """Tên riêng cho lần chạy test; khi xong xoá dashboard, chart, dataset mang tên đó (không đụng của bạn)."""
    tag = uuid.uuid4().hex[:8]
    state = {"prefix": f"test-{tag} · ", "table": f"test_{tag}_bike_hour_demand"}
    yield state
    for d in _all(superset, "dashboard"):
        if d["dashboard_title"].startswith(state["prefix"]):
            superset.delete(f"/api/v1/dashboard/{d['id']}")
    for c in _all(superset, "chart"):
        if c["slice_name"].startswith(state["prefix"]):
            superset.delete(f"/api/v1/chart/{c['id']}")
    for t in _all(superset, "dataset"):
        if t["table_name"] == state["table"]:
            superset.delete(f"/api/v1/dataset/{t['id']}")


def published(superset, run):
    if "ids" not in run:
        sc = ex.module("superset_charts.py")
        run["ids"] = sc.publish(superset, prefix=run["prefix"])
        run["again"] = sc.publish(superset, prefix=run["prefix"])
    return run["ids"]


def chart_rows(superset, chart_id):
    r = superset.get(f"/api/v1/chart/{chart_id}/data/")
    assert r.ok, r.text[:300]
    return r.json()["result"][0]["data"]


def test_real_publish(superset, run):
    ids = published(superset, run)
    assert run["again"] == ids, "Chạy publish lần hai phải trả cùng id"
    ds = superset.get(f"/api/v1/dataset/{ids['dataset']}").json()["result"]
    assert ds["table_name"] == run["table"] and ds["kind"] == "virtual"
    assert {m["metric_name"] for m in ds["metrics"]} >= {"total_rides", "avg_rides_per_hour", "casual_share"}
    charts = superset.get(f"/api/v1/dashboard/{ids['dashboard']}/charts").json()["result"]
    assert len(charts) == 3


def test_real_hourly_profile(superset, run):
    ids = published(superset, run)
    rows = chart_rows(superset, ids["charts"][0])
    avg = {(r["hr"], r["day_type"]): r["avg_rides_per_hour"] for r in rows}
    assert len(avg) == 48
    assert avg[(17, "Ngày làm việc")] == pytest.approx(525.3, abs=0.05)
    assert avg[(8, "Ngày làm việc")] == pytest.approx(477.0, abs=0.05)
    assert avg[(13, "Ngày nghỉ")] == pytest.approx(372.7, abs=0.05)


def test_real_weather_and_share(superset, run):
    ids = published(superset, run)
    weather = {r["weather"]: r["avg_rides_per_hour"] for r in chart_rows(superset, ids["charts"][1])}
    assert weather["1 · Quang, ít mây"] == pytest.approx(204.87, abs=0.01)
    assert weather["3 · Mưa/tuyết nhẹ"] == pytest.approx(111.58, abs=0.01)
    share = chart_rows(superset, ids["charts"][2])[0]["casual_share"]
    assert share == pytest.approx(0.1883, abs=1e-4)
