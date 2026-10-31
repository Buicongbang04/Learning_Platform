import datetime as dt
import sys
import uuid

import duckdb
import pytest
import requests

import testkit
from testkit import Exercise

ex = Exercise(__file__)
sys.path.insert(0, str(testkit.ROOT / "setup" / "bi"))

BI_START = (
    "docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase superset "
    "&& uv run python setup/bi/load_da.py && uv run python setup/bi/init_bi.py"
)


@pytest.fixture
def kd():
    return ex.module("kpi_dashboard.py")


# ---------- SQL: chạy trên DuckDB, giả lập cách Metabase thay field filter {{country}} ----------

def render(sql: str, country: str | None = None) -> str:
    """Metabase thay `{{country}}` bằng điều kiện trên cột đầy đủ tên bảng, hoặc `1 = 1` khi bộ lọc trống."""
    assert "{{country}}" in sql, "SQL phải có field filter {{country}} (WHERE {{country}})"
    cond = "1 = 1" if country is None else f"\"da\".\"online_retail_ii\".\"country\" = '{country}'"
    return sql.replace("{{country}}", cond)


def tiny_db(last_day: str = "2011-11-15 12:00") -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    con.execute("CREATE SCHEMA da")
    con.execute(
        "CREATE TABLE da.online_retail_ii (invoice VARCHAR, stockcode VARCHAR, description VARCHAR, quantity BIGINT, "
        "invoicedate TIMESTAMP, price DOUBLE, customer_id BIGINT, country VARCHAR, revenue DOUBLE)"
    )
    rows = [  # invoice, stockcode, description, ngày giờ, khách, nước, doanh thu
        ("1", "20001", "LAMP", "2011-09-05 10:00", 1, "United Kingdom", 100.0),
        ("2", "20001", "LAMP", "2011-09-20 10:00", 2, "Germany", 50.0),
        ("3", "20001", "LAMP", "2011-10-03 09:00", 1, "United Kingdom", 120.0),
        ("3", "20002", "CUP", "2011-10-03 09:00", 1, "United Kingdom", 30.0),
        ("4", "POST", "POSTAGE", "2011-10-10 09:00", 2, "Germany", 500.0),     # phí ship, không phải sản phẩm
        ("4", "20002", "CUP", "2011-10-10 09:00", 2, "Germany", 40.0),
        ("5", "20003", "BAG", "2011-10-31 23:30", None, "Germany", 60.0),      # khách vãng lai, phút cuối tháng
        ("6", "20003", "BAG", last_day, 1, "United Kingdom", 999.0),          # tháng chưa đủ
    ]
    con.executemany("INSERT INTO da.online_retail_ii VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)",
                    [(i, s, d, t, r, c, n, r) for i, s, d, t, c, n, r in rows])
    return con


def q(con, sql, country=None):
    rel = con.execute(render(sql, country))
    return [d[0] for d in rel.description], rel.fetchall()


def test_kpi_thang_du_gan_nhat(kd):
    con = tiny_db()
    cols, rows = q(con, kd.KPI_SQL)
    assert cols == ["month", "revenue", "mom_pct"]
    assert rows[0][0] == dt.date(2011, 10, 1), "Dữ liệu tới 15/11: tháng đủ gần nhất là 10/2011"
    assert float(rows[0][1]) == pytest.approx(750.0)
    assert float(rows[0][2]) == pytest.approx(750 / 150 - 1, abs=1e-4)
    _, rows = q(con, kd.KPI_SQL, "Germany")
    assert rows[0][0] == dt.date(2011, 10, 1), "Mốc tháng đủ tính trên toàn bộ dữ liệu, không theo nước đang lọc"
    assert float(rows[0][1]) == pytest.approx(600.0) and float(rows[0][2]) == pytest.approx(11.0, abs=1e-4)
    _, rows = q(tiny_db(last_day="2011-11-30 18:00"), kd.KPI_SQL)
    assert rows[0][0] == dt.date(2011, 11, 1), "Dữ liệu tới ngày cuối tháng: tháng đó đã đủ"
    assert float(rows[0][1]) == pytest.approx(999.0)


def test_trend_bo_thang_chua_du(kd):
    cols, rows = q(tiny_db(), kd.TREND_SQL)
    assert cols == ["month", "revenue"]
    assert [r[0] for r in rows] == [dt.date(2011, 9, 1), dt.date(2011, 10, 1)], "Không vẽ tháng 11 (chưa đủ)"
    assert [float(r[1]) for r in rows] == pytest.approx([150.0, 750.0])
    _, rows = q(tiny_db(), kd.TREND_SQL, "United Kingdom")
    assert [float(r[1]) for r in rows] == pytest.approx([100.0, 150.0])


def test_top_products_chi_san_pham(kd):
    cols, rows = q(tiny_db(), kd.TOP_PRODUCTS_SQL)
    assert cols == ["stockcode", "description", "revenue"]
    assert [(r[0], float(r[2])) for r in rows] == [("20001", 120.0), ("20002", 70.0), ("20003", 60.0)], (
        "Chỉ tháng đủ gần nhất, bỏ mã không phải sản phẩm (POST...), sắp giảm dần")
    _, rows = q(tiny_db(), kd.TOP_PRODUCTS_SQL, "Germany")
    assert [r[0] for r in rows] == ["20003", "20002"]


def test_monthly_table(kd):
    cols, rows = q(tiny_db(), kd.MONTHLY_TABLE_SQL)
    assert cols == ["month", "orders", "customers", "aov"]
    assert [r[0] for r in rows] == [dt.date(2011, 10, 1), dt.date(2011, 9, 1)], "Tháng mới nhất lên đầu bảng"
    oct_ = rows[0]
    assert (oct_[1], oct_[2]) == (3, 2), "orders = hoá đơn khác nhau; customers bỏ khách vãng lai"
    assert float(oct_[3]) == pytest.approx(250.0)


def test_card_payload(kd):
    assert list(kd.CARDS) == ["kpi", "trend", "top_products", "monthly_table"]
    assert [kd.CARDS[k][1] for k in kd.CARDS] == ["scalar", "line", "row", "table"]
    ids = {"database_id": 2, "country_field_id": 94}
    card = kd.card_payload("trend", ids, prefix="X · ")
    assert card["name"] == "X · " + kd.CARDS["trend"][0] and card["display"] == "line"
    native = card["dataset_query"]["native"]
    assert card["dataset_query"]["type"] == "native" and card["dataset_query"]["database"] == 2
    assert native["query"] == kd.TREND_SQL
    tag = native["template-tags"]["country"]
    assert tag["type"] == "dimension", "Field filter: tag kiểu dimension, không phải text"
    assert tag["dimension"] == ["field", 94, None] and tag["widget-type"] == "string/="
    assert tag["name"] == "country"


def test_layout(kd):
    cards = kd.dashcards({"kpi": 1, "trend": 2, "top_products": 3, "monthly_table": 4})
    assert [c["card_id"] for c in cards] == [1, 2, 3, 4]
    assert kd.validate_layout(cards) == []
    by_id = {c["card_id"]: c for c in cards}
    assert by_id[1]["row"] == 0 and by_id[1]["col"] == 0, "KPI ở góc trái trên"
    assert min(by_id[3]["row"], by_id[4]["row"]) >= by_id[2]["row"] + 1, "Breakdown và bảng chi tiết nằm dưới trend"
    for c in cards:
        assert c["parameter_mappings"] == [
            {"parameter_id": "country", "card_id": c["card_id"], "target": ["dimension", ["template-tag", "country"]]}
        ], "Mọi card nối với bộ lọc Quốc gia"


def test_validate_layout_bat_loi(kd):
    def card(cid, row, col, w, h):
        return {"card_id": cid, "row": row, "col": col, "size_x": w, "size_y": h}

    assert kd.validate_layout([card(1, 0, 0, 12, 4), card(2, 0, 12, 12, 4), card(3, 4, 0, 24, 6)]) == []
    assert len(kd.validate_layout([card(1, 0, 0, 12, 4), card(2, 3, 6, 12, 4)])) == 1, "Hai card chồng nhau"
    assert len(kd.validate_layout([card(1, 0, 14, 12, 4)])) == 1, "Tràn lưới 24 cột"
    assert kd.validate_layout([card(1, 0, 0, 12, 4), card(2, 4, 0, 12, 4)]) == [], "Chạm cạnh không phải chồng"
    assert len(kd.validate_layout([card(1, 0, 0, 0, 4)])) >= 1


# ---------- Metabase thật ----------

@pytest.fixture(scope="module")
def metabase():
    for name in ("postgres", "metabase"):
        if not testkit.service_up(name):
            pytest.skip(f"Dịch vụ {name} chưa chạy. Bật BI bằng: {BI_START}")
        ex.require_service(name)
    import clients

    try:
        return clients.metabase_session()
    except RuntimeError as e:
        pytest.skip(str(e))


def list_for_teardown(session, url, prefix, **kwargs):
    """GET danh sách cho teardown; lỗi (vd. session hết hạn) thì báo rõ cần dọn tay object của lần chạy."""
    try:
        res = session.get(url, **kwargs)
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        pytest.fail(f"Teardown không đọc được GET {url} ({e}); hãy xoá tay object có tên bắt đầu bằng {prefix!r}")


def delete_all(session, urls):
    """Xoá từng url, không dừng giữa chừng; cuối cùng báo mọi lần xoá lỗi (url + status) để dọn tay."""
    failed = []
    for url in urls:
        try:
            res = session.delete(url)
        except requests.RequestException as e:
            failed.append(f"DELETE {url}: {type(e).__name__}")
            continue
        if not res.ok:
            failed.append(f"DELETE {url}: HTTP {res.status_code} {res.text[:200]}")
    if failed:
        pytest.fail("Teardown không dọn hết object test, hãy xoá tay:\n" + "\n".join(failed))


@pytest.fixture(scope="module")
def run(metabase):
    state = {"prefix": f"test-{uuid.uuid4().hex[:8]} · "}
    yield state
    dashboards = list_for_teardown(metabase, "/api/dashboard", state["prefix"])
    cards = list_for_teardown(metabase, "/api/card", state["prefix"])
    delete_all(
        metabase,
        [f"/api/dashboard/{d['id']}" for d in dashboards if d["name"].startswith(state["prefix"])]
        + [f"/api/card/{c['id']}" for c in cards if c["name"].startswith(state["prefix"])],
    )


def published(metabase, run):
    if "ids" not in run:
        kd = ex.module("kpi_dashboard.py")
        run["ids"] = kd.publish(metabase, prefix=run["prefix"])
        run["again"] = kd.publish(metabase, prefix=run["prefix"])
    return run["ids"]


def dash_query(metabase, ids, key, country=None):
    dash = metabase.get(f"/api/dashboard/{ids['dashboard']}").json()
    dc = next(d for d in dash["dashcards"] if d["card_id"] == ids["cards"][key])
    params = [] if country is None else [
        {"id": "country", "type": "string/=", "value": [country], "target": ["dimension", ["template-tag", "country"]]}
    ]
    res = metabase.post(f"/api/dashboard/{dash['id']}/dashcard/{dc['id']}/card/{dc['card_id']}/query",
                        json={"parameters": params}).json()
    assert res.get("status") == "completed", res.get("error")
    return res["data"]["rows"]


def test_real_dashboard(metabase, run):
    ids = published(metabase, run)
    assert run["again"] == ids, "Chạy publish lần hai phải trả cùng id"
    dash = metabase.get(f"/api/dashboard/{ids['dashboard']}").json()
    assert [p["slug"] for p in dash["parameters"]] == ["country"]
    assert len(dash["dashcards"]) == 4, "Đúng 4 card, chạy lại không nhân đôi"
    assert all(dc["parameter_mappings"] for dc in dash["dashcards"])


def test_real_kpi_and_filter(metabase, run):
    ids = published(metabase, run)
    month, revenue, mom = dash_query(metabase, ids, "kpi")[0]
    assert month.startswith("2011-11") and revenue == pytest.approx(1_509_496.33, abs=0.01)
    assert mom == pytest.approx(0.3069, abs=1e-4)
    month, revenue, mom = dash_query(metabase, ids, "kpi", "Germany")[0]
    assert revenue == pytest.approx(28_025.02, abs=0.01) and mom == pytest.approx(-0.1142, abs=1e-4)


def test_real_trend_top_table(metabase, run):
    ids = published(metabase, run)
    trend = dash_query(metabase, ids, "trend")
    assert len(trend) == 24 and trend[-1][0].startswith("2011-11"), "24 tháng đủ, không có 12/2011"
    top = dash_query(metabase, ids, "top_products")
    assert (top[0][0], top[0][1].strip()) == ("23084", "RABBIT NIGHT LIGHT") and top[0][2] == pytest.approx(34_556.72)
    top_de = dash_query(metabase, ids, "top_products", "Germany")
    assert top_de[0][0] == "22423" and top_de[0][2] == pytest.approx(1_215.30)
    table = dash_query(metabase, ids, "monthly_table")
    assert table[0][0].startswith("2011-11") and table[0][1:3] == [2769, 1664]
