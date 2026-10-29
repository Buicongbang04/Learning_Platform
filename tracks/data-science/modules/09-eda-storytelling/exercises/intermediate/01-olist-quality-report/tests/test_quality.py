import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)
RAW = ROOT / "data" / "raw"

NAMES = [
    "orders_pk_duplicated", "delivered_missing_delivery_date", "delivered_missing_approved_at",
    "carrier_after_customer_delivery", "approved_before_purchase", "orders_without_items",
    "items_orphan_order", "items_orphan_product", "orders_without_review", "review_id_duplicated",
    "products_missing_category", "category_not_translated", "customer_zip_not_in_geolocation",
    "payment_items_mismatch", "freight_zero",
]
COLUMNS = ["check", "table", "severity", "n_failed", "n_total", "fail_rate"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("quality.ipynb")


def ts(values):
    return pd.to_datetime(pd.Series(values, dtype="object"))


def make_tables() -> dict[str, pd.DataFrame]:
    orders = pd.DataFrame({
        "order_id": ["o1", "o2", "o3", "o4", "o5", "o5"],          # o5 lặp khoá
        "customer_id": ["c1", "c2", "c3", "c4", "c5", "c5"],
        "order_status": ["delivered", "delivered", "delivered", "canceled", "delivered", "delivered"],
        "order_purchase_timestamp": ts(["2018-01-01 10:00", "2018-01-02 10:00", "2018-01-03 10:00",
                                        "2018-01-04 10:00", "2018-01-05 10:00", "2018-01-05 10:00"]),
        # o3 được duyệt trước lúc đặt; o2 thiếu approved_at
        "order_approved_at": ts(["2018-01-01 11:00", None, "2018-01-03 09:00", "2018-01-04 11:00",
                                 "2018-01-05 11:00", "2018-01-05 11:00"]),
        # o1: hãng vận chuyển nhận sau khi khách nhận
        "order_delivered_carrier_date": ts(["2018-01-06", "2018-01-03", "2018-01-04", None,
                                            "2018-01-06", "2018-01-06"]),
        # o3 delivered nhưng thiếu ngày khách nhận
        "order_delivered_customer_date": ts(["2018-01-05", "2018-01-08", None, None,
                                             "2018-01-09", "2018-01-09"]),
        "order_estimated_delivery_date": ts(["2018-01-20"] * 6),
    })
    items = pd.DataFrame({
        "order_id": ["o1", "o1", "o2", "o3", "o9"],                 # o9 mồ côi; o4, o5 không có item
        "order_item_id": [1, 2, 1, 1, 1],
        "product_id": ["p1", "p2", "p1", "p404", "p2"],             # p404 không có trong products
        "price": [100.0, 50.0, 30.0, 20.0, 10.0],
        "freight_value": [10.0, 5.0, 0.0, 4.0, 1.0],                # một item phí vận chuyển 0
    })
    payments = pd.DataFrame({
        "order_id": ["o1", "o1", "o2", "o3", "o4"],
        "payment_sequential": [1, 2, 1, 1, 1],
        # o1: 40 + 125 = 165 khớp; o2: 32 lệch 2 BRL; o3: 24.5 lệch 0.5 (không tính); o4 không có item
        "payment_value": [40.0, 125.0, 32.0, 24.5, 15.0],
    })
    reviews = pd.DataFrame({
        "review_id": ["r1", "r2", "r2", "r3"],                       # r2 gắn hai đơn
        "order_id": ["o1", "o2", "o3", "o4"],                         # o5 không có review
        "review_score": [5, 1, 1, 3],
    })
    products = pd.DataFrame({
        "product_id": ["p1", "p2", "p3", "p4"],
        "product_category_name": ["beleza_saude", "pc_gamer", None, "beleza_saude"],
    })
    customers = pd.DataFrame({
        "customer_id": ["c1", "c2", "c3", "c4", "c5"],
        "customer_unique_id": ["u1", "u2", "u3", "u1", "u5"],
        "customer_zip_code_prefix": ["01001", "02002", "99999", "01001", "03003"],
    })
    geolocation = pd.DataFrame({
        "geolocation_zip_code_prefix": ["01001", "01001", "02002", "03003"],
        "geolocation_lat": [-23.5, -23.6, -22.9, -19.9],
        "geolocation_lng": [-46.6, -46.7, -43.2, -43.9],
    })
    translation = pd.DataFrame({
        "product_category_name": ["beleza_saude"],
        "product_category_name_english": ["health_beauty"],
    })
    return {"orders": orders, "items": items, "payments": payments, "reviews": reviews,
            "products": products, "customers": customers, "geolocation": geolocation,
            "translation": translation}


def test_count_duplicated(nb):
    t = make_tables()
    assert nb.count_duplicated(t["orders"], ["order_id"]) == 2
    assert nb.count_duplicated(t["reviews"], ["review_id"]) == 2
    assert nb.count_duplicated(t["reviews"], ["review_id", "order_id"]) == 0


def test_count_orphans(nb):
    t = make_tables()
    assert nb.count_orphans(t["items"], "order_id", t["orders"], "order_id") == 1
    assert nb.count_orphans(t["orders"], "order_id", t["items"], "order_id") == 3     # o4, o5, o5
    child = pd.DataFrame({"k": ["a", None, "z"]})
    assert nb.count_orphans(child, "k", pd.DataFrame({"k": ["a"]}), "k") == 1       # None không tính


def test_count_order_violations(nb):
    o = make_tables()["orders"]
    assert nb.count_order_violations(o, "order_delivered_carrier_date", "order_delivered_customer_date") == (1, 4)
    assert nb.count_order_violations(o, "order_purchase_timestamp", "order_approved_at") == (1, 5)


def test_report_structure(nb):
    report = nb.quality_report(make_tables())
    assert list(report.columns) == COLUMNS
    assert report["check"].tolist() == NAMES
    sev = dict(zip(report["check"], report["severity"]))
    assert sev["carrier_after_customer_delivery"] == "error" and sev["freight_zero"] == "info"
    assert sev["orders_without_review"] == "warning"


EXPECTED = {
    "orders_pk_duplicated": (2, 6),
    "delivered_missing_delivery_date": (1, 5),
    "delivered_missing_approved_at": (1, 5),
    "carrier_after_customer_delivery": (1, 4),
    "approved_before_purchase": (1, 5),
    "orders_without_items": (3, 6),
    "items_orphan_order": (1, 5),
    "items_orphan_product": (1, 5),
    "orders_without_review": (2, 6),
    "review_id_duplicated": (2, 4),
    "products_missing_category": (1, 4),
    "category_not_translated": (1, 3),
    "customer_zip_not_in_geolocation": (1, 5),
    "payment_items_mismatch": (1, 3),
    "freight_zero": (1, 5),
}


def test_report_values(nb):
    report = nb.quality_report(make_tables()).set_index("check")
    for name, (failed, total) in EXPECTED.items():
        assert (report.loc[name, "n_failed"], report.loc[name, "n_total"]) == (failed, total), name
        assert report.loc[name, "fail_rate"] == pytest.approx(failed / total), name


def test_payment_mismatch_does_not_double_count(nb):
    # o1 có 2 item × 2 payment: join thẳng hai bảng chi tiết sẽ nhân đôi tổng và báo lệch nhầm
    report = nb.quality_report(make_tables()).set_index("check")
    assert report.loc["payment_items_mismatch", "n_failed"] == 1


def test_clean_tables_have_no_blocking(nb):
    t = make_tables()
    o = t["orders"].drop_duplicates("order_id").copy()
    o.loc[o.order_id == "o1", "order_delivered_carrier_date"] = pd.Timestamp("2018-01-02")
    o.loc[o.order_id == "o3", "order_approved_at"] = pd.Timestamp("2018-01-03 11:00")
    t["orders"] = o
    t["items"] = t["items"][~t["items"].order_id.eq("o9") & ~t["items"].product_id.eq("p404")]
    assert nb.blocking_checks(nb.quality_report(t)) == []


def test_blocking_checks(nb):
    report = nb.quality_report(make_tables())
    assert nb.blocking_checks(report) == [
        "orders_pk_duplicated", "carrier_after_customer_delivery", "approved_before_purchase",
        "items_orphan_order", "items_orphan_product"]


REAL = {
    "orders_pk_duplicated": 0, "delivered_missing_delivery_date": 8, "delivered_missing_approved_at": 14,
    "carrier_after_customer_delivery": 23, "approved_before_purchase": 0, "orders_without_items": 775,
    "items_orphan_order": 0, "items_orphan_product": 0, "orders_without_review": 768,
    "review_id_duplicated": 1603, "products_missing_category": 610, "category_not_translated": 13,
    "customer_zip_not_in_geolocation": 278, "payment_items_mismatch": 249, "freight_zero": 383,
}


def test_real_olist(nb):
    if not (RAW / "olist_orders_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    dates = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
             "order_delivered_customer_date", "order_estimated_delivery_date"]
    t = {
        "orders": pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=dates),
        "items": pd.read_csv(RAW / "olist_order_items_dataset.csv"),
        "payments": pd.read_csv(RAW / "olist_order_payments_dataset.csv"),
        "reviews": pd.read_csv(RAW / "olist_order_reviews_dataset.csv"),
        "products": pd.read_csv(RAW / "olist_products_dataset.csv"),
        "customers": pd.read_csv(RAW / "olist_customers_dataset.csv", dtype={"customer_zip_code_prefix": str}),
        "geolocation": pd.read_csv(RAW / "olist_geolocation_dataset.csv",
                                   dtype={"geolocation_zip_code_prefix": str},
                                   usecols=["geolocation_zip_code_prefix"]),
        "translation": pd.read_csv(RAW / "product_category_name_translation.csv"),
    }
    report = nb.quality_report(t).set_index("check")
    assert report["n_failed"].to_dict() == REAL
    assert report.loc["delivered_missing_delivery_date", "n_total"] == 96478
    assert report.loc["payment_items_mismatch", "n_total"] == 98665
    assert nb.blocking_checks(report.reset_index()) == ["carrier_after_customer_delivery"]
