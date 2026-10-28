# Lời giải: Window functions

## Lấy bản ghi mới nhất (dedup)

`row_number()` trên window `partitionBy(order_id) orderBy(updated_at desc, order_status desc)` rồi giữ
`rn = 1`. Đây là mẫu chuẩn để gộp bảng CDC/append-only thành trạng thái hiện tại. So với
`groupBy(order_id).agg(max(updated_at))` rồi join ngược lại: window chỉ shuffle một lần và tự xử lý
trường hợp hoà (join ngược sẽ trả 2 dòng khi hai bản ghi cùng timestamp). Thêm khoá phụ vào `orderBy`
để kết quả **tất định**; nếu không, chạy lại có thể chọn dòng khác, phá vỡ tính idempotent.

## Running total

Mặc định khi có `orderBy`, frame là `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`: các dòng cùng
`order_date` được cộng gộp. Khai báo rõ `rowsBetween(unboundedPreceding, currentRow)` để biết chính xác
frame (với dữ liệu mỗi seller mỗi ngày một dòng thì hai cách như nhau).

## Xếp hạng

| Hàm | Doanh thu 100, 100, 80 |
| --- | --- |
| `row_number` | 1, 2, 3 |
| `rank` | 1, 1, 3 |
| `dense_rank` | 1, 1, 2 |

## Hiệu năng

Mỗi window với `partitionBy` khác nhau gây một `Exchange` + `Sort`. Window không có `partitionBy` dồn
toàn bộ dữ liệu vào **một** partition (Spark cảnh báo "No Partition Defined for Window operation"),
tránh trên dữ liệu lớn. Key partition lệch (một state có phần lớn seller) cũng gây skew như groupBy.
