---
title: Feature repo Feast cho tốc độ trung bình theo zone
level: intermediate
services: [redis]
files:
  - path: starter/features.py
    note: Entity và FeatureView cần định nghĩa
  - path: tests/test_feast_repo.py
    note: Không sửa
run:
  - docker compose -f setup/mlops/compose.yaml --profile feast up -d --wait
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/intermediate/01-feast-zone-speed -q
---

## Mục tiêu

Dựng một feature repo Feast thật: khai báo entity và feature view, `apply`, `materialize-incremental` vào Redis, đọc feature
online, và chứng minh giá trị online bằng giá trị offline cho cùng zone và cùng thời điểm.

## Đề bài

Cần Redis của stack (profile `feast`); test tự skip và nói lệnh bật nếu chưa chạy. Feast **không** có trong môi trường Python
mặc định: mọi lệnh Feast chạy trong container `mlops-feast:0.67.0` qua `mlopskit.feast_run` và `mlopskit.feast_python` (xem
`## 0. Cài đặt` của README module). Lần chạy đầu build image, mất vài phút. Code `features.py` của bạn cũng chỉ chạy trong container,
đừng `import feast` ở host.

Test tự dựng repo tạm: ghi `feature_store.yaml` (Redis ở `redis:6379` trong mạng `mlops_default`, offline store là tệp,
project tên ngẫu nhiên), chép `starter/features.py` của bạn, và ghi `data/zone_stats.parquet` làm từ chuyến thật tháng 3/2019
(`mlopskit.real_month`): tốc độ trung bình và số chuyến theo zone và giờ, 8 zone đông nhất, 48 giờ, thời điểm được tịnh tiến
để giờ mới nhất cách hiện tại 1 giờ. Cột của bảng: `zone_id` (`int64`), `event_timestamp` (UTC), `avg_speed_mph` (`float32`),
`trip_count` (`int64`).

Trong `starter/features.py`, giữ hai biến cấp module `zone` và `zone_speed`:

- `zone` là `Entity` tên `zone`, khoá nối `zone_id`.
- `zone_speed` là `FeatureView` tên `zone_speed`, entity `zone`, nguồn `FileSource` đọc `data/zone_stats.parquet` với
  `timestamp_field="event_timestamp"`, hai feature đúng tên và kiểu `avg_speed_mph` (`Float32`) và `trip_count` (`Int64`) theo
  thứ tự này, và `ttl` **tối thiểu 3 ngày**.

Test chạy `feast apply`, `feast materialize-incremental <bây giờ>`, rồi một script đọc cả online
(`get_online_features`) và offline (`get_historical_features`), và kiểm:

- online bằng dòng mới nhất của bảng cho từng zone, và bằng kết quả offline tại thời điểm hiện tại;
- zone không tồn tại trả rỗng (`None`) ở online;
- offline tại một thời điểm 10 giờ 30 phút trước cho giá trị đúng của dòng mới nhất không muộn hơn thời điểm đó (point-in-time).

Test dọn Redis bằng `teardown` của Feast khi xong.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/intermediate/01-feast-zone-speed -q` pass.
- Giải thích được vì sao hai lần đọc (online và offline) bằng nhau chỉ khi đã `materialize`, và điều gì xảy ra nếu quên.
- Nói được `ttl` ảnh hưởng thế nào tới offline và online.

## Gợi ý

### Gợi ý 1

Thông báo lỗi của `feast apply` đã nằm trong output test. Tài liệu Feast ghi rõ các đối số của `Entity`, `FileSource` và
`FeatureView` (schema là danh sách `Field`); kiểu đặt trong `feast.types`.

### Gợi ý 2

Nếu online trả rỗng dù `apply` thành công: `materialize-incremental` lấy dữ liệu trong `[bây giờ - ttl, bây giờ]` cho lần chạy
đầu; hỏi mình `ttl` đang ngắn bao nhiêu so với tuổi của dữ liệu.
