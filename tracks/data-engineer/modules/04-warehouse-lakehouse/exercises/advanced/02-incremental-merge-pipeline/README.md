---
title: Pipeline nạp tăng dần idempotent với Delta MERGE và dữ liệu đến trễ
level: advanced
services: []
files:
  - path: starter/incremental.py
    note: 3 TODO
  - path: tests/test_incremental.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/04-warehouse-lakehouse/exercises/advanced/02-incremental-merge-pipeline -q
---

## Mục tiêu

Thiết kế một bước nạp tăng dần (incremental load) chịu được những gì luôn xảy ra ngoài đời: batch bị chạy lại,
bản ghi trùng trong cùng batch, bản cập nhật đến sai thứ tự, dữ liệu của ngày cũ đến trễ. Và chỉ tính lại phần gold
bị ảnh hưởng thay vì tính lại toàn bộ.

## Đề bài

Mỗi batch là một `pyarrow.Table` các phiên bản đơn hàng (CDC) với schema:
`order_id` string, `customer_state` string, `order_status` string, `order_purchase_timestamp` timestamp[us],
`order_value` double, `updated_at` timestamp[us]. Hoàn thiện `starter/incremental.py`:

1. `load_increment(silver_path, batch) -> set[datetime.date]`
   - khử trùng trong batch (mỗi `order_id` giữ bản `updated_at` lớn nhất);
   - thêm cột `order_date` (date, từ `order_purchase_timestamp`);
   - tạo bảng Delta silver nếu chưa có, ngược lại `MERGE` theo `order_id`: chỉ cập nhật khi bản mới có `updated_at`
     **lớn hơn**, chèn nếu chưa có;
   - trả tập `order_date` của các đơn **thực sự thay đổi** trong silver (được chèn hoặc được cập nhật). Batch chạy lại
     hoặc toàn bản cũ thì trả tập rỗng.
2. `refresh_gold(silver_path, gold_path, dates) -> int`
   - bảng Delta gold `daily_revenue(order_date, delivered_orders, revenue)` chỉ tính đơn `delivered`;
   - **chỉ tính lại các ngày trong `dates`**: thay toàn bộ dòng gold của các ngày đó bằng kết quả mới, không đụng
     ngày khác. Ngày không còn đơn delivered thì không có dòng;
   - `dates` rỗng thì không làm gì. Trả số dòng gold đã ghi trong lần gọi này.
3. `run_batch(silver_path, gold_path, batch) -> set[datetime.date]`: gọi hai bước trên, trả các ngày bị ảnh hưởng.

Viết thêm docstring đầu tệp: giải thích vì sao trả về "ngày bị ảnh hưởng" thay vì tính lại cả gold, và trường hợp nào
cách này sai (gợi ý: đơn đổi `order_purchase_timestamp`).

## Tiêu chí đạt

- Chạy lại cùng batch: silver và gold không đổi, hàm trả tập rỗng.
- Bản cập nhật cũ hơn đến sau không ghi đè bản mới hơn.
- Trùng khoá trong cùng batch không làm MERGE lỗi; bản mới nhất thắng.
- `refresh_gold` chỉ chạm các ngày được truyền vào.
- Sau một chuỗi batch, gold bằng đúng kết quả tính lại toàn phần từ silver.

## Gợi ý

### Gợi ý 1

Để biết đơn nào thực sự thay đổi, so batch đã khử trùng với silver hiện tại *trước khi* MERGE (join theo `order_id`,
giữ dòng chưa có hoặc có `updated_at` lớn hơn). Chính tập đó cũng là source cho MERGE. DuckDB `register` Arrow table
giúp viết phép so sánh này bằng SQL.

### Gợi ý 2

Thay dữ liệu một số ngày trong gold: `DeltaTable(gold).delete("order_date IN ('2024-03-01', ...)")` rồi
`write_deltalake(gold, new_rows, mode="append")`, hoặc dùng `write_deltalake(..., mode="overwrite", predicate=...)`
(dữ liệu ghi phải thoả predicate). Cách thứ hai nguyên tử trong một commit. Ép `order_date` sang kiểu `date32` thống nhất.
