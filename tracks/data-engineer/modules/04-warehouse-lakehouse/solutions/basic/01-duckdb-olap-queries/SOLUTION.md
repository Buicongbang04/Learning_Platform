# Lời giải: Truy vấn OLAP với DuckDB

## revenue_rollup.sql

`GROUP BY ROLLUP (state, month)` tương đương `GROUPING SETS ((state, month), (state), ())`: một lần quét bảng
cho ra cả dòng chi tiết, subtotal theo bang và grand total. Không cần `UNION ALL` ba truy vấn.

Lưu ý: ở dòng subtotal, cột bị "cuộn" lên có giá trị NULL. Nếu dữ liệu gốc cũng có NULL thật, dùng
`GROUPING(col)` để phân biệt (`GROUPING` = 1 nghĩa là NULL do ROLLUP sinh ra).

## top_products.sql

Hai bước: tổng hợp doanh thu theo `(category, product_id)` trong CTE, rồi đánh số bằng
`ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC, product_id)`. `QUALIFY` lọc trên kết quả
window function giống `HAVING` lọc trên aggregate.

Chọn `ROW_NUMBER` thay vì `RANK` vì đề yêu cầu đúng 2 dòng mỗi nhóm và phá hoà bằng `product_id`.
`RANK`/`DENSE_RANK` có thể trả nhiều hơn 2 dòng khi hoà.

## monthly_running.sql

Window function được tính sau `GROUP BY`, nên tổng hợp tháng trong CTE rồi:

- luỹ kế: `SUM(revenue) OVER (ORDER BY order_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`;
- MoM: `LAG(revenue)` lấy doanh thu tháng trước; tháng đầu `LAG` trả NULL nên phép chia cũng ra NULL.

Ghi rõ `ROWS BETWEEN ...` để tránh hành vi mặc định `RANGE` (gộp các dòng có cùng khoá sắp xếp).
