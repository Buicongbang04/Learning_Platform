# Lời giải: Đọc CSV lớn theo lô bằng generator

## Cách làm

**`read_rows`** đặt `with open(...)` *bên trong* generator, rồi `yield from csv.DictReader(f)`.
File chỉ mở khi vòng lặp đầu tiên gọi `next()`, và tự đóng khi generator chạy hết (hoặc bị
garbage-collect). Nếu mở file bên ngoài rồi trả `csv.DictReader(f)`, file sẽ bị đóng trước khi đọc.

**`batched`** dùng `islice` để lấy tối đa `size` phần tử từ *cùng một* iterator mỗi vòng. Nhờ không
gọi `list(iterable)` nên chạy được trên `itertools.count()` vô hạn. Toán tử walrus `:=` dừng vòng
lặp khi `islice` trả list rỗng. Python 3.12 có sẵn `itertools.batched` (trả tuple), đây là bản tự
viết để hiểu cơ chế.

**`parse_item`** gom việc đổi tiền vào `_money`: `Decimal` thay vì `float` để `0.10 + 0.20` đúng
bằng `0.30`. `Decimal("abc")` raise `InvalidOperation` nên phải bắt và đổi thành `ValueError` để
người gọi chỉ cần bắt một loại lỗi. Kiểm tra thêm `is_finite()` vì `Decimal("NaN")` hay
`Decimal("Infinity")` parse được.

**`revenue_by_seller`** nối các generator thành pipeline. Mỗi dòng lỗi được đếm rồi bỏ qua, job
không sập vì một dòng hỏng. Bộ nhớ chỉ gồm một lô cộng với dict kết quả (số seller), không phụ thuộc
số dòng của file.

## Vì sao

- Pipeline thật xử lý file hàng chục GB. Generator giữ bộ nhớ O(lô) thay vì O(file).
- Lô (batch) là đơn vị tự nhiên để ghi vào DB: `executemany` 1000 dòng một lần nhanh hơn nhiều so
  với 1000 lần insert lẻ, và là đơn vị để commit/checkpoint.
- Trong thực tế, dòng lỗi nên được ghi ra file/bảng reject kèm lý do (bài intermediate 02), không
  chỉ đếm.

## Mở rộng

- Đo bộ nhớ: tạo file 5 triệu dòng, chạy với `/usr/bin/time -v` và so với `pd.read_csv` cả file.
- So sánh với `duckdb.sql("SELECT seller_id, SUM(price + freight_value) FROM 'f.csv' GROUP BY 1")`.
