# Lời giải: funnel vòng đời đơn hàng

## Cấu trúc query

1. `latest_review`: một review mỗi đơn bằng `QUALIFY ROW_NUMBER() ... = 1`. Không làm bước này thì đơn
   có hai review bị đếm hai lần ở bước 5 khi `LEFT JOIN`.
2. `flags`: một cột boolean cho mỗi bước. `COALESCE(r.review_score >= 4, FALSE)` để đơn không có review
   là `FALSE` rõ ràng thay vì NULL.
3. `steps`: 6 dòng ghép bằng `UNION ALL`, mỗi dòng `COUNT(*) FILTER (WHERE ...)` với điều kiện là
   **AND của mọi bước tới bước đó**. Đây là chỗ biến funnel độc lập thành funnel tuần tự.
4. Tỉ lệ: `LAG(orders) OVER (ORDER BY step)` cho bước trước (bước 1 không có dòng trước:
   `COALESCE(LAG(...), orders)` cho 1.0), `FIRST_VALUE(orders)` cho bước đầu, ép `::DOUBLE`.

Bản chặt chỉ đổi cờ: `order_approved_at >= order_purchase_timestamp`,
`order_delivered_carrier_date >= order_approved_at`, `order_delivered_customer_date >=
order_delivered_carrier_date`. So sánh có NULL cho NULL, nên cờ cũng đúng là "không đạt" cho đơn thiếu
mốc; `COALESCE(..., FALSE)` làm ý đồ rõ ràng.

## Kết quả trên Olist thật

| Bước | Tuần tự | Chặt |
| --- | --- | --- |
| purchased | 99 441 | 99 441 |
| approved | 99 281 | 99 281 |
| shipped | 97 644 | 96 285 |
| delivered | 96 455 | 95 082 |
| reviewed | 95 809 | 94 443 |
| good_review | 75 623 | 74 480 |

- **Chỗ rơi lớn nhất là trải nghiệm, không phải vận hành**: từ "có review" sang "review 4–5 sao" chỉ
  còn 78.9%. Các bước vận hành đều giữ trên 97%.
- **1 359 đơn được giao cho hãng vận chuyển trước khi được duyệt thanh toán.** Câu hỏi cho đội vận
  hành: đây là quy trình thật (hàng được xuất trước khi thanh toán được xác nhận), hay timestamp được
  ghi sai (múi giờ, nhập tay)? Câu trả lời quyết định nên dùng funnel nào cho
  dashboard. Không tự ý loại các đơn này khỏi mọi phân tích khi chưa biết nguyên nhân.
- 14 đơn có trạng thái giao xong nhưng thiếu mốc duyệt: funnel tuần tự dừng chúng ở bước 1, funnel độc
  lập sẽ đếm chúng ở bước "delivered". Đó là lý do tỉ lệ của funnel độc lập có thể vượt 100%.

## Lỗi hay gặp

- `COUNT(DISTINCT order_id)` sau khi join review chưa dedupe: vẫn đúng số đơn nhưng che mất việc join
  nhân dòng; sang metric khác (trung bình điểm) sẽ sai.
- Dùng `INNER JOIN` với review: mất toàn bộ đơn không có review ở mọi bước.
- Lọc `WHERE order_status = 'delivered'` ở đầu query: funnel chỉ còn các đơn đã tới cuối, mọi tỉ lệ
  thành gần 100%.
