---
title: Backfill theo tháng - N tháng, N artifact, tháng lỗi không kéo theo cả đợt
level: intermediate
services: []
files:
  - path: starter/backfill.py
    note: 3 hàm TODO
  - path: tests/test_backfill.py
    note: Không sửa
  - path: tests/conftest.py
    note: Dựng Prefect tạm, không sửa
run:
  - uv run pytest tracks/mlops/modules/05-training-pipelines/exercises/intermediate/01-backfill-months -q
---

## Mục tiêu

Viết backfill tham số hoá theo **tháng logic** (không theo ngày chạy): sinh đúng N artifact đặt tên theo tháng, an toàn khi chạy
lại, và biết nói rõ tháng nào xong, tháng nào bỏ qua, tháng nào lỗi.

## Đề bài

Dữ liệu mỗi tháng nằm ở `data_dir/trips-<YYYY-MM>.csv` với hai cột `distance_km`, `duration_s` (test tự sinh, không đọc dữ liệu
thật). Không cần Prefect server (xem `tests/conftest.py`). Trong `starter/backfill.py` cài:

1. `month_range(start, end)`: danh sách tháng `"YYYY-MM"` từ `start` đến `end`, gồm hai đầu, qua được ranh giới năm. Sai định dạng
   (`"2026-3"`, tháng 13) hoặc `start` sau `end` thì `ValueError`.
2. `train_month(month, data_dir, out_dir, seed=0)`: đọc tệp của tháng đó, fit `LinearRegression(distance_km -> duration_s)`,
   ghi `out_dir/model-<month>.joblib` và `out_dir/model-<month>.json` với `{"month", "rows", "mae", "data_sha256"}`
   (`mae` tính trên chính dữ liệu tháng đó, `data_sha256` là sha256 của tệp CSV). Trả dict metadata. Tệp CSV rỗng (chỉ có
   header) là lỗi; một tháng lỗi **không** được để lại tệp đầu ra dở dang. Tạo `out_dir` nếu chưa có.
3. `backfill(start, end, data_dir, out_dir, overwrite=False)`: flow Prefect chạy từng tháng, trả
   `{"done": [...], "skipped": [...], "failed": {tháng: thông báo}}`. Tháng đã có **cả hai** tệp đầu ra thì vào `skipped` và không
   bị đụng tới (từng byte), trừ khi `overwrite=True`. Một tháng lỗi (thiếu tệp, tệp rỗng) vào `failed` và các tháng còn lại vẫn chạy.

## Tiêu chí đạt

- `backfill("2025-12", "2026-03", ...)` sinh đúng 4 cặp `model-<tháng>.joblib` / `.json`, mỗi cặp mang `data_sha256` của tệp
  đúng tháng đó.
- Chạy một tháng riêng cho đúng cùng metadata như tháng đó bên trong một đợt backfill.
- Chạy lại đợt có sẵn 2 tháng: 2 tháng `skipped`, các tháng mới `done`; với `overwrite=True` thì train lại tất cả.
- Tháng thiếu tệp: nằm trong `failed`, không có tệp đầu ra của tháng đó, các tháng khác xong. Sửa dữ liệu rồi chạy lại thì xong.

## Gợi ý

### Gợi ý 1

Đổi `(năm, tháng)` thành số tháng liên tục `năm * 12 + tháng - 1` rồi `range`; đổi ngược bằng `//` và `%`. Kiểm định dạng bằng
một regex chặt thay vì để `int()` tự bắt lỗi.

### Gợi ý 2

Để không bao giờ có tệp dở dang, ghi ra tên tạm (`.tmp`) rồi `Path.replace` sang tên thật sau khi cả hai tệp đã ghi xong; kiểm
dữ liệu rỗng **trước** khi ghi bất cứ thứ gì. Muốn mỗi tháng là một task Prefect, bọc hàm thường bằng `task(train_month)` và gọi
trong flow; bắt ngoại lệ quanh lời gọi để một tháng lỗi không làm hỏng cả đợt.
