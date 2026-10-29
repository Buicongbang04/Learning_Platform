---
title: Notebook EDA và memo một trang cho Giám đốc vận hành Olist
level: advanced
services: []
files:
  - path: starter/eda.ipynb
    note: 3 hàm TODO + phân tích tự do
  - path: starter/MEMO.md
    note: Memo một trang theo SCQA
  - path: tests/test_eda.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/09-eda-storytelling/exercises/advanced/01-olist-eda-memo/starter/eda.ipynb
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/advanced/01-olist-eda-memo -q
---

## Mục tiêu

Làm trọn một vòng EDA có câu hỏi, có giới hạn thời gian, trên dữ liệu thật, rồi biến nó thành một
memo một trang khiến người đọc biết nên làm gì. Đây cũng là milestone "EDA và định nghĩa metric"
của capstone.

## Đề bài

Giám đốc vận hành hỏi: **"Vì sao review xấu tăng vọt đầu năm 2018, và nên làm gì?"** Bạn có hai
ngày. Mở `starter/eda.ipynb`:

1. `order_table(orders, items, reviews, customers, sellers)`: một dòng mỗi đơn giao xong có review,
   các cột theo docstring (tháng mua, bang khách, bang seller của item đầu tiên, số item, số seller,
   tổng tiền hàng, tổng phí vận chuyển, số ngày giao, số ngày hẹn, trễ, review xấu).
2. `rate_by(table, factor, target="bad", min_n=30, z=1.96)`: tỉ lệ theo nhóm với n, khoảng Wilson,
   `lift` so với tỉ lệ toàn bảng; bỏ nhóm nhỏ hơn `min_n`; sắp giảm dần.
3. `decompose_change(table, period_col, a, b, segment="late", target="bad")`: tách thay đổi tỉ lệ
   giữa hai kỳ thành phần **mix** (tỉ trọng segment đổi) và phần **rate** (tỉ lệ trong segment đổi):

   Segment chỉ có mặt ở một trong hai kỳ bị bỏ khỏi `mix` và `rate` (khi đó `mix + rate` có thể khác
   `total`; nên kiểm tra trước).

   $$
   \Delta = \underbrace{\sum_s (w_{b,s} - w_{a,s})\, r_{a,s}}_{\text{mix}} + \underbrace{\sum_s w_{b,s}\,(r_{b,s} - r_{a,s})}_{\text{rate}}
   $$

4. Phân tích tự do trong các cell `explore`: hiện tượng theo tháng (bỏ tháng chưa chín), yếu tố đi
   cùng review xấu, tách mix/rate, đào vào giao trễ (tuyến, ngày hẹn, category, seller), kiểm tra
   Simpson. Chọn 2–3 biểu đồ cho memo, mỗi biểu đồ có tiêu đề là kết luận.
5. Viết `starter/MEMO.md` theo khung SCQA có sẵn: tiêu đề là kết luận (có con số), 250–700 từ, đủ sáu
   mục.

## Tiêu chí đạt

- `order_table` đúng trên dữ liệu nhỏ (lọc, review mới nhất, item đầu tiên, tổng theo đơn, số ngày
  thực, trễ theo nguyên timestamp).
- `rate_by` khớp khoảng Wilson của statsmodels, xử lý tỉ lệ 0 và 1, `lift` trên toàn bảng.
- `decompose_change` đúng với mix thuần và thoả `mix + rate = total`.
- Trên Olist thật: 95 824 đơn, trễ 7.99%, review xấu 12.81%; AL đứng đầu (394 đơn), AP đứng cuối với
  66 đơn và khoảng tin cậy rộng hơn 10 điểm; tháng 1 → tháng 3/2018: tổng +7.47 điểm, mix +7.69,
  rate −0.22.
- `MEMO.md` không còn TODO, 250–700 từ, tiêu đề có con số, đủ sáu mục SCQA.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Viết câu hỏi trước khi vẽ. Với mỗi biểu đồ, ghi ra một câu "biểu đồ này trả lời câu hỏi …". Không
trả lời được thì không vẽ. Time-box: nửa ngày cho bảng và chất lượng dữ liệu, một ngày cho phân tích,
nửa ngày cho memo.

### Gợi ý 2

Phần mix gần bằng toàn bộ thay đổi nghĩa là: giá như tỉ lệ đơn trễ không đổi, review xấu đã gần như
không tăng. Đó là câu chuyện chính, nhưng chưa phải nhân quả (đơn trễ khác đơn đúng hẹn ở nhiều mặt).
Nói rõ điều đó trong mục Giới hạn, và chỉ ra bước tiếp theo để chắc chắn hơn.
