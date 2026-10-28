import pytest

from testkit import Exercise

ex = Exercise(__file__)


def m():
    return ex.module("finops.py")


def test_monthly_cost():
    f = m().monthly_cost
    assert f(1000, "STANDARD", 5000) == pytest.approx(23.0)
    assert f(1000, "STANDARD_IA", 100) == pytest.approx(12.5 + 1.0)
    assert f(1000, "GLACIER_IR", 0) == pytest.approx(4.0)
    with pytest.raises(ValueError):
        f(1, "COLDLINE", 0)


@pytest.mark.parametrize(
    "size, reads, expected",
    [
        (1000, 5000, "STANDARD"),      # 23.0 vs IA 62.5 vs GIR 154.0
        (1000, 1000, "STANDARD_IA"),   # 23.0 vs IA 22.5 vs GIR 34.0
        (1000, 500, "STANDARD_IA"),    # 23.0 vs IA 17.5 vs GIR 19.0
        (1000, 100, "GLACIER_IR"),     # 23.0 vs IA 13.5 vs GIR 7.0
        (1000, 0, "DEEP_ARCHIVE"),
        (0, 0, "STANDARD"),            # hoà 0 = 0 -> class nóng nhất
    ],
)
def test_best_storage_class(size, reads, expected):
    assert m().best_storage_class(size, reads) == expected


def test_archive_excluded_when_read():
    # đọc rất ít nhưng > 0: không được chọn DEEP_ARCHIVE
    assert m().best_storage_class(10_000, 0.001) == "GLACIER_IR"


def test_scanned_gb():
    f = m().scanned_gb
    # bảng 730 GB, 730 partition ngày, đọc 30 ngày, 20 cột đọc 4 cột
    assert f(730, 730, 30, 20, 4, columnar=True) == pytest.approx(6.0)
    assert f(730, 730, 30, 20, 4, columnar=False) == pytest.approx(30.0)
    assert f(730, 1, 1, 20, 4, columnar=False) == pytest.approx(730.0)
    for bad in [(730, 10, 11, 20, 4, True), (730, 0, 0, 20, 4, True), (730, 10, 1, 0, 0, True), (-1, 1, 1, 1, 1, True)]:
        with pytest.raises(ValueError):
            f(*bad)


def test_query_cost():
    f = m().query_cost
    assert f(1024) == pytest.approx(6.25)
    assert f(102.4) == pytest.approx(0.625)
    tiny = 10 / 1024 / 1024 * 6.25
    assert f(0.0001) == pytest.approx(tiny)
    assert f(0) == pytest.approx(tiny)


DATASETS = [
    {"name": "raw_orders_2016", "size_gb": 2000, "storage_class": "STANDARD", "gb_read_per_month": 0},
    {"name": "silver_orders", "size_gb": 500, "storage_class": "STANDARD", "gb_read_per_month": 5000},
    {"name": "raw_reviews", "size_gb": 1000, "storage_class": "STANDARD", "gb_read_per_month": 100},
    {"name": "archive_logs", "size_gb": 300, "storage_class": "DEEP_ARCHIVE", "gb_read_per_month": 0},
]


def test_savings_report():
    report = m().savings_report(DATASETS)
    assert [r["name"] for r in report] == ["raw_orders_2016", "raw_reviews"]
    first = report[0]
    assert first == {
        "name": "raw_orders_2016",
        "current": "STANDARD",
        "recommended": "DEEP_ARCHIVE",
        "current_cost": 46.0,
        "recommended_cost": 1.98,
        "monthly_savings": 44.02,
    }
    second = report[1]
    assert second["recommended"] == "GLACIER_IR"
    assert second["current_cost"] == 23.0 and second["recommended_cost"] == 7.0
    assert second["monthly_savings"] == 16.0


def test_savings_report_empty():
    assert m().savings_report([]) == []
