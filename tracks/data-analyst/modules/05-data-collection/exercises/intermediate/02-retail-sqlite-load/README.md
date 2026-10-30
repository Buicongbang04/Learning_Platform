---
title: Nạp Online Retail II vào SQLite bằng SQLAlchemy - idempotent, có nhật ký, đối chiếu được
level: intermediate
services: []
files:
  - path: starter/retail_sqlite.ipynb
    note: 5 hàm TODO; schema cho sẵn; cell explore đọc Excel thật (1-2 phút)
  - path: tests/test_retail_sqlite.py
    note: Không sửa; test Postgres tự skip khi chưa bật dịch vụ
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/05-data-collection/exercises/intermediate/02-retail-sqlite-load/starter/retail_sqlite.ipynb
  - uv run pytest tracks/data-analyst/modules/05-data-collection/exercises/intermediate/02-retail-sqlite-load -q
---

## Mục tiêu

Biến một file Excel hơn một triệu dòng mà ai cũng đọc lại theo cách riêng thành **một** bảng SQL mọi người truy vấn
chung: nạp idempotent và atomic theo batch, ghi nhật ký nạp, dùng bind parameter, đối chiếu số dòng và doanh thu với
nguồn, viết SQL chạy được trên cả SQLite và Postgres.

## Đề bài

Bộ `online-retail-ii` (UCI, CC BY 4.0): `online_retail_II.xlsx`, sheet `Year 2009-2010` (525 461 dòng) và `Year
2010-2011` (541 910 dòng), hai sheet trùng nhau từ 01/12 tới 09/12/2010. Mở `starter/retail_sqlite.ipynb`:

1. `to_table(df)`: 8 cột tên `snake_case`, `invoice`/`stock_code` là chuỗi, `customer_id` kiểu `Int64`.
2. `load_batch(engine, df, batch_id, source, now)`: một transaction gồm xoá batch cũ, ghi `sales`, ghi lại `load_log`.
3. `monthly_revenue(engine, start, end)`: `month`, `revenue`, `invoices` trên dòng hợp lệ, `start`/`end` là bind
   parameter, SQL chạy được trên SQLite và Postgres.
4. `reconcile(engine, df, batch_id)`: so số dòng và doanh thu hợp lệ giữa nguồn và database.
5. Chạy các cell `explore`: đọc hai sheet, bỏ đoạn trùng khỏi sheet cũ, nạp vào `data/clean/online_retail.sqlite`,
   nạp lại để thấy idempotent, so tốc độ `to_sql` hai cách, đối chiếu, truy vấn doanh thu theo tháng. Báo cáo bài
   học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: nạp lại cùng batch không nhân đôi, chỉ thay đúng batch đó, lỗi lúc ghi giữ nguyên dữ liệu
  cũ, giá trị có dấu nháy không làm hỏng SQL, `reconcile` phát hiện dòng bị mất.
- Trên 20 000 dòng đầu sheet `Year 2010-2011`: doanh thu 12/2010 (tới ngày 9) là 399 971.28 GBP, 756 hoá đơn hợp lệ.
- Notebook trên dữ liệu đầy đủ: 1 044 848 dòng sau khi bỏ 22 523 dòng trùng; hai batch đối chiếu khớp; tháng 11/2011
  là 1 509 496.33 GBP, tăng 2.7% so với tháng 11/2010.
- Khi bật Postgres (`docker compose -f setup/docker-compose.yml up -d postgres`), test Postgres pass với cùng code.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`with engine.begin() as conn:` mở transaction, tự commit khi khối kết thúc bình thường và rollback khi có exception.
Mọi lệnh (DELETE, `to_sql(..., con=conn)`, INSERT log) phải dùng **cùng** `conn` đó; gọi `to_sql(..., con=engine)` sẽ
mở một kết nối khác, không nằm trong transaction của bạn.

### Gợi ý 2

`pd.read_sql(text(sql), conn, params={"start": start, "end": end})`. So ngày với chuỗi `YYYY-MM-DD` chạy được vì SQLite
lưu timestamp dạng chuỗi ISO (so theo thứ tự chữ) và Postgres tự ép chuỗi sang timestamp.
