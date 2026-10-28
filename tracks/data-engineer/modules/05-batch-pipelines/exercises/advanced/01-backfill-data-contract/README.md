---
title: Pipeline theo ngày có data contract, quarantine và backfill an toàn
level: advanced
services: []
files:
  - path: starter/contract.yml
    note: 5 TODO
  - path: starter/pipeline.py
    note: 4 TODO
  - path: tests/test_contract_pipeline.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/advanced/01-backfill-data-contract -q
---

## Mục tiêu

Ghép các nguyên lý của module thành một pipeline có thể đưa vào vận hành: contract khai báo bằng
tệp, kiểm tra ở biên, cách ly dòng xấu thay vì làm sập pipeline, ngưỡng lỗi để chặn publish
(write-audit-publish), và backfill nhiều ngày chạy lại an toàn.

## Đề bài

Team checkout xuất mỗi ngày một file `orders_<ds>.csv` gồm
`order_id, customer_id, order_status, amount, order_purchase_timestamp`. Dữ liệu có lỗi: thiếu
khoá, status lạ, số tiền âm hoặc không phải số, timestamp hỏng, dòng trùng; có ngày không có file.

1. Hoàn thiện `starter/contract.yml` theo định dạng ghi ở đầu tệp: `order_id` bắt buộc và unique,
   `customer_id` bắt buộc, `order_status` thuộc `created, approved, shipped, delivered, canceled`,
   `amount` kiểu `number` với `min: 0`, `order_purchase_timestamp` kiểu `timestamp` bắt buộc.
2. Cài đặt `starter/pipeline.py`:
   - `load_contract(path)`.
   - `validate(rows, contract)` → `(good, bad)`. Dòng đạt đã ép kiểu (`amount` float, timestamp
     thành `datetime`). Dòng vi phạm là dict gốc + `_reason` (chứa tên cột vi phạm). Với cột
     unique, lần đầu hợp lệ, các lần sau vi phạm. Code phải đọc luật từ contract, không hard-code.
   - `run_partition(raw_dir, db_path, ds, contract_path, max_error_rate=0.2)`: ghi dòng vi phạm vào
     `quarantine_orders(ds, row_json, reason)` (thay quarantine cũ của `ds`); nếu tỉ lệ vi phạm
     **lớn hơn** ngưỡng thì raise `ContractViolation` và **không đụng** `fct_orders` của `ds`; ngược
     lại delete-insert partition `ds` của `fct_orders(order_id, customer_id, order_status, amount,
     purchased_at, ds)`. Trả về `{"ds", "loaded", "quarantined"}`.
   - `backfill(raw_dir, db_path, start, end, contract_path, max_error_rate=0.2)`: chạy từng ngày;
     ngày lỗi (thiếu file, vi phạm ngưỡng) ghi `{"ds": ds, "error": "..."}` và chạy tiếp.

Bài không có đáp án duy nhất: test chỉ khoá giao diện và hành vi; cách tổ chức code, thông báo lỗi,
dùng `jsonschema`/`pandera` hay tự viết bộ kiểm tra là quyết định của bạn.

## Tiêu chí đạt

- Contract đủ luật cho 5 cột.
- `validate` bắt đủ các loại lỗi và ép kiểu dòng đạt.
- Backfill 4 ngày: ngày 01 nạp 4/cách ly 1, ngày 02 nạp 5/cách ly 1 (trùng), ngày 03 báo lỗi thiếu
  file, ngày 04 báo lỗi vượt ngưỡng; `fct_orders` chỉ có ngày 01 và 02.
- Chạy backfill lần hai không đổi số dòng, tổng tiền, số dòng quarantine.
- File giao lại bị hỏng không ghi đè partition tốt đang có.
- Tự đánh giá thêm theo rubric trong lời giải.

## Gợi ý

### Gợi ý 1

Viết một hàm `_check(value, rule) -> (giá trị đã ép, lỗi | None)` cho từng cột, rồi `validate`
duyệt `contract["columns"]`. Giữ một `set` cho mỗi cột unique.

### Gợi ý 2

Thứ tự trong `run_partition`: đọc file → validate → tính tỉ lệ → (một transaction) ghi quarantine →
nếu vượt ngưỡng thì commit quarantine rồi raise, không thì delete-insert `fct_orders` → commit.
Lưu `row_json` bằng `json.dumps` của dict gốc (bỏ `_reason`).
