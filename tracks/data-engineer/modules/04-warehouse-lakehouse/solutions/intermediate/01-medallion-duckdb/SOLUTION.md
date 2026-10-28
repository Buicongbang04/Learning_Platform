# Lời giải: Medallion với DuckDB

Xem `medallion.py`.

## Bronze: giữ nguyên, thêm metadata

- `all_varchar = true`: bronze là bản sao trung thực của nguồn. Nếu để DuckDB tự đoán kiểu, giá trị `abc` trong
  cột số hoặc `not-a-date` có thể làm hỏng cả lần nạp hoặc bị ép âm thầm. Lỗi kiểu dữ liệu là việc của silver.
- `_source_file`, `_ingested_at` phục vụ truy vết (lineage) và debug: dòng này đến từ đâu, lúc nào.
- Bronze không lọc gì, để có thể **replay** lại silver khi đổi quy tắc làm sạch mà không cần đọc lại nguồn.

## Silver: một nguồn sự thật đã làm sạch

- `TRY_CAST` biến giá trị hỏng thành NULL; sau đó quyết định theo quy tắc nghiệp vụ: thiếu khoá hoặc thời điểm
  đặt hàng thì bỏ (không thể dùng), thiếu giá trị thì giữ (vẫn đếm được đơn).
- Chuẩn hoá `lower(trim(status))` để `' Delivered '`, `DELIVERED` cùng là `delivered`.
- Khử trùng lặp bằng `QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY updated_at DESC) = 1`: xử lý cả dòng
  trùng y hệt lẫn nhiều phiên bản (CDC). Đây là cách silver trở thành "trạng thái hiện tại" của thực thể.
- Thực tế nên ghi các dòng bị loại vào một bảng quarantine để đếm và báo động.

## Gold: phục vụ câu hỏi nghiệp vụ

Bảng tổng hợp theo ngày, đúng thứ BI cần. Gold thường được thiết kế theo mô hình Kimball (fact/dim) hoặc
bảng aggregate rộng.

## Idempotency

Mỗi tầng ghi đè toàn bộ tệp đích bằng `COPY ... TO`, nên chạy lại không nhân đôi dữ liệu. Ở quy mô lớn
sẽ chuyển sang ghi đè theo partition hoặc `MERGE` trên Delta/Iceberg (bài intermediate/02 và advanced/02).
