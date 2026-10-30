---
title: Độ tập trung doanh thu và ngưỡng khách VIP trên Online Retail II - Pareto, Lorenz, Gini
level: advanced
services: []
files:
  - path: starter/concentration.ipynb
    note: 4 hàm TODO + phân tích ngưỡng VIP tự do
  - path: starter/MEMO.md
    note: Memo cho Head of CRM - trả lời ngắn, độ tập trung, ngưỡng, rủi ro, việc cần làm
  - path: tests/test_concentration.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/07-descriptive-eda/exercises/advanced/02-revenue-concentration/starter/concentration.ipynb
  - uv run pytest tracks/data-analyst/modules/07-descriptive-eda/exercises/advanced/02-revenue-concentration -q
---

## Mục tiêu

Biến một câu hỏi về độ phân tán ("doanh thu tập trung ở bao nhiêu khách?") thành quyết định kinh doanh: đo độ tập
trung bằng top share, Lorenz, Gini; so các ngưỡng VIP theo số khách và doanh thu; và nói rõ những gì làm con số bị
phóng đại hay bỏ sót.

## Đề bài

Head of CRM chuẩn bị chương trình khách VIP năm 2012 (quản lý tài khoản riêng, giá sỉ ưu đãi), ngân sách khoảng
400–500 khách, và hỏi: *"Có đúng là 20% khách mang 80% doanh thu không? Đặt ngưỡng VIP ở đâu, nhóm đó mang bao nhiêu
doanh thu, và có rủi ro gì?"* Dữ liệu: bộ `online-retail-ii`, sheet `Year 2010-2011`, theo định nghĩa dùng chung của
track (bỏ hoá đơn `C...`, bỏ dòng `Quantity <= 0` hoặc `Price <= 0`, doanh thu gộp, khách là `Customer ID` khác null).
Mở `starter/concentration.ipynb`:

1. `customer_revenue(tx)`: Series doanh thu mỗi khách (index `Customer ID`, tên `revenue`), sắp giảm dần.
2. `lorenz_curve(x)`: DataFrame `customer_share`, `revenue_share` với `n + 1` điểm từ `(0, 0)` tới `(1, 1)`.
3. `gini(x)`: hệ số Gini (công thức ở phần 3 lý thuyết).
4. `top_share(x, q)`: tỉ trọng của `ceil(q * n)` giá trị lớn nhất; `ValueError` nếu `q` ngoài `(0, 1]`.
   Ba hàm cuối báo `ValueError` khi dữ liệu rỗng, có NaN, có số âm hoặc tổng bằng 0.
5. Phân tích trong các cell `explore`: Pareto, Lorenz, các ngưỡng VIP ứng viên, và các bẫy (khách mới, vài khách lớn
   nhất, khách vãng lai, hàng trả).
6. Viết `starter/MEMO.md` theo khung: 200-600 từ, dòng đầu là headline có con số, đủ các mục.

Cell đầu notebook đọc xlsx một lần (20-90 giây) rồi lưu bản parquet vào thư mục tạm của hệ điều hành, các lần sau
đọc nhanh. Không ghi gì vào `data/raw/`.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: làm sạch đúng định nghĩa dùng chung, đường Lorenz đúng điểm, Gini bằng 0 khi mọi giá trị
  bằng nhau và bằng `1 - 2 × diện tích dưới đường Lorenz`, `top_share` làm tròn lên đúng, kiểm lỗi đầu vào.
- Trên bộ thật: 4 338 khách, tổng 8 911 425.90 GBP, khách lớn nhất là 14646; Gini 0.7151; top 20% mang 74.62%, top 1%
  mang 32.00% doanh thu.
- `MEMO.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Gini từ dữ liệu đã sắp tăng dần: `i = np.arange(1, n + 1)`, `2 * (i * a).sum() / (n * a.sum()) - (n + 1) / n`. Kiểm
bằng hai ca dễ: mọi giá trị bằng nhau (0) và một giá trị dương, còn lại bằng 0 (`(n - 1) / n`).

### Gợi ý 2

`np.ceil(0.2 * 10)` có thể ra 3 vì sai số dấu phẩy động (`0.2 * 10` không đúng bằng 2 trong máy). Trừ một lượng rất
nhỏ trước khi làm tròn lên, hoặc dùng `round` trước `ceil`. Với ngưỡng VIP, đừng chỉ nhìn top share: kiểm xem nhóm VIP
có mua đều không (số hoá đơn), mua lần đầu khi nào, ở nước nào.
