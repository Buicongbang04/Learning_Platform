---
title: Shadow mode không đổi response
level: basic
services: []
files:
  - path: starter/shadow.py
    note: Viết ShadowRunner, hiện trả dự đoán của shadow
  - path: tests/test_shadow.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/07-model-serving/exercises/basic/03-shadow-mode -q
---

## Mục tiêu

Chạy model ứng viên trên traffic thật mà người dùng không thấy gì: không đổi response, không thêm độ trễ, không thêm lỗi.

## Đề bài

`ShadowRunner(primary, shadow, log)`; `primary` và `shadow` có `.predict(rows) -> {"model_version": int, "predictions": [float, ...]}`; `log` là hàm nhận một dict. `starter/shadow.py` đang trả kết quả của shadow, tức là đổi cái người dùng thấy. Viết lại để:

- `predict(request_id, rows)` trả **đúng nguyên** dict mà `primary.predict` trả, không thêm khoá nào. Lỗi của primary được ném tiếp, và khi đó không ghi log shadow.
- Shadow chạy **ngoài đường của request** (thread nền) trên bản sao sâu của `rows`: shadow chậm 0.6 giây thì `predict` vẫn xong dưới 0.3 giây; shadow sửa tại chỗ `rows` không làm hỏng `rows` của người gọi hay dự đoán của primary.
- Mỗi lần shadow chạy xong, gọi `log(record)` đúng một lần với `record` gồm: `request_id`, `primary_version`, `primary` (danh sách dự đoán), `shadow_version`, `shadow`, `max_abs_diff` (độ lệch tuyệt đối lớn nhất giữa hai danh sách) và `error`.
- Shadow ném ngoại lệ: request vẫn thành công, log ghi `shadow=None`, `shadow_version=None`, `max_abs_diff=None` và `error` là chuỗi `"<TênLỗi>: <thông điệp>"`.
- `log` ném lỗi (vd. đĩa đầy) cũng không làm hỏng request.
- `drain(timeout=5.0)` chờ các shadow đang chạy; 40 request liên tiếp đều phải có đúng một bản ghi sau `drain`.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/07-model-serving/exercises/basic/03-shadow-mode -q` pass.
- Giải thích được shadow trả lời câu hỏi nào mà canary không trả lời được, và nó không trả lời được câu nào (tác động lên người dùng).
- Nói được điều gì xảy ra khi shadow chậm hơn nhịp đến của request và hàng đợi dài ra mãi.

## Gợi ý

### Gợi ý 1

`ThreadPoolExecutor` nhỏ; `copy.deepcopy(rows)` trước khi gọi primary (primary có thể sửa `rows`) và trước khi giao cho shadow.

### Gợi ý 2

Giữ tập các `Future` đang chạy để `drain` dùng `concurrent.futures.wait`. Bọc phần chạy shadow và phần ghi log trong hai `try/except` riêng.
