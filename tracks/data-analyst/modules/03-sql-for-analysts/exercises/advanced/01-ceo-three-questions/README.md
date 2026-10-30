---
title: Trả lời ba câu hỏi của CEO bằng SQL và một memo ngắn
level: advanced
services: []
files:
  - path: starter/q1_revenue_12m.sql
    note: Câu 1 - doanh thu 12 tháng, số đơn, AOV
  - path: starter/q2_new_vs_returning.sql
    note: Câu 2 - khách mới, quay lại, vãng lai theo tháng
  - path: starter/q3_markets.sql
    note: Câu 3 - thị trường ngoài UK, độ tập trung khách
  - path: starter/MEMO.md
    note: Memo 200-600 từ cho CEO
  - path: starter/run_query.py
    note: Chạy thử SQL trên dữ liệu thật, không cần sửa
  - path: tests/test_ceo.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run python tracks/data-analyst/modules/03-sql-for-analysts/exercises/advanced/01-ceo-three-questions/starter/run_query.py q1_revenue_12m.sql
  - uv run pytest tracks/data-analyst/modules/03-sql-for-analysts/exercises/advanced/01-ceo-three-questions -q
---

## Mục tiêu

Đi trọn một vòng làm việc thật của DA với SQL: nhận ba câu hỏi ngắn của CEO, tự chọn kỳ so sánh và định nghĩa,
viết truy vấn có thể chạy lại, kiểm con số, rồi trả lời bằng một memo mà CEO đọc trong hai phút.

## Đề bài

Ngày 10/12/2011 CEO nhắn: **"Trước buổi họp kế hoạch năm, cho tôi biết: (1) năm nay mình bán tốt hơn năm ngoái
không? (2) tiền đang đến từ khách mới hay khách cũ? (3) ngoài UK nên đầu tư thị trường nào?"**

Bảng `online_retail` như các bài trước. Dòng hợp lệ, doanh thu, khách và "khách mới trong tháng" theo định nghĩa
chung của track. Hai kỳ cố định (12 tháng đủ, bỏ 1-9/12/2011): `prev_12m` = `2009-12-01` tới trước `2010-12-01`,
`last_12m` = `2010-12-01` tới trước `2011-12-01`. Mỗi tệp là một câu `SELECT`; tên cột và thứ tự là phần test
chấm, cách tính bên trong do bạn quyết.

1. **`q1_revenue_12m.sql`**: hai dòng `prev_12m`, `last_12m` (theo thứ tự đó). Cột `period, revenue, orders`
   (số hoá đơn), `customers` (số khách có mã), `aov` (doanh thu / số đơn).
2. **`q2_new_vs_returning.sql`**: với mỗi tháng của `last_12m`, mỗi loại khách có doanh thu một dòng:
   `new` (tháng này là tháng mua hợp lệ đầu tiên của khách **trên toàn bộ dữ liệu**), `returning` (khách có mã,
   đã mua ở tháng trước đó), `guest` (`customer_id` NULL). Cột `month, customer_type, customers` (khách có mã khác
   nhau; `guest` là 0), `revenue`. Sắp theo `month, customer_type`.
3. **`q3_markets.sql`**: 10 nước (không tính United Kingdom) có `revenue_last` lớn nhất, sắp giảm dần. Cột
   `country, revenue_prev` (0 nếu không bán), `revenue_last, growth_pct` (`revenue_last / revenue_prev - 1`,
   NULL khi kỳ trước bằng 0), `customers_last` (khách có mã), `top_customer_share` (doanh thu của khách có mã lớn
   nhất / `revenue_last` của nước, kỳ `last_12m`).
4. **`MEMO.md`**: theo khung có sẵn, 200-600 từ, dòng đầu là headline có con số, mỗi mục "Câu" có số liệu và dẫn
   tệp `.sql`. Ngoài ba truy vấn bắt buộc, được viết thêm truy vấn kiểm tra (đặt trong `starter/`, không chấm).

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: kỳ nửa mở, bỏ dòng huỷ và giá 0, "mới" tính theo toàn bộ lịch sử và theo tháng,
  khách vãng lai tách riêng, growth `NULL` khi kỳ trước bằng 0, độ tập trung tính trên doanh thu cả nước.
- Trên bộ thật: `last_12m` 10 027 891.86 GBP, 19 141 đơn, 4 297 khách; doanh thu khách mới cả 12 tháng 754 193.58,
  khách quay lại 7 639 021.53; nước đứng đầu ngoài UK là EIRE; khách lớn nhất của Netherlands chiếm 98.1%.
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Trước khi viết SQL, viết ra định nghĩa và kỳ so sánh cho từng câu hỏi; CEO hỏi "năm nay" nhưng năm 2011 chưa
kết thúc. Mỗi con số trong memo phải chỉ được về một dòng kết quả. Tự kiểm: tổng `revenue` của `q2` qua 12 tháng
phải bằng `revenue` của `last_12m` ở `q1`.

### Gợi ý 2

"Mới" cần lần mua đầu trên **cả** dữ liệu: tính `min(month)` theo khách trong CTE không lọc kỳ, rồi mới lọc
tháng. Độ tập trung: gom doanh thu theo `(country, customer_id)` trong kỳ, `max` theo nước, chia cho doanh thu nước.
Một thị trường mà một khách chiếm 90% là một **khách hàng**, không phải một thị trường.
