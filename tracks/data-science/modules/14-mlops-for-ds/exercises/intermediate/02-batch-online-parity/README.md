---
title: Batch và online dùng chung một logic feature
level: intermediate
services: []
files:
  - path: starter/scoring.py
    note: 3 hàm TODO
  - path: tests/test_scoring.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/intermediate/02-batch-online-parity -q
---

## Mục tiêu

Phục vụ cùng một model theo hai cách, job batch hằng ngày ghi bảng điểm và hàm online chấm từng
đơn, mà **không** sinh ra training-serving skew: cùng một đơn thì hai đường cho cùng một score tới
1e-12. Job batch phải chạy lại được an toàn (idempotent).

## Đề bài

Đội CSKH muốn hai thứ: mỗi sáng một bảng điểm nguy cơ review xấu cho các đơn giao hôm qua (batch),
và một API để app CSKH chấm ngay khi tổng đài viên mở một đơn (online). Model chấm lúc đơn vừa giao
xong, nên đầu vào là đơn thô có đủ ngày giao. Trong `starter/scoring.py`:

1. `make_features(orders) -> DataFrame`: từ đơn thô ra `order_id` + 12 cột `FEATURES`, đúng
   docstring. Nhận được cả cột thời gian kiểu datetime (batch đọc từ bảng) lẫn chuỗi ISO (JSON
   online). Không sửa đầu vào.
2. `score_batch(model, orders, model_version, out_dir, run_date) -> Path`: ghi
   `out_dir/run_date=<run_date>/scores.parquet` với cột `order_id, score, model_version, run_date`.
   Chạy lại cùng ngày thì **thay** phân vùng đó, không nhân đôi dòng; ngày khác giữ nguyên.
3. `score_online(model, payload, model_version) -> dict`: một đơn dạng JSON (timestamp là chuỗi,
   thiếu là `null`), trả `order_id`, `score` (kiểu `float` của Python), `model_version`.

Ràng buộc thiết kế: `score_online` và `score_batch` phải cùng gọi `make_features`. Viết logic
feature thứ hai cho đường online (ví dụ tính tay từ dict cho "nhanh") là cách skew sinh ra.

## Tiêu chí đạt

- Ví dụ tính tay đúng (số ngày theo giờ thật, không làm tròn ngày), cột số là `float64`,
  `payment_type` thiếu thành `"missing"`.
- Feature từ chuỗi ISO giống hệt feature từ datetime.
- Batch: đúng đường dẫn, đúng cột, score khớp model; chạy lại 3 lần vẫn một tệp, cùng số dòng; chạy
  lại với dữ liệu ít hơn thì không còn dòng cũ; phân vùng ngày khác không bị đụng.
- Online khớp batch tới 1e-12 cho cả 150 đơn, kể cả đơn thiếu `order_approved_at`, `payment_type`.
- Không sửa payload đầu vào.

## Gợi ý

### Gợi ý 1

`pd.to_datetime(col)` nhận cả datetime lẫn chuỗi ISO và biến `None` thành `NaT`; hiệu hai cột
datetime chia cho `pd.Timedelta(days=1)` cho số ngày dạng float, `NaT` thành NaN. Online:
`make_features(pd.DataFrame([payload]))`.

### Gợi ý 2

Idempotent: xoá thư mục phân vùng (`shutil.rmtree(..., ignore_errors=True)`) rồi ghi lại. Tốt hơn
nữa: ghi vào thư mục tạm cùng cấp rồi `rename`, để job chết giữa chừng không để lại phân vùng dở.
Với `payment_type`, `.where(col.notna(), "missing")` giữ nguyên giá trị có và thay giá trị thiếu.
