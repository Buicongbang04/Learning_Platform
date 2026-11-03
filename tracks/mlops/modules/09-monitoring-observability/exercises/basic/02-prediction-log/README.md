---
title: Log dự đoán có cấu trúc và nối nhãn về sau
level: basic
services: []
files:
  - path: starter/predlog.py
    note: Hai hàm TODO
  - path: tests/test_predlog.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/basic/02-prediction-log -q
---

## Mục tiêu

Metric cho biết "độ trễ p95 tăng"; chỉ log mới cho biết "chuyến `trip-123` được dự đoán 612 giây, mà thực tế mất 1 400 giây".
Bài này viết hai nửa của vòng đó: ghi log dự đoán đủ để nối nhãn về sau, rồi nối thật bằng `request_id`, thứ tuyệt đối không
được làm label của metric nhưng bắt buộc có trong log.

## Đề bài

Trong `starter/predlog.py` cài hai hàm.

**`log_prediction(stream, *, request_id, model_version, features, prediction, fallback, ts)`** ghi đúng một dòng JSON, kết thúc
bằng `\n`, với đúng các khoá `ts`, `request_id`, `model_version`, `prediction`, `fallback`, `features`.

- `ts` là `datetime` **có múi giờ**, ghi ra UTC dạng `2019-03-04T08:15:00Z`. `ts` không có múi giờ thì `ValueError`.
- `prediction` không hữu hạn (NaN, vô cực) thì `ValueError`, không ghi gì.
- `features` chỉ giữ các khoá nằm trong `ALLOWED_FEATURES` (danh sách cho phép, không phải danh sách cấm): số điện thoại
  hay tên khách không bao giờ vào log dù ai đó thêm vào `features`.
- Giá trị chứa ký tự xuống dòng không được làm vỡ cấu trúc một dòng.

**`join_labels(lines, labels) -> JoinResult`** nối log với nhãn thật. `lines` là iterable các dòng log (chuỗi), `labels` là
iterable các `{"request_id", "actual_seconds"}`.

- Mỗi dự đoán khớp nhãn cho một dòng trong `rows` với khoá `request_id`, `ts`, `model_version`, `prediction`,
  `actual_seconds`, `abs_error`; sắp theo `ts` rồi `request_id`.
- Dòng log không phải JSON object, thiếu `request_id` hoặc `ts` dạng chuỗi, hoặc `prediction` không phải số hữu hạn: bỏ qua và
  tăng `bad_lines`. Dòng trống bỏ qua không đếm.
- Nhãn thiếu `request_id` dạng chuỗi hoặc có `actual_seconds` không phải số hữu hạn: bỏ qua và tăng `bad_labels`. Hai nhãn
  cùng `request_id` thì lấy cái sau.
- Cùng `request_id` xuất hiện nhiều lần trong log (client retry): giữ dòng có `ts` mới nhất.
- `unmatched_predictions` là số dự đoán chưa có nhãn (nhãn thường về trễ); `orphan_labels` là số nhãn không có dự đoán tương ứng.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/09-monitoring-observability/exercises/basic/02-prediction-log -q` pass, gồm một ca chạy
  trên 2 000 chuyến thật của NYC TLC tháng 3 năm 2019 (cần `data/raw/nyc-tlc`; thiếu thì test đó skip).
- MAE tính từ `rows` khớp MAE tính trực tiếp bằng NumPy trên cùng dữ liệu.
- Bạn nêu được vì sao `request_id` phải có trong log và vì sao không được có trong label của metric.

## Gợi ý

### Gợi ý 1

`json.dumps(record, ensure_ascii=False, separators=(",", ":"))` cho một dòng gọn; JSON tự escape `\n` bên trong chuỗi. Với
`ts` dùng `ts.astimezone(timezone.utc).strftime(...)`.

### Gợi ý 2

Dựng hai dict trước: `request_id -> bản ghi mới nhất` và `request_id -> nhãn`. Sau đó mọi con số (`unmatched_predictions`,
`orphan_labels`) chỉ là phép hiệu giữa hai tập khoá.
