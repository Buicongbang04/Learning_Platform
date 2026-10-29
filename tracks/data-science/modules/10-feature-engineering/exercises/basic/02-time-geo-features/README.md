---
title: Feature thời gian và địa lý cho đơn hàng
level: basic
services: []
files:
  - path: starter/features.py
    note: 5 hàm TODO
  - path: tests/test_features.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/basic/02-time-geo-features -q
---

## Mục tiêu

Tạo các feature mạnh nhất của bài toán review xấu (thời gian giao so với lời hứa, khoảng cách khách
và seller) và gặp ba cái bẫy dữ liệu thật: timestamp lúc 00:00, giờ là biến vòng tròn, zip code mất
số 0 đầu và toạ độ lỗi.

## Đề bài

Trong `starter/features.py`, làm theo docstring:

1. `delivery_time_features(orders)`: `promised_days`, `delivery_days`, `delay_days` (số ngày thực),
   `is_late` (so nguyên timestamp), `purchase_hour`, `purchase_dow` (thứ Hai = 0), `is_weekend`.
2. `cyclic_encode(values, period)`: trả `(sin, cos)` của góc $$2\pi \cdot \text{value} / \text{period}$$.
3. `haversine_km(lat1, lon1, lat2, lon2)`: khoảng cách đường tròn lớn, bán kính Trái Đất 6 371 km,
   nhận mảng:

   $$
   d = 2R \arcsin\sqrt{\sin^2\frac{\varphi_2 - \varphi_1}{2} + \cos\varphi_1 \cos\varphi_2 \sin^2\frac{\lambda_2 - \lambda_1}{2}}
   $$

   với $$\varphi$$ là vĩ độ, $$\lambda$$ là kinh độ, tính bằng radian.
4. `zip_centroids(geo)`: bỏ toạ độ ngoài khung Brazil (`LAT_RANGE`, `LNG_RANGE`), lấy **trung vị**
   lat/lng theo zip prefix; index là chuỗi 5 ký tự.
5. `order_distance_km(customer_zip, seller_zip, centroids)`: khoảng cách cho từng cặp, NaN nếu thiếu.

## Tiêu chí đạt

- Giao 15:00 đúng ngày hẹn là trễ (ngày hẹn lưu lúc 00:00); đơn chưa giao cho NaN, không lỗi.
- 23h và 0h gần nhau sau khi mã hoá vòng tròn; 0h và 12h đối nhau.
- São Paulo – Rio khoảng 361 km; São Paulo – Manaus khoảng 2 690 km.
- Zip đọc thành số (`1037`) vẫn khớp `"01037"`; toạ độ lỗi không kéo lệch trung vị.
- Trên Olist thật: 19 010 zip prefix có toạ độ hợp lệ; 8.11% đơn giao xong bị trễ; trung vị thời
  gian hứa giao 23.2 ngày.

## Gợi ý

### Gợi ý 1

`(a - b) / pd.Timedelta(days=1)` cho số ngày thực (có phần lẻ). `.dt.days` chỉ cho phần nguyên và
làm tròn xuống: −0.4 ngày thành −1.

### Gợi ý 2

`pd.Series(values).astype(str).str.zfill(5)` chuẩn hoá zip. Với `centroids.reindex(zips)`, zip
không có trong bảng thành dòng NaN, và `haversine_km` tự trả NaN.
