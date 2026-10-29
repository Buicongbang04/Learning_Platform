import numpy as np
import pandas as pd
import pytest

from testkit import ROOT, Exercise

ex = Exercise(__file__)


def ts(values):
    return pd.to_datetime(values, format="ISO8601")


ORDERS = pd.DataFrame({
    "order_purchase_timestamp": ts(["2018-03-05 14:30:00", "2018-03-10 23:00:00", "2018-03-11 08:00:00"]),
    "order_estimated_delivery_date": ts(["2018-03-20 00:00:00", "2018-03-25 00:00:00", "2018-03-30 00:00:00"]),
    "order_delivered_customer_date": ts(["2018-03-20 15:00:00", "2018-03-15 11:00:00", None]),
}, index=[10, 20, 30])


@pytest.fixture(scope="module")
def features():
    return ex.module("features.py")


def test_delivery_time_features_values(features):
    out = features.delivery_time_features(ORDERS)
    assert list(out.index) == [10, 20, 30]
    expected_cols = {"promised_days", "delivery_days", "delay_days", "is_late",
                     "purchase_hour", "purchase_dow", "is_weekend"}
    assert expected_cols <= set(out.columns)
    assert out.loc[10, "promised_days"] == pytest.approx(14 + 9.5 / 24)
    assert out.loc[10, "delivery_days"] == pytest.approx(15 + 0.5 / 24)
    assert out.loc[10, "delay_days"] == pytest.approx(15 / 24)
    assert out.loc[20, "delay_days"] == pytest.approx(-(9 + 13 / 24))


def test_late_compares_full_timestamp(features):
    out = features.delivery_time_features(ORDERS)
    # giao 15:00 đúng ngày hẹn (ngày hẹn lưu lúc 00:00) vẫn tính là trễ
    assert out.is_late.tolist() == [1, 0, 0]
    assert np.isnan(out.loc[30, "delay_days"])


def test_calendar_features(features):
    out = features.delivery_time_features(ORDERS)
    assert out.purchase_hour.tolist() == [14, 23, 8]
    assert out.purchase_dow.tolist() == [0, 5, 6]     # thứ Hai, thứ Bảy, Chủ nhật
    assert out.is_weekend.tolist() == [0, 1, 1]


def test_cyclic_encode(features):
    sin, cos = features.cyclic_encode([0, 6, 12, 23], period=24)
    points = np.column_stack([sin, cos])
    assert np.allclose(np.hypot(sin, cos), 1)
    assert np.linalg.norm(points[0] - points[3]) < 0.3       # 23h sát 0h
    assert np.linalg.norm(points[0] - points[2]) == pytest.approx(2)   # 0h và 12h đối nhau
    assert points[1] == pytest.approx([1, 0], abs=1e-12)


def test_haversine_known_distances(features):
    sao_paulo, rio, manaus = (-23.5505, -46.6333), (-22.9068, -43.1729), (-3.1190, -60.0217)
    assert float(features.haversine_km(*sao_paulo, *rio)) == pytest.approx(360.7, abs=1)
    assert float(features.haversine_km(*sao_paulo, *manaus)) == pytest.approx(2689.5, abs=2)
    assert float(features.haversine_km(*rio, *rio)) == pytest.approx(0, abs=1e-9)


def test_haversine_vectorised(features):
    lat = np.array([-23.5505, -22.9068, np.nan])
    lon = np.array([-46.6333, -43.1729, -40.0])
    out = features.haversine_km(lat, lon, lat[::-1], lon[::-1])
    assert out.shape == (3,)
    assert np.isnan(out[0]) and np.isnan(out[2])
    assert out[1] == pytest.approx(0, abs=1e-9)


GEO = pd.DataFrame({
    "geolocation_zip_code_prefix": [1037, 1037, 1037, 1037, 20000, 20000],
    "geolocation_lat": [-23.5, -23.6, -23.7, 40.0, -22.9, -22.95],     # 40.0 là toạ độ lỗi (ngoài Brazil)
    "geolocation_lng": [-46.6, -46.7, -46.5, -3.7, -43.2, -43.1],
})


def test_zip_centroids_median_clean_and_padded(features):
    out = features.zip_centroids(GEO)
    assert sorted(out.index) == ["01037", "20000"]
    assert {"lat", "lng"} <= set(out.columns)
    assert out.loc["01037", "lat"] == pytest.approx(-23.6)   # trung vị sau khi bỏ điểm lỗi
    assert out.loc["01037", "lng"] == pytest.approx(-46.6)
    assert out.loc["20000", "lat"] == pytest.approx(-22.925)


def test_order_distance_handles_int_zip_and_missing(features):
    cen = features.zip_centroids(GEO)
    out = features.order_distance_km([1037, "20000", "99999"], ["20000", "01037", "01037"], cen)
    assert out[0] == pytest.approx(out[1])
    assert 320 < out[0] < 380
    assert np.isnan(out[2])


def test_real_olist(features):
    raw = ROOT / "data" / "raw"
    if not (raw / "olist_geolocation_dataset.csv").exists():
        pytest.skip("Chưa tải Olist thật: uv run python data/download_olist.py")
    geo = pd.read_csv(raw / "olist_geolocation_dataset.csv")
    cen = features.zip_centroids(geo)
    assert len(cen) == 19010
    orders = pd.read_csv(raw / "olist_orders_dataset.csv", parse_dates=[
        "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date"])
    delivered = orders[(orders.order_status == "delivered") & orders.order_delivered_customer_date.notna()]
    out = features.delivery_time_features(delivered)
    assert out.is_late.mean() == pytest.approx(0.0811, abs=5e-4)
    assert out.promised_days.median() == pytest.approx(23.23, abs=0.01)
