---
title: Client cho Feast feature server
level: intermediate
services: [redis]
files:
  - path: starter/client.py
    note: build_request và parse_response cần viết
  - path: tests/test_client.py
    note: Không sửa
  - path: tests/fixtures/features.py
    note: Feature repo mà test dùng để dựng feature server
run:
  - docker compose -f setup/mlops/compose.yaml --profile feast up -d --wait
  - uv run pytest tracks/mlops/modules/06-feature-stores/exercises/intermediate/03-feature-server-client -q
---

## Mục tiêu

Viết lớp client mỏng gọi `POST /get-online-features` của **Feast feature server**, đọc đúng định dạng trả về và xử lý
thực thể thiếu bằng default tường minh. Đây là phần mã nằm giữa dịch vụ dự đoán và feature store.

## Đề bài

Trong `starter/client.py` (chỉ dùng thư viện chuẩn; test chạy tệp này cả ở host lẫn trong container Feast):

`build_request(feature_refs, zone_ids)` trả `dict` JSON-serializable dạng `{"features": [...], "entities": {"zone_id": [...]}}`:

- `features` là bản **sao** của `feature_refs` (sửa kết quả không làm đổi đầu vào), giữ thứ tự.
- `zone_id` ép về `int`, **loại trùng giữ thứ tự xuất hiện đầu tiên**.
- `feature_refs` hoặc `zone_ids` rỗng thì `ValueError`.

`parse_response(response, defaults)` nhận JSON đã giải mã của feature server và trả `(values, defaulted)`:

- `response["metadata"]["feature_names"]` là danh sách tên cột; `response["results"][i]` ứng với `feature_names[i]` và có
  `values`, `statuses`, `event_timestamps` cùng độ dài. Cột `zone_id` (khoá thực thể) cũng nằm trong đó. **Tìm cột theo tên,
  không theo vị trí.**
- `values` là `{zone_id (int): {tên_feature: giá_trị}}`, mỗi feature trừ `zone_id`.
- Một giá trị là **thiếu** nếu là `None` hoặc `status` khác `"PRESENT"` (server có thể báo `PRESENT` cho giá trị `null`,
  nên phải kiểm cả hai). Giá trị thiếu thay bằng `defaults[tên_feature]`; thiếu mà `defaults` không có tên đó thì `KeyError`.
- `defaulted` là `{zone_id: [tên feature đã dùng default, **sắp tăng dần theo tên**, vì thứ tự cột server trả về không cố định]}` chỉ cho zone có default.

Test gồm các ca đơn vị trên phản hồi mẫu, và một ca tích hợp: dựng feature repo (dữ liệu thật tháng 3/2019 như bài 01), `apply`,
`materialize-incremental`, khởi động `feast serve` trong container, gọi bằng `client.py` của bạn với 2 zone có dữ liệu, 1 zone không
có và một zone lặp. Default dùng trong test: `{"avg_speed_mph": -1.0, "trip_count": 0}`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/06-feature-stores/exercises/intermediate/03-feature-server-client -q` pass.
- Giải thích được vì sao default phải đến từ dịch vụ gọi chứ không phải ngầm trong client, và vì sao nên ghi nhận tỉ lệ
  thực thể rơi vào default như một metric.

## Gợi ý

### Gợi ý 1

`dict(zip(feature_names, results))` cho bạn tra cột theo tên. Thứ tự hàng trong mỗi cột trùng thứ tự `zone_id` trong cột
`zone_id`, không nhất thiết trùng thứ tự bạn gửi.

### Gợi ý 2

Chạy thử thủ công phản hồi mẫu trong test với thứ tự cột đảo, và với `statuses` khác `PRESENT`. Hầu hết lỗi đều ở nhánh
"thiếu".
