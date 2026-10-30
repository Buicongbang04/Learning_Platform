import datetime as dt

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from testkit import Exercise

ex = Exercise(__file__)

COLUMNS = ["instant", "dteday", "season", "yr", "mnth", "holiday", "weekday", "workingday", "weathersit",
           "temp", "atemp", "hum", "windspeed", "casual", "registered", "cnt"]
ROWS = [  # (ngày, season, casual, registered)
    ("2011-01-10", 1, 10, 90),
    ("2011-01-11", 1, 20, 180),
    ("2011-07-01", 3, 100, 300),
    ("2012-01-10", 1, 30, 270),
    ("2012-02-29", 1, 20, 180),
    ("2012-07-02", 3, 200, 600),
    ("2012-07-03", 3, 0, 700),
]
SPRING = "1 · spring (21/12-20/3)"


@pytest.fixture
def csv(tmp_path):
    records = []
    for i, (day, season, casual, registered) in enumerate(ROWS, 1):
        d = dt.date.fromisoformat(day)
        records.append([i, day, season, d.year - 2011, d.month, 0, d.isoweekday() % 7, 1, 1,
                        0.5, 0.5, 0.5, 0.1, casual, registered, casual + registered])
    path = tmp_path / "day.csv"
    pd.DataFrame(records, columns=COLUMNS).to_csv(path, index=False)
    return path


@pytest.fixture
def app():
    return ex.module("app.py")


def test_load_and_filter(app, csv):
    df = app.load_day(csv)
    assert pd.api.types.is_datetime64_any_dtype(df["dteday"]), "dteday phải là kiểu ngày"
    assert df["year"].tolist() == [2011] * 3 + [2012] * 4, "year = 2011 + yr"
    assert app.filter_days(df, 2012, [1])["dteday"].dt.strftime("%m-%d").tolist() == ["01-10", "02-29"]
    assert len(app.filter_days(df, 2012, [])) == 4, "Không chọn mùa nào nghĩa là không lọc theo mùa"
    assert len(app.filter_days(df, 2011, None)) == 3
    assert app.filter_days(df, 2012, [1, 3]).index.tolist() == [0, 1, 2, 3], "index đánh lại từ 0"


def test_kpis_and_yoy(app, csv):
    df = app.load_day(csv)
    k = app.kpis(app.filter_days(df, 2012, []))
    assert k["days"] == 4 and k["total"] == 2000
    assert k["per_day"] == pytest.approx(500.0)
    assert k["casual_share"] == pytest.approx(0.125), "Tỉ trọng = tổng casual / tổng cnt, không phải trung bình tỉ lệ từng ngày"
    empty = app.kpis(app.filter_days(df, 2010, []))
    assert empty == {"days": 0, "total": 0, "per_day": None, "casual_share": None}
    assert app.yoy(2000, 700) == pytest.approx(2000 / 700 - 1)
    assert app.yoy(10, 0) is None and app.yoy(10, None) is None and app.yoy(None, 5) is None


def test_monthly(app, csv):
    m = app.monthly(app.filter_days(app.load_day(csv), 2012, []))
    assert list(m.columns[:4]) == ["month", "casual", "registered", "cnt"]
    assert m["month"].tolist() == [pd.Timestamp("2012-01-01"), pd.Timestamp("2012-02-01"), pd.Timestamp("2012-07-01")]
    assert m["cnt"].tolist() == [300, 200, 1500]


def run_app(monkeypatch, csv_path):
    monkeypatch.setenv("BIKE_DAY_CSV", str(csv_path))
    at = AppTest.from_file(str(ex.path("app.py")), default_timeout=60)
    at.run()
    assert not at.exception, f"App lỗi khi chạy: {at.exception[0].message if at.exception else ''}"
    return at


def metrics(at):
    return {m.label: (m.value, m.delta) for m in at.metric}


def test_app_layout_and_metrics(monkeypatch, csv):
    at = run_app(monkeypatch, csv)
    assert [s.label for s in at.sidebar.selectbox] == ["Năm"], "Sidebar có selectbox `Năm`"
    assert at.sidebar.selectbox[0].value == 2012, "Mặc định năm mới nhất"
    assert [s.label for s in at.sidebar.multiselect] == ["Mùa"]
    assert at.sidebar.multiselect[0].value == list(app_seasons().values()), "Mặc định chọn cả 4 mùa"
    assert metrics(at) == {
        "Tổng lượt thuê": ("2,000", "+185.7%"),
        "Lượt thuê TB/ngày": ("500", "+114.3%"),
        "Tỉ trọng khách vãng lai": ("12.5%", "-6.1 điểm %"),
    }
    assert len(at.get("plotly_chart")) == 1, "Một biểu đồ plotly (st.plotly_chart) theo tháng"
    top = at.dataframe[0].value
    assert len(top) == 4 and int(top["cnt"].iloc[0]) == 800, "Bảng drill-down: các ngày đông nhất, sắp giảm dần"


def app_seasons():
    return ex.module("app.py").SEASONS


def test_app_filters_change_metrics(monkeypatch, csv):
    at = run_app(monkeypatch, csv)
    at.sidebar.multiselect[0].set_value([SPRING]).run()
    assert not at.exception
    assert metrics(at) == {
        "Tổng lượt thuê": ("500", "+66.7%"),
        "Lượt thuê TB/ngày": ("250", "+66.7%"),
        "Tỉ trọng khách vãng lai": ("10.0%", "+0.0 điểm %"),
    }, "Delta so với cùng mùa đã chọn của năm trước"
    at.sidebar.selectbox[0].set_value(2011).run()
    m = metrics(at)
    assert m["Tổng lượt thuê"] == ("300", ""), "2011 là năm đầu: không có delta (delta=None)"
    assert m["Lượt thuê TB/ngày"][1] == "" and m["Tỉ trọng khách vãng lai"][1] == ""


def test_real_data_default_view(monkeypatch):
    path = ex.dataset("bike-sharing-uci") / "day.csv"
    at = run_app(monkeypatch, path)
    assert metrics(at) == {
        "Tổng lượt thuê": ("2,049,576", "+64.9%"),
        "Lượt thuê TB/ngày": ("5,600", "+64.4%"),
        "Tỉ trọng khách vãng lai": ("18.2%", "-1.7 điểm %"),
    }
    assert str(at.dataframe[0].value["dteday"].iloc[0]) == "2012-09-15"
