---
title: Pipeline ETL idempotent nạp đơn hàng theo ngày vào DuckDB
level: basic
services: []
files:
  - path: starter/pipeline.py
    note: 4 TODO
  - path: tests/test_pipeline.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/05-batch-pipelines/exercises/basic/01-idempotent-etl -q
---

## Mục tiêu

Viết một pipeline Extract → Transform → Load bằng Python thuần, tham số hoá theo ngày (`ds`) và
**idempotent**: chạy lại bao nhiêu lần cho cùng một ngày thì bảng đích vẫn đúng, không trùng dòng.

## Đề bài

Hệ thống nguồn xuất file CSV đơn hàng Olist (có thể chứa nhiều ngày, có dòng trùng, có dòng thiếu
`order_id`, `order_status` viết hoa lẫn khoảng trắng). Các cột:
`order_id, customer_id, order_status, order_purchase_timestamp, amount`.

Hoàn thành 4 hàm trong `starter/pipeline.py`:

1. `extract(csv_path)`: đọc CSV thành `pandas.DataFrame`, **mọi cột là chuỗi** (`dtype=str`), để
   bước transform tự quyết định kiểu.
2. `transform(df, ds)`: trả về DataFrame chỉ gồm các cột
   `order_id, customer_id, order_status, amount, ds` (đúng thứ tự này), trong đó:
   - chỉ giữ đơn có ngày của `order_purchase_timestamp` bằng `ds` (chuỗi `YYYY-MM-DD`);
   - bỏ dòng thiếu `order_id`;
   - `order_status` được `strip()` và viết thường;
   - `amount` là `float`;
   - mỗi `order_id` chỉ còn một dòng (giữ dòng xuất hiện **sau cùng** trong file);
   - cột `ds` chứa chính chuỗi `ds`; index được reset về 0..n-1.
3. `load(con, df, ds)`: nạp vào bảng `fct_orders(order_id VARCHAR, customer_id VARCHAR,
   order_status VARCHAR, amount DOUBLE, ds DATE)` trong DuckDB theo kiểu **delete-insert trong một
   transaction**: tạo bảng nếu chưa có, xoá partition `ds`, chèn dữ liệu mới. Nếu chèn lỗi thì
   rollback, dữ liệu cũ của `ds` còn nguyên. Không đụng tới các ngày khác. Trả về số dòng đã chèn.
4. `run(csv_path, db_path, ds)`: nối 3 bước trên với một kết nối DuckDB tới tệp `db_path`, đóng
   kết nối khi xong, trả về số dòng đã nạp.

## Tiêu chí đạt

- `extract` trả về DataFrame toàn cột kiểu chuỗi.
- `transform` lọc đúng ngày, bỏ dòng thiếu khoá, dedup giữ bản sau cùng, chuẩn hoá status và kiểu.
- Gọi `load` hai lần cùng `ds` thì số dòng của `ds` không đổi.
- Nạp lại `ds` với dữ liệu đã sửa thì dữ liệu cũ của `ds` bị thay hoàn toàn, ngày khác giữ nguyên.
- Khi chèn lỗi, partition cũ không bị mất.
- `run` chạy end-to-end trên tệp DuckDB và chạy lại vẫn cho cùng kết quả.

## Gợi ý

### Gợi ý 1

`pd.read_csv(path, dtype=str)`. Lấy ngày từ timestamp: `df["order_purchase_timestamp"].str[:10]`
hoặc `pd.to_datetime(...).dt.strftime("%Y-%m-%d")`. Dedup: `drop_duplicates("order_id", keep="last")`.

### Gợi ý 2

Với DuckDB: `con.execute("BEGIN")`, `con.execute("DELETE FROM fct_orders WHERE ds = ?", [ds])`,
`con.register("incoming", df)` rồi `INSERT INTO fct_orders SELECT order_id, customer_id,
order_status, amount, CAST(ds AS DATE) FROM incoming`, cuối cùng `COMMIT`. Bọc trong
`try/except` để `ROLLBACK` rồi `raise` lại lỗi.
