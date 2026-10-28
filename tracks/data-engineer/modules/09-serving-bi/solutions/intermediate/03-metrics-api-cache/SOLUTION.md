# Lời giải: Lớp serving cho API metric có cache và phân trang

Xem `serving.py` cùng thư mục.

## Thứ tự xử lý một request

1. **Validate và chuẩn hoá** (`validate`). Mọi thứ người dùng gửi đều bị kiểm tra theo whitelist: state đúng 2 chữ
   cái, ngày đúng định dạng, khoảng ngày có giới hạn, `limit` có trần. Giới hạn khoảng ngày và `limit` không chỉ để
   đẹp: chúng chặn request kéo cả bảng làm nghẽn DB.
2. **Tra cache** với key gồm tham số đã chuẩn hoá và `data_version`. Chuẩn hoá trước khi tạo key giúp `sp` và `SP`
   dùng chung entry, tăng hit rate.
3. **Query tham số hoá** khi miss: một câu `COUNT(*)` cho `total`, một câu lấy trang với `ORDER BY` xác định
   (`order_date, customer_state`). Không có `ORDER BY` thì phân trang `LIMIT/OFFSET` có thể trả trùng hoặc sót dòng.
4. **Lưu cache** rồi trả body kèm `data_version` để client biết số liệu mới tới đâu.

## Invalidation bằng version

Khi pipeline refresh `agg_daily_sales` xong, nó ghi thời điểm refresh (ví dụ vào bảng `_serving_state` hoặc Redis).
`data_version()` đọc giá trị đó. Version đổi thì mọi key mới khác key cũ, nên không cần xoá cache thủ công, và
không bao giờ trả dữ liệu cũ sau refresh. TTL vẫn cần để giải phóng bộ nhớ và làm lưới an toàn.

## Đưa lên production

- Cache dùng Redis (chia sẻ giữa nhiều instance API) thay vì dict trong tiến trình.
- Với bảng lớn, `OFFSET` lớn chậm vì DB vẫn phải bỏ qua các dòng đầu. Dùng **keyset pagination**
  (`WHERE (order_date, customer_state) > (?, ?) ORDER BY … LIMIT ?`) và trả cursor.
- Thêm authN/authZ (seller chỉ xem dữ liệu của mình), rate limit, timeout query, log p95 latency và tỉ lệ cache hit.
- Chống cache stampede: khi nhiều request cùng miss một key nặng, chỉ một request được tính (lock hoặc single flight).
