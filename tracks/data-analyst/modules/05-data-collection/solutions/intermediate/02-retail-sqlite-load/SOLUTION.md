# Lời giải: nạp Online Retail II vào SQLite

## Cách làm

- `to_table`: `rename(columns=COLUMNS)[list(COLUMNS.values())]` để cố định thứ tự cột, rồi ép kiểu từng cột. Cột
  `Invoice` trong Excel lẫn số (`536365`) và chuỗi (`C536379`); không ép thì SQL nhận khi `INTEGER` khi `TEXT`, và
  `invoice NOT LIKE 'C%'` hay so khớp hoá đơn giữa hai bảng cho kết quả lạ. `customer_id` ép `Int64` để ô trống thành
  `NULL` chứ không làm cả cột thành `17850.0`.
- `load_batch`: một khối `with engine.begin() as conn:` chứa DELETE batch, `to_sql(..., con=conn)`, DELETE + INSERT
  `load_log`. Khối này là transaction: lỗi ở bất kỳ bước nào thì rollback, dữ liệu cũ còn nguyên (test cố ý làm lỗi
  INSERT sau khi đã DELETE). Xoá-rồi-ghi theo `batch_id` là cách idempotent đơn giản nhất cho dữ liệu nạp theo lô;
  upsert theo khoá (`INSERT ... ON CONFLICT`) dùng khi có khoá tự nhiên, mà bảng dòng hoá đơn này không có (một hoá
  đơn có thể có hai dòng giống hệt nhau).
- `monthly_revenue`: một câu SQL với `:start`, `:end`; tháng lấy bằng `substr(CAST(invoice_date AS TEXT), 1, 7)` để
  cùng câu chạy trên SQLite và Postgres. Muốn tận dụng hàm riêng của từng hệ (`date_trunc`, `strftime`) thì dùng
  `sqlalchemy.func` hoặc tách SQL theo `engine.dialect.name`.
- `reconcile`: phía nguồn tính bằng pandas trên `to_table(df)`, phía database bằng hai câu `COUNT(*)` và `SUM` có bind
  parameter; so số dòng tuyệt đối, so doanh thu với dung sai 0.01 (cộng số thực theo thứ tự khác nhau lệch ở chữ số
  thập phân thứ 9).

## Con số trên dữ liệu đầy đủ

| Đại lượng | Giá trị |
| --- | --- |
| Dòng hai sheet | 525 461 + 541 910 = 1 067 371 |
| Dòng trùng 01–09/12/2010 trong sheet cũ | 22 523 |
| Dòng sau khi bỏ trùng | 502 938 + 541 910 = 1 044 848 |
| Doanh thu hợp lệ theo batch | 9 867 039.37 và 10 666 702.54 GBP, khớp nguồn |
| Tháng 12/2010 đúng / nếu không bỏ trùng | 823 746.14 / 1 262 598.79 GBP (+53%) |
| Tháng 11/2010 → 11/2011 | 1 470 272.48 → 1 509 496.33 GBP (+2.7%) |
| Tháng 12/2011 | 638 810.68 GBP, chỉ tới ngày 9 |
| Thời gian (máy tham chiếu) | đọc 2 sheet 62 giây; nạp 6–8 giây mỗi batch; truy vấn 25 tháng 0.9 giây |
| `to_sql` 50 000 dòng | `method=None` 0.4 giây, `method="multi"` 6.2 giây |
| Tệp SQLite | 183 MB (tệp Excel 46 MB, nén zip) |

## Giải thích trắc nghiệm

- **overlap-rows (c)**: 22 523 dòng của sheet cũ có `InvoiceDate >= 2010-12-01`, đúng bằng số dòng 01–09/12/2010 của
  sheet mới.
- **naive-december (b)**: 9 ngày đầu tháng 12/2010 là 438 852.65 GBP, hơn nửa doanh thu cả tháng (mùa mua quà Giáng
  sinh dồn đầu tháng), nên đếm hai lần làm tháng 12 cao thêm 53%, không phải "9/31".
- **reload (d)**: không có khoá chính trên `sales` (a, b sai); `to_sql(if_exists="append")` chỉ thêm (c sai).
- **read-vs-query (a)**: chênh hai bậc độ lớn: Excel là XML nén, phải giải nén và parse từng ô mỗi lần đọc.
- **nov-yoy (a)**: +2.7%. Không so tháng 12/2011 (9 ngày) với tháng 12/2010 (cả tháng).
- **bind-params (c)**: database nhận giá trị tách khỏi câu lệnh. Test truyền `"2010-12-01'"`: bản f-string lỗi cú pháp,
  bản bind parameter chạy bình thường. Với giá trị do người dùng nhập (filter trên dashboard, app Streamlit), f-string
  là lỗ hổng SQL injection.
- **to-sql-multi (d)**: `method="multi"` dựng một câu `INSERT ... VALUES (...), (...), ...` rất dài, SQLite phải parse
  câu đó và bị giới hạn số tham số mỗi câu; `executemany` của `sqlite3` chạy một câu đã chuẩn bị cho nhiều bộ giá trị.
  Với Postgres qua mạng, `multi` (hoặc `COPY`) lại thường nhanh hơn vì giảm số lần đi về: đo trước khi chọn.
- **outgrow-sqlite (a, b, c)**: SQLite khoá cả tệp khi ghi, chạy trong tiến trình của bạn, không có người dùng/phân
  quyền. Một triệu dòng (d) với SQLite là nhỏ.
