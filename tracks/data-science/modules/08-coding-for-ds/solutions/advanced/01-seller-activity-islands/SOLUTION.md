# Hướng làm: seller của Olist hoạt động liên tục bao lâu?

## Hai query

**`streaks.sql`** (gaps-and-islands cổ điển):

```sql
WITH active AS (
    SELECT DISTINCT oi.seller_id, DATE_TRUNC('month', o.order_purchase_timestamp)::DATE AS month
    FROM order_items oi JOIN orders o USING (order_id)
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_purchase_timestamp < TIMESTAMP '2018-09-01'
), grouped AS (
    SELECT seller_id, month,
           DATE_DIFF('month', DATE '2000-01-01', month)
             - ROW_NUMBER() OVER (PARTITION BY seller_id ORDER BY month) AS grp
    FROM active
)
SELECT seller_id, MIN(month) AS start_month, MAX(month) AS end_month, COUNT(*) AS n_months
FROM grouped GROUP BY seller_id, grp
ORDER BY seller_id, start_month;
```

`DISTINCT` trước khi đánh số là bắt buộc: một seller có hai đơn trong cùng tháng (hoặc một đơn hai
món) sẽ làm `ROW_NUMBER` tăng mà tháng không tăng, phá khoá nhóm.

**`spells.sql`** (sessionization): thay khoá nhóm bằng cờ "bắt đầu đợt mới":
`CASE WHEN DATE_DIFF('month', LAG(month) OVER w, month) <= 2 THEN 0 ELSE 1 END` (dòng đầu: LAG là NULL,
so sánh cho NULL, rơi vào `ELSE 1`), rồi `SUM(is_new) OVER (PARTITION BY seller_id ORDER BY month)` là
số thứ tự đợt. `span_months = DATE_DIFF('month', MIN(month), MAX(month)) + 1`.

## Con số trên Olist thật (để đối chiếu ANALYSIS.md)

| Chỉ số | Giá trị |
| --- | --- |
| Seller có ít nhất một tháng hoạt động | 2 970 |
| Số chuỗi liên tiếp | 5 183 |
| Seller chưa từng bán 2 tháng liền (chuỗi dài nhất = 1) | 963 (32.4%) |
| Seller có chuỗi từ 6 tháng | 717 (24.1%) |
| Seller bán liên tục cả 20 tháng (01/2017 – 08/2018) | 35 |
| Số đợt (cho phép nghỉ 1 tháng) | 3 914 |
| Seller có hơn một đợt (nghỉ từ 2 tháng rồi quay lại) | 735 |
| Trung vị độ dài đợt (`span_months`) | 2 tháng |
| Seller có tháng hoạt động cuối ≤ 2018-06 ("đã rời bỏ" theo định nghĩa nghỉ từ 2 tháng) | 1 365 |
| Trong 1 715 seller bắt đầu bán trước 2018-01, tỉ lệ đã rời bỏ | 59.9% |

Đổi định nghĩa đổi con số: theo chuỗi liên tiếp, có 5 183 − 2 970 = 2 213 lần "kết thúc chuỗi" giữa
chừng; cho phép nghỉ 1 tháng còn 3 914 − 2 970 = 944 lần. Hơn một nửa các lần "ngừng bán" theo định
nghĩa chặt chỉ là nghỉ một tháng rồi quay lại: báo động "seller rời bỏ" theo định nghĩa chặt sẽ làm đội
Seller Success chạy theo nhiều báo động giả.

## Các quyết định cần cân nhắc trong ANALYSIS.md

- **"Hoạt động" là gì**: có đơn giao xong là định nghĩa của bài, nhưng seller có thể vẫn hoạt động
  (đăng sản phẩm) mà không có đơn. Nói rõ đây là "có doanh số", không phải "đang mở shop".
- **Ngưỡng rời bỏ**: nghỉ 1 hay 2 tháng? Dựa vào phân phối khoảng nghỉ: nếu phần lớn seller quay lại
  sau đúng 1 tháng nghỉ thì ngưỡng 2 tháng hợp lý. Đề xuất kiểm bằng dữ liệu, không phải cảm giác.
- **Right-censoring**: seller có tháng cuối 2018-07 hoặc 2018-08 chưa thể bị coi là rời bỏ. Tỉ lệ rời
  bỏ nên tính theo cohort tháng bắt đầu, chỉ trên seller đã có đủ thời gian quan sát.
- **Khuyến nghị có hành động**: ví dụ liên hệ seller ngay khi qua tháng thứ nhất không có đơn (trước
  khi chạm ngưỡng rời bỏ), ưu tiên seller có doanh thu/rating cao; đo hiệu quả bằng thí nghiệm (random
  seller nào được liên hệ), metric chính là tỉ lệ quay lại bán trong 60 ngày.
- **Hạn chế**: Olist công khai là mẫu; seller có thể bán qua kênh khác; mùa vụ (Black Friday 11/2017)
  làm tháng 12 trông như "nghỉ" với seller nhỏ.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| SQL đúng | 25 | Hai query qua test, đọc được (CTE đặt tên rõ), không phụ thuộc thứ tự ngẫu nhiên |
| Định nghĩa | 15 | Nêu rõ "hoạt động", "chuỗi", "đợt", "rời bỏ"; có ít nhất một con số so sánh khi đổi định nghĩa |
| Kết quả có số | 20 | Ít nhất 4 con số đúng từ query (phân phối độ dài, tỉ lệ chỉ bán 1 tháng, tỉ lệ quay lại, tỉ lệ rời bỏ theo cohort) |
| Right-censoring | 10 | Không gọi seller mới nghỉ ở cuối dữ liệu là rời bỏ; tỉ lệ tính trên nhóm đủ thời gian quan sát |
| Khuyến nghị | 20 | Cụ thể (ai, khi nào, làm gì), có cách đo hiệu quả (thí nghiệm hoặc tương đương) |
| Hạn chế và trình bày | 10 | Ít nhất 2 hạn chế thực tế; viết ngắn, người không làm data đọc được |

Đạt từ 70 điểm là đủ gửi cho trưởng nhóm Seller Success.
