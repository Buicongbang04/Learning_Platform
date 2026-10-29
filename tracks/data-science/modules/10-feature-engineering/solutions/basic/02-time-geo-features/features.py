"""Feature thời gian và địa lý cho bài toán review xấu của Olist."""

from __future__ import annotations

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0
# Khung bao Brazil (rộng tay): toạ độ ngoài khung là lỗi nhập liệu trong bảng geolocation
LAT_RANGE = (-34.0, 6.0)
LNG_RANGE = (-74.0, -34.0)


def delivery_time_features(orders: pd.DataFrame) -> pd.DataFrame:
    """Feature thời gian của đơn, cùng index với orders.

    promised_days  (estimated_delivery − purchase) tính bằng ngày, số thực
    delivery_days  (delivered_customer − purchase), ngày
    delay_days     (delivered_customer − estimated_delivery), ngày; âm là giao sớm
    is_late        1 nếu delivered_customer > estimated_delivery (so nguyên timestamp), ngược lại 0
    purchase_hour  giờ mua 0–23
    purchase_dow   thứ trong tuần lúc mua, thứ Hai = 0
    is_weekend     1 nếu mua thứ Bảy hoặc Chủ nhật
    Đơn chưa giao: delivery_days, delay_days là NaN và is_late là 0.
    """
    day = pd.Timedelta(days=1)
    bought = orders["order_purchase_timestamp"]
    delivered = orders["order_delivered_customer_date"]
    promised = orders["order_estimated_delivery_date"]
    return pd.DataFrame({
        "promised_days": (promised - bought) / day,
        "delivery_days": (delivered - bought) / day,
        "delay_days": (delivered - promised) / day,
        "is_late": (delivered > promised).astype(int),
        "purchase_hour": bought.dt.hour,
        "purchase_dow": bought.dt.day_of_week,
        "is_weekend": (bought.dt.day_of_week >= 5).astype(int),
    }, index=orders.index)


def cyclic_encode(values, period: float) -> tuple[np.ndarray, np.ndarray]:
    """(sin, cos) của 2π·values/period: giờ 23 và giờ 0 nằm cạnh nhau trên vòng tròn."""
    angle = 2 * np.pi * np.asarray(values, dtype=float) / period
    return np.sin(angle), np.cos(angle)


def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Khoảng cách đường tròn lớn (km) giữa hai điểm, nhận số hoặc mảng; NaN đi qua thành NaN."""
    lat1, lon1, lat2, lon2 = (np.radians(np.asarray(v, dtype=float)) for v in (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def _zip(values) -> pd.Series:
    return pd.Series(values).astype(str).str.zfill(5)


def zip_centroids(geo: pd.DataFrame) -> pd.DataFrame:
    """Toạ độ trung vị của mỗi zip prefix; index là chuỗi 5 ký tự ("01037"), cột lat, lng.

    Bỏ toạ độ nằm ngoài khung Brazil trước khi lấy trung vị. Zip đọc thành số (mất số 0 đầu) vẫn đúng.
    """
    ok = (geo["geolocation_lat"].between(*LAT_RANGE) & geo["geolocation_lng"].between(*LNG_RANGE))
    clean = geo[ok]
    out = (clean.assign(zip=_zip(clean["geolocation_zip_code_prefix"]).to_numpy())
           .groupby("zip")[["geolocation_lat", "geolocation_lng"]].median())
    out.columns = ["lat", "lng"]
    out.index.name = "zip"
    return out


def order_distance_km(customer_zip, seller_zip, centroids: pd.DataFrame) -> np.ndarray:
    """Khoảng cách khách–seller theo toạ độ trung vị zip; NaN nếu thiếu toạ độ một trong hai đầu."""
    c = centroids.reindex(_zip(customer_zip)).to_numpy()
    s = centroids.reindex(_zip(seller_zip)).to_numpy()
    return haversine_km(c[:, 0], c[:, 1], s[:, 0], s[:, 1])
