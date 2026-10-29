---
title: Phí ship Olist - hồi quy log-log, chẩn đoán residual và cluster SE
level: intermediate
services: []
files:
  - path: starter/freight.ipynb
    note: 5 hàm/hằng TODO + phần kết luận
  - path: tests/test_freight.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/05-econometrics-regression/exercises/intermediate/01-olist-freight-ols/starter/freight.ipynb
  - uv run pytest tracks/data-science/modules/05-econometrics-regression/exercises/intermediate/01-olist-freight-ols -q
---

## Mục tiêu

Làm trọn một phân tích hồi quy trên dữ liệu thật như ở công ty: nối nhiều bảng thành bảng phân tích
có quy tắc rõ ràng, fit model log-log, đọc hệ số thành ngôn ngữ kinh doanh, chẩn đoán residual, và
chọn SE đúng với cấu trúc dữ liệu.

## Đề bài

Mở `starter/freight.ipynb`, làm theo thứ tự:

1. `haversine_km(lat1, lon1, lat2, lon2)`: khoảng cách đường tròn lớn, bán kính 6 371 km, nhận cả
   số lẫn mảng.
2. `build_freight_table(items, orders, customers, sellers, products, geo)`: một dòng mỗi đơn giao
   xong có đúng một món, theo đúng các quy tắc và cột trong docstring. Toạ độ mỗi zip prefix là
   **trung vị** lat/lng trong bảng geolocation.
3. `FORMULA` (đã cho), `fit_freight(df, cov_type)` với `nonrobust`, `HC3`, `cluster` (theo
   `seller_id`), và `compare_se(df)` trả bảng SE ba cột `classic`, `HC3`, `cluster`.
4. Chạy các cell `explore`: residual vs fitted, QQ-plot, residual trung bình theo seller, thử bỏ
   `same_state`.
5. `effects(res)`: quy hệ số ra % thay đổi phí ship.
6. Viết kết luận 5–8 câu trong cell markdown cuối (không chấm tự động; so với lời giải mẫu).

## Tiêu chí đạt

- `haversine_km` đúng với khoảng cách đã biết và đối xứng.
- `build_freight_table` loại đúng: đơn nhiều món, chưa giao xong, thiếu toạ độ, thiếu cân nặng, phí
  ship 0, khoảng cách 0; khoảng cách dùng trung vị toạ độ.
- Ba loại SE khớp statsmodels; trên dữ liệu mô phỏng có cú sốc chung theo seller, cluster SE của
  biến cấp seller lớn hơn rõ SE cổ điển.
- Trên Olist thật: 86 065 đơn, $$R^2 \approx 0.655$$, hệ số `log_distance` ≈ 0.1418, `same_state` ≈ −0.2242.
- Kết luận nêu được SE nào được báo cáo và vì sao, và một điều model không nói được.

## Gợi ý

### Gợi ý 1

Thứ tự lọc: tìm `order_id` có đúng một dòng trong `items` **trước** khi nối, không phải sau (nối với
products có thể làm mất dòng và một đơn hai món trông như một món). Zip prefix phải đọc dạng `str`
(có số 0 ở đầu: `01037`); test thật đọc như vậy.

### Gợi ý 2

`coords = geo.groupby("geolocation_zip_code_prefix")[["geolocation_lat", "geolocation_lng"]].median()`,
rồi `.join(coords.add_prefix("c_"), on="customer_zip_code_prefix")` và tương tự cho seller. Cluster
SE trong statsmodels cần nhóm là số nguyên: `pd.factorize(df["seller_id"])[0]`.
