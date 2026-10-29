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
    # TODO: hiệu hai cột datetime chia cho pd.Timedelta(days=1) cho số ngày thực
    # TODO: các feature lịch dùng .dt.hour, .dt.day_of_week
    raise NotImplementedError


def cyclic_encode(values, period: float) -> tuple[np.ndarray, np.ndarray]:
    """(sin, cos) của 2π·values/period: giờ 23 và giờ 0 nằm cạnh nhau trên vòng tròn."""
    # TODO
    raise NotImplementedError


def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Khoảng cách đường tròn lớn (km) giữa hai điểm, nhận số hoặc mảng; NaN đi qua thành NaN."""
    # TODO: đổi độ sang radian rồi áp công thức haversine (xem README của bài)
    raise NotImplementedError


def zip_centroids(geo: pd.DataFrame) -> pd.DataFrame:
    """Toạ độ trung vị của mỗi zip prefix; index là chuỗi 5 ký tự ("01037"), cột lat, lng.

    Bỏ toạ độ nằm ngoài khung Brazil trước khi lấy trung vị. Zip đọc thành số (mất số 0 đầu) vẫn đúng.
    """
    # TODO: lọc theo LAT_RANGE, LNG_RANGE
    # TODO: chuẩn hoá zip thành chuỗi 5 ký tự (str.zfill), groupby, median
    raise NotImplementedError


def order_distance_km(customer_zip, seller_zip, centroids: pd.DataFrame) -> np.ndarray:
    """Khoảng cách khách–seller theo toạ độ trung vị zip; NaN nếu thiếu toạ độ một trong hai đầu."""
    # TODO: chuẩn hoá zip như trên, centroids.reindex(...) để lấy toạ độ, rồi haversine_km
    raise NotImplementedError
