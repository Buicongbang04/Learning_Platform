# Lời giải: DataFrame cơ bản

## Cách làm

- `delivered_orders`: chuẩn hoá trạng thái bằng `F.lower(F.trim(...))` rồi so sánh. Dữ liệu thật hay
  có hoa thường, khoảng trắng lẫn lộn; chuẩn hoá trong điều kiện lọc giữ nguyên dữ liệu gốc.
- `add_purchase_month`: `to_timestamp` rồi `date_format(..., "yyyy-MM")`. Cách này an toàn hơn
  `substring` nếu sau này cột đã là kiểu timestamp.
- `revenue_by_state`: lọc trước rồi mới join (giảm dữ liệu đi qua shuffle), `select` chỉ những cột cần
  (column pruning), dùng `countDistinct("order_id")` vì join với `payments` nhân bản dòng khi một đơn
  trả bằng nhiều phương thức (voucher + credit card).

## Vì sao

- Các hàm không gọi action, chỉ trả DataFrame: người gọi quyết định khi nào chạy, Catalyst tối ưu cả
  chuỗi. Gọi `explain()` sẽ thấy filter được đẩy xuống trước join.
- `groupBy` là wide transformation, tạo một `Exchange` (shuffle) trong plan; `orderBy` tạo thêm một
  `Exchange rangepartitioning`.

## Sai lầm hay gặp

- Dùng `count("order_id")` thay vì `countDistinct`: đếm trùng đơn nhiều payment.
- Join `payments` trước khi lọc delivered: đúng kết quả nhưng shuffle nhiều hơn (Catalyst thường tự
  đẩy filter, nhưng không nên trông chờ với logic phức tạp).
