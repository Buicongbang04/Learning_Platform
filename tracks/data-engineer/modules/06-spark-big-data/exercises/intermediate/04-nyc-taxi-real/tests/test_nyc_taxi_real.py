import re
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import nbformat
import pytest
from pyspark.sql import SparkSession

from testkit import Exercise

ex = Exercise(__file__)
NB = "nyc_taxi.ipynb"
KEY = "spark.sql.autoBroadcastJoinThreshold"
TRIP_SCHEMA = (
    "pickup_at timestamp_ntz, dropoff_at timestamp_ntz, passenger_count int, trip_distance double, "
    "pu_location_id int, do_location_id int, payment_type int, fare_amount double, tip_amount double, "
    "total_amount double"
)
CLEAN_EXTRA = ["duration_min", "pickup_hour", "pickup_date"]


def _build(master):
    return (
        SparkSession.builder.master(master)
        .appName("06-intermediate-04")
        .config("spark.driver.memory", "4g")       # chỉ có tác dụng nếu JVM chưa chạy
        .config("spark.ui.enabled", "false")
        .config("spark.ui.showConsoleProgress", "false")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.sql.warehouse.dir", tempfile.mkdtemp(prefix="spark-wh-"))
        .config("spark.sql.shuffle.partitions", "16")
        .getOrCreate()
    )


@pytest.fixture(scope="module")
def spark():
    # Mỗi tệp TLC là MỘT row group ~100 MB: mỗi task đọc giữ cả column chunk trong heap, ~4 task/GB là an toàn
    # (đo được: heap 1 GB chạy được 8 task, 12 task thì OutOfMemoryError). Khi test của bài khác đã khởi động
    # JVM với heap mặc định 1 GB thì không tăng heap được nữa, nên giảm số task song song cho vừa.
    session = _build("local[*]")
    heap_gb = session.sparkContext._jvm.java.lang.Runtime.getRuntime().maxMemory() / 2**30
    slots = max(1, int(heap_gb * 4))
    if slots < session.sparkContext.defaultParallelism:
        session.stop()
        session = _build(f"local[{slots}]")
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


@pytest.fixture(scope="module")
def nb():
    return ex.notebook(NB)


def T(day, hour, minute=0, second=0):
    return datetime(2019, 3, day, hour, minute, second)


def trip(pickup, minutes, miles, payment=1, fare=10.0, tip=2.0, pu=4, do=4, total=None, passengers=1):
    dropoff = None if minutes is None else pickup + timedelta(minutes=minutes)
    total = fare + tip + 1.3 if total is None else total
    return (pickup, dropoff, passengers, miles, pu, do, payment, fare, tip, total)


# Mỗi dòng "bad" vi phạm đúng một luật (trừ dòng ghi chú), thứ tự luật: out_of_period trước.
GOOD = [
    trip(T(1, 8), 12, 2.0, payment=1, fare=10.0, tip=2.0, pu=4, do=7),        # Manhattan -> Queens
    trip(T(1, 8, 30), 20, 3.5, payment=1, fare=15.0, tip=3.0, pu=7, do=4),    # Queens -> Manhattan
    trip(T(1, 18), 10, 1.5, payment=2, fare=8.0, tip=0.0, pu=4, do=4),        # tiền mặt
    trip(T(2, 18, 5), 45, 17.0, payment=1, fare=52.0, tip=10.0, pu=132, do=4),  # từ JFK
    trip(T(2, 18, 40), 30, 10.0, payment=2, fare=30.0, tip=0.0, pu=4, do=138),  # tới LaGuardia
    trip(T(3, 23, 59), 15, 4.0, payment=3, fare=14.0, tip=0.0, pu=3, do=3),   # no charge, Bronx
    trip(T(3, 18), 8, 1.0, payment=1, fare=7.0, tip=0.0, pu=3, do=3, passengers=None),  # Bronx, thiếu số khách
]
BAD = {
    "out_of_period": [trip(datetime(2008, 12, 31, 23, 50), 15, 3.0), trip(datetime(2020, 1, 1, 0, 5), 15, 3.0)],
    "bad_duration": [trip(T(4, 9), -5, 2.0), trip(T(4, 9), 0, 2.0), trip(T(4, 9), 200, 30.0), trip(T(4, 9), None, 2.0)],
    "bad_distance": [trip(T(5, 9), 10, 0.0), trip(T(5, 9), 10, -1.2), trip(T(5, 9), 150, 120.0)],
    "bad_amount": [trip(T(6, 9), 10, 2.0, fare=-7.0, total=-8.3), trip(T(6, 9), 10, 2.0, fare=0.0),
                   trip(T(6, 9), 10, 2.0, tip=-1.0), trip(T(6, 9), 100, 60.0, fare=900.0)],
    "too_fast": [trip(T(7, 9), 1, 5.0)],                                      # 300 dặm/giờ
}
# Vi phạm nhiều luật cùng lúc: luật đứng trước trong REASONS thắng.
MULTI = [
    (trip(datetime(2018, 12, 31, 22), -3, 0.0, fare=-1.0, total=-1.0), "out_of_period"),
    (trip(T(8, 9), -3, 0.0, fare=-1.0, total=-1.0), "bad_duration"),
    (trip(T(8, 9), 10, 0.0, fare=-1.0, total=-1.0), "bad_distance"),
]
ZONES = [
    (3, "Bronx", "Allerton/Pelham Gardens", "Boro Zone"),
    (4, "Manhattan", "Alphabet City", "Yellow Zone"),
    (7, "Queens", "Astoria", "Boro Zone"),
    (132, "Queens", "JFK Airport", "Airports"),
    (138, "Queens", "LaGuardia Airport", "Airports"),
    (1, "EWR", "Newark Airport", "EWR"),
]


@pytest.fixture(scope="module")
def raw(spark):
    rows = GOOD + [r for rows in BAD.values() for r in rows] + [r for r, _ in MULTI]
    return spark.createDataFrame(rows, TRIP_SCHEMA)


@pytest.fixture(scope="module")
def zones(spark):
    return spark.createDataFrame(ZONES, "location_id int, borough string, zone string, service_zone string")


def plan_string(df):
    return df._jdf.queryExecution().executedPlan().toString()


# ---------- load: chọn cột, đổi tên, ép kiểu ----------

def test_load_trips_selects_renames_casts(spark, nb, tmp_path):
    tlc = spark.createDataFrame(
        [(2, datetime(2019, 3, 1, 8), datetime(2019, 3, 1, 8, 12), 1.0, 2.0, 1.0, "N", 4, 7, 1, 10.0, 0.5, 0.5,
          2.0, 0.0, 0.3, 13.3, 2.5, None)],
        "VendorID long, tpep_pickup_datetime timestamp_ntz, tpep_dropoff_datetime timestamp_ntz, "
        "passenger_count double, trip_distance double, RatecodeID double, store_and_fwd_flag string, "
        "PULocationID long, DOLocationID long, payment_type long, fare_amount double, extra double, "
        "mta_tax double, tip_amount double, tolls_amount double, improvement_surcharge double, "
        "total_amount double, congestion_surcharge double, airport_fee double",
    )
    for month in (1, 2):
        tlc.write.parquet(str(tmp_path / f"yellow_tripdata_2019-0{month}.parquet"))
    df = nb.load_trips(spark, [tmp_path / "yellow_tripdata_2019-01.parquet", tmp_path / "yellow_tripdata_2019-02.parquet"])
    assert df.columns == [c for c, _ in (f.split() for f in TRIP_SCHEMA.split(", "))]
    types = dict(df.dtypes)
    assert types["pickup_at"] == types["dropoff_at"] == "timestamp_ntz"
    assert types["passenger_count"] == types["pu_location_id"] == types["payment_type"] == "int"
    assert types["fare_amount"] == types["trip_distance"] == "double"
    assert df.count() == 2


# ---------- làm sạch: lý do loại và dữ liệu giữ lại ----------

def test_flag_rejects_reason_per_rule(nb, raw):
    flagged = nb.flag_rejects(raw)
    assert flagged.columns == raw.columns + ["reject_reason"]
    counts = {r["reject_reason"]: r["count"] for r in flagged.groupBy("reject_reason").count().collect()}
    expected = {reason: len(rows) for reason, rows in BAD.items()}
    for _, reason in MULTI:
        expected[reason] += 1
    expected[None] = len(GOOD)
    assert counts == expected


def test_reasons_constant_order(nb):
    assert list(nb.REASONS) == ["out_of_period", "bad_duration", "bad_distance", "bad_amount", "too_fast"]


def test_clean_trips_keeps_only_good_rows(nb, raw):
    clean = nb.clean_trips(raw)
    assert clean.columns == raw.columns + CLEAN_EXTRA
    rows = sorted(clean.collect(), key=lambda r: r["pickup_at"])
    assert len(rows) == len(GOOD)
    first = rows[0]
    assert first["duration_min"] == pytest.approx(12.0)
    assert first["pickup_hour"] == 8
    assert first["pickup_date"] == date(2019, 3, 1)
    late = [r for r in rows if r["pickup_at"] == T(3, 23, 59)][0]
    assert (late["pickup_hour"], late["pickup_date"]) == (23, date(2019, 3, 3))   # ngày theo giờ đón
    assert any(r["passenger_count"] is None for r in rows), "Thiếu passenger_count không phải lý do loại chuyến"


def test_clean_trips_is_lazy_and_does_not_mutate(nb, raw):
    before = raw.columns[:]
    nb.clean_trips(raw)
    assert raw.columns == before


# ---------- phân tích ----------

def test_peak_hours(nb, raw):
    rows = [tuple(r) for r in nb.peak_hours(nb.clean_trips(raw)).collect()]
    assert rows == [(8, 2), (18, 4), (23, 1)]


def test_tip_by_payment(nb, raw):
    result = nb.tip_by_payment(nb.clean_trips(raw))
    assert result.columns == ["payment", "trips", "tip_rate", "tipped_share"]
    rows = {r["payment"]: tuple(r)[1:] for r in result.collect()}
    assert rows["card"] == (4, round(15.0 / 84.0, 4), 0.75)
    assert rows["cash"] == (2, 0.0, 0.0)
    assert rows["other"] == (1, 0.0, 0.0)
    assert [r["payment"] for r in result.collect()] == ["card", "cash", "other"]   # trips giảm dần


def test_tip_rate_by_borough_values(nb, raw, zones):
    result = nb.tip_rate_by_borough(nb.clean_trips(raw), zones)
    assert result.columns == ["borough", "trips", "tip_rate"]
    rows = [tuple(r) for r in result.collect()]
    # chỉ chuyến thẻ (tiền tip tiền mặt không được ghi), theo khu đón khách, tip_rate giảm dần
    assert rows == [("Manhattan", 1, 0.2), ("Queens", 2, round(13.0 / 67.0, 4)), ("Bronx", 1, 0.0)]


def test_tip_rate_by_borough_broadcasts_zones(spark, nb, raw, zones):
    old = spark.conf.get(KEY)
    spark.conf.set(KEY, "-1")                    # tắt broadcast tự động: chỉ hint tường minh mới broadcast
    try:
        plan = plan_string(nb.tip_rate_by_borough(nb.clean_trips(raw), zones))
    finally:
        spark.conf.set(KEY, old)
    assert "BroadcastHashJoin" in plan, "Bảng zones nhỏ: phải broadcast(zones) thay vì sort-merge join"


def test_airport_summary(nb, raw, zones):
    got = nb.airport_summary(nb.clean_trips(raw), zones)
    assert got == {"airport_trips": 2, "airport_share": round(2 / 7, 4), "airport_avg_fare": 41.0,
                   "other_avg_fare": round((10 + 15 + 8 + 14 + 7) / 5, 2)}


# ---------- ghi dữ liệu sạch: partition theo ngày, không small files, chạy lại không nhân đôi ----------

def _partitions(out):
    return {p.name: [f for f in p.iterdir() if f.suffix == ".parquet"] for p in Path(out).iterdir()
            if p.is_dir() and p.name.startswith("pickup_date=")}


def test_write_clean_partitioned_by_day_idempotent(spark, nb, raw, tmp_path):
    clean = nb.clean_trips(raw).repartition(6)     # dữ liệu rải đều 6 partition, như sau một shuffle
    out = tmp_path / "clean"
    nb.write_clean(clean, out)
    nb.write_clean(clean, out)                     # chạy lại
    parts = _partitions(out)
    assert sorted(parts) == ["pickup_date=2019-03-01", "pickup_date=2019-03-02", "pickup_date=2019-03-03"]
    assert all(len(files) == 1 for files in parts.values()), "Mỗi ngày đúng 1 tệp Parquet (không small files)"
    back = spark.read.parquet(str(out))
    assert back.count() == len(GOOD)
    assert dict(back.dtypes)["pickup_date"] == "date"


# ---------- dữ liệu thật: NYC Yellow Taxi 2019 (12 tháng, ~84,6 triệu chuyến) ----------

_REAL = {}


def real(spark, nb):
    raw_dir = ex.dataset("nyc-tlc")
    if "raw" not in _REAL:
        paths = sorted(raw_dir.glob("yellow_tripdata_2019-*.parquet"))
        assert len(paths) == 12
        _REAL["raw"] = nb.load_trips(spark, paths)
        _REAL["zones"] = nb.load_zones(spark, raw_dir / "taxi_zone_lookup.csv")
    return _REAL["raw"], _REAL["zones"]


def test_real_reject_reasons(spark, nb):
    # Bộ dữ liệu là snapshot ghim: số phải khớp gần như tuyệt đối (abs=20 chỉ cho sai khác ở biên luật tốc độ).
    raw, _ = real(spark, nb)
    counts = {r["reject_reason"]: r["count"] for r in nb.flag_rejects(raw).groupBy("reject_reason").count().collect()}
    assert sum(counts.values()) == 84_598_444
    assert counts[None] == pytest.approx(83_382_609, abs=20)
    assert counts["out_of_period"] == pytest.approx(1_442, abs=10)          # năm 2001, 2008, 2088...
    assert counts["bad_distance"] == pytest.approx(677_276, abs=20)       # nhiều nhất: quãng đường 0
    assert counts["bad_duration"] == pytest.approx(302_998, abs=20)
    assert counts["bad_amount"] == pytest.approx(161_874, abs=20)
    assert counts["too_fast"] == pytest.approx(72_245, abs=20)


def test_real_peak_hour(spark, nb):
    raw, _ = real(spark, nb)
    hours = {r["pickup_hour"]: r["trips"] for r in nb.peak_hours(nb.clean_trips(raw)).collect()}
    assert len(hours) == 24
    assert max(hours, key=hours.get) == 18
    assert hours[18] == pytest.approx(5_478_973, abs=20)
    assert min(hours, key=hours.get) == 4


def test_real_tips(spark, nb):
    raw, zones = real(spark, nb)
    clean = nb.clean_trips(raw)
    pay = {r["payment"]: r for r in nb.tip_by_payment(clean).collect()}
    assert pay["card"]["tip_rate"] == pytest.approx(0.2277, abs=0.0005)
    assert pay["card"]["tipped_share"] == pytest.approx(0.963, abs=0.001)
    assert pay["cash"]["tip_rate"] == pytest.approx(0.0, abs=0.0005)      # tip tiền mặt không được ghi
    assert pay["cash"]["trips"] == pytest.approx(22_510_014, abs=20)
    boroughs = {r["borough"]: r["tip_rate"] for r in nb.tip_rate_by_borough(clean, zones).collect()}
    assert boroughs["Manhattan"] == pytest.approx(0.2346, abs=0.0005)
    assert boroughs["Queens"] == pytest.approx(0.2073, abs=0.0005)
    assert boroughs["Brooklyn"] == pytest.approx(0.1414, abs=0.0005)
    assert boroughs["Bronx"] == pytest.approx(0.0271, abs=0.0005)


def test_real_airports(spark, nb):
    raw, zones = real(spark, nb)
    got = nb.airport_summary(nb.clean_trips(raw), zones)
    assert got["airport_share"] == pytest.approx(0.077, abs=0.0005)
    assert got["airport_avg_fare"] == pytest.approx(40.07, abs=0.05)
    assert got["other_avg_fare"] == pytest.approx(11.01, abs=0.05)


def test_real_write_one_month(spark, nb, tmp_path):
    # Ghi một tháng thật (idempotent đã kiểm ở test fixture). Tệp tháng 2 còn chứa vài chục chuyến của
    # ngày 31/01 và các tháng sau (bản ghi gửi trễ), nên có nhiều hơn 28 thư mục ngày.
    raw_dir = ex.dataset("nyc-tlc")
    feb = nb.clean_trips(nb.load_trips(spark, [raw_dir / "yellow_tripdata_2019-02.parquet"]))
    out = tmp_path / "feb"
    nb.write_clean(feb, out)
    parts = _partitions(out)
    assert {f"pickup_date=2019-02-{d:02d}" for d in range(1, 29)} <= set(parts), "Thiếu ngày tháng 2"
    assert all(len(files) == 1 for files in parts.values()), "Mỗi ngày đúng 1 tệp Parquet"
    assert spark.read.parquet(str(out)).count() == pytest.approx(6_966_272, abs=20)


# ---------- notebook, biểu đồ và báo cáo ----------

def _code_cells():
    book = nbformat.read(ex.path(NB), as_version=4)
    return [c for c in book.cells if c.cell_type == "code"]


def test_notebook_uses_real_dataset():
    first = _code_cells()[0]
    assert "explore" in first.metadata.get("tags", [])
    assert 'ensure("nyc-tlc")' in first.source


def test_notebook_draws_charts():
    plots = [c for c in _code_cells() if "explore" in c.metadata.get("tags", [])
             and re.search(r"plt\.|\.plot\(|\.bar\(|\.barh\(|\.hist\(", "\n".join(
                 line for line in c.source.splitlines() if not line.lstrip().startswith("#")))]
    assert len(plots) >= 2, "Cần ít nhất 2 cell explore vẽ biểu đồ"


def test_report_sections_and_numbers():
    text = ex.read("report.md")
    assert "TODO" not in text, "Điền hết các mục TODO trong report.md"
    for heading in ("## Bộ dữ liệu", "## Làm sạch", "## Insight", "## Giới hạn"):
        assert heading in text
    insight = text.split("## Insight", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"\d[\d.,]*", insight)) >= 3, "Mục Insight cần số liệu cụ thể"
