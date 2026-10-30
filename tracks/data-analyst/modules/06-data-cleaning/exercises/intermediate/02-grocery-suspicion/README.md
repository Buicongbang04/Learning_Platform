---
title: Nghi ngờ dữ liệu - chứng minh bộ Grocery Sales là sinh giả và không báo cáo insight
level: intermediate
services: []
files:
  - path: starter/grocery_suspicion.ipynb
    note: 6 hàm TODO + chart so với siêu thị thật + kết luận
  - path: tests/test_grocery_suspicion.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py grocery-sales-synthetic
  - uv run jupyter lab tracks/data-analyst/modules/06-data-cleaning/exercises/intermediate/02-grocery-suspicion/starter/grocery_suspicion.ipynb
  - uv run pytest tracks/data-analyst/modules/06-data-cleaning/exercises/intermediate/02-grocery-suspicion -q
---

## Mục tiêu

Tập phản xạ quan trọng nhất của DA trước khi báo cáo: **hỏi dữ liệu có mô tả thế giới thật không**. Bạn dùng kiểm
định thống kê (chi-square độ phù hợp, chỉ số phân tán) và chart so với một siêu thị thật để đi tới một kết luận có
bằng chứng: không báo cáo insight từ bộ này. Đồng thời tập làm việc với CSV 517 MB trên laptop yếu bằng DuckDB.

## Đề bài

Bộ `grocery-sales-synthetic` (7 bảng; `sales.csv` 6 758 125 dòng). Giám đốc vận hành xin năm báo cáo: doanh thu theo
tháng và danh mục, giỏ hàng và sản phẩm mua cùng, giờ cao điểm để xếp ca, khách VIP theo thành phố, xếp hạng 23 nhân
viên. Mở `starter/grocery_suspicion.ipynb` (DuckDB đọc thẳng CSV, giới hạn 1 GB RAM):

1. `sales_profile(con, table="sales")`: một câu SQL cho số dòng, số giao dịch, số dòng nhiều nhất một giao dịch, tỉ lệ
   `TotalPrice = 0`, tỉ lệ thiếu `SalesDate`, `Quantity` nhỏ nhất và lớn nhất.
2. `count_by(con, expr, table="sales")`: số dòng theo giá trị của một biểu thức SQL, bỏ `NULL`, sắp theo giá trị.
3. `uniformity_test(counts)`: `chi2`, `p_value` (`scipy.stats.chisquare`, kỳ vọng đều) và `max_min_ratio`.
4. `dispersion_index(counts)`: phương sai / trung bình.
5. `red_flags(profile, quantity_test, hour_test, daily_dispersion)`: năm cờ theo thứ tự cố định (bảng trong notebook).
6. Chạy các cell `explore`: bảng kiểm định cho 6 chiều (số lượng, giờ, ngày, nhân viên, sản phẩm, khách), bẫy thứ
   trong tuần, chart 4 panel so với dunnhumby (siêu thị thật, nếu đã tải), các bảng chiều. Viết kết luận một dòng cho
   Giám đốc vận hành. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Bộ dữ liệu không rõ giấy phép: chỉ dùng cục bộ, không commit trích mẫu, không đưa con số của nó vào báo cáo thật.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: hồ sơ đúng kiểu, `count_by` bỏ `NULL`, chi-square và chỉ số phân tán
  khớp tính tay, từng cờ bật đúng ngưỡng và đúng thứ tự.
- Trên bộ thật: 6 758 125 dòng và 6 758 125 giao dịch (mỗi giao dịch 1 dòng), 100% `TotalPrice = 0`, 1.0% thiếu
  `SalesDate`, `Quantity` 1 tới 25 với chi2 23.19, p 0.509; giờ trong ngày p 0.860, max/min 1.006; chỉ số phân tán số
  dòng mỗi ngày 0.916; đủ năm cờ đỏ.
- Kết luận trong notebook: không báo cáo insight, kèm bằng chứng cho từng báo cáo trong 5 yêu cầu.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Số dòng nhiều nhất của một giao dịch: subquery `SELECT max(n) FROM (SELECT count(*) AS n FROM sales GROUP BY
TransactionNumber)`. Tỉ lệ: `avg(CASE WHEN TotalPrice = 0 THEN 1.0 ELSE 0.0 END)`. `fetchone()` trả một tuple, nhớ ép
về `int` / `float` của Python.

### Gợi ý 2

p-value lớn không chứng minh "đều"; nó chỉ nói kiểm định không thấy khác biệt. Sức nặng của bằng chứng đến từ việc
**nhiều chiều độc lập cùng phẳng** (số lượng, giờ, ngày, nhân viên, sản phẩm, khách) trong khi siêu thị thật lệch mạnh
ở mọi chiều đó, cộng với các lỗi logic (cột tiền toàn 0, rượu vang trong danh mục "Snails").
