# Lời giải: embedding đơn hàng và aggregation pipeline

## Thiết kế document

- **Embedding `items` và `customer`**: trang "chi tiết đơn" luôn đọc đơn cùng item; số item mỗi đơn nhỏ và có
  giới hạn, nên nhúng là hợp lý (một lần đọc, cập nhật nguyên tử).
- **Extended reference**: chép `category` vào từng item để báo cáo doanh thu theo category không cần `$lookup`.
  Đổi lại, nếu category của sản phẩm đổi thì đơn cũ vẫn giữ giá trị cũ — với đơn hàng điều đó thường là *đúng*
  (giá trị tại thời điểm mua), giống snapshot trong fact table.
- **Computed pattern**: lưu `total` khi tạo document để không phải tính lại mỗi lần đọc.
- Dựng `dict` tra cứu trước (O(n + m)) thay vì lồng vòng lặp (O(n × m)) — chuyện nhỏ với 6 dòng nhưng quan trọng
  với 100 nghìn đơn.

## Pipeline

- **Doanh thu theo category**: `$match` đầu tiên để lọc sớm (và dùng được index trên `status` ở MongoDB thật),
  `$unwind` biến mỗi item thành một document, `$group` theo `$items.category`. `$project` đổi `_id` thành
  `category` và bỏ `_id`. Item có category `None` vẫn được gom thành một nhóm, giống `GROUP BY` với NULL.
- **Theo tháng**: `$dateToString` với format `%Y-%m` làm khoá nhóm. Ở MongoDB thật có thể thêm `timezone`
  (`"America/Sao_Paulo"`) vì `Date` lưu UTC — chi tiết hay bị quên khi làm báo cáo theo ngày.
- **Rating**: gom trên `reviews` **trước** rồi mới `$lookup` — chỉ join số sản phẩm đã gom và đã lọc, không join
  từng review. Đây là quy tắc "giảm dữ liệu sớm" giống tối ưu SQL. `$unwind: "$product"` loại các review có
  product không tồn tại (giống INNER JOIN); muốn giữ thì dùng `preserveNullAndEmptyArrays: true`.

## Đối chiếu SQL

```sql
SELECT p.category, SUM(i.price) AS revenue, COUNT(*) AS items
FROM orders o JOIN order_items i USING (order_id) LEFT JOIN products p USING (product_id)
WHERE o.order_status = 'delivered'
GROUP BY p.category ORDER BY revenue DESC;
```

Với dữ liệu lớn trên MongoDB thật: thêm `allowDiskUse=True`, và cân nhắc `$merge` để ghi kết quả vào collection
tổng hợp (materialized view) thay vì tính lại mỗi lần.
