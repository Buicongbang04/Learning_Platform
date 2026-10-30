---
title: Metric tree doanh thu Online Retail II và phân rã thay đổi tháng so với tháng
level: intermediate
services: []
files:
  - path: starter/revenue_tree.ipynb
    note: 3 hàm TODO (cây theo tháng, phân rã LMDI) + đọc 3 cặp tháng
  - path: tests/test_revenue_tree.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/01-analyst-mindset/exercises/intermediate/01-revenue-metric-tree/starter/revenue_tree.ipynb
  - uv run pytest tracks/data-analyst/modules/01-analyst-mindset/exercises/intermediate/01-revenue-metric-tree -q
---

## Mục tiêu

Dựng metric tree doanh thu = doanh thu khách có mã (khách × tần suất × AOV) + doanh thu không mã, rồi trả lời câu
hỏi mỗi tháng của CEO "doanh thu đổi là nhờ đâu" bằng phân rã chính xác, không phụ thuộc thứ tự, cộng đúng bằng
mức thay đổi.

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2010-2011`** (541 910 dòng, 01/12/2010 tới 09/12/2011). Quy tắc làm sạch
dùng chung của track: bỏ hoá đơn bắt đầu bằng `C`, bỏ dòng `Quantity <= 0` hoặc `Price <= 0`; doanh thu dòng =
`Quantity * Price` (GBP, doanh thu gộp). Mở `starter/revenue_tree.ipynb`:

1. `monthly_tree(tx)`: mỗi tháng một dòng, cột `revenue`, `known_revenue`, `guest_revenue`, `customers`, `orders`,
   `frequency`, `aov` (định nghĩa chính xác trong notebook). Tích `customers * frequency * aov` phải bằng
   `known_revenue`.
2. `decompose(tree, m0, m1)`: đóng góp GBP của `customers`, `frequency`, `aov` (phân rã log LMDI trên
   `known_revenue`) và `guest` vào thay đổi doanh thu gộp; bốn số cộng lại đúng bằng mức thay đổi.
3. Chạy các cell `explore`: small multiples bốn nhánh, phân rã ba cặp tháng (12/2010 → 1/2011, 10 → 11/2011,
   11 → 12/2011), waterfall, các hoá đơn lớn nhất. Viết cho CEO một câu mỗi cặp tháng. Báo cáo bài học: làm phần
   trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: làm sạch theo dòng, `Invoice` trộn số và chữ, đếm đơn chỉ trên dòng có mã khách,
  tháng không có khách có mã, phân rã cộng đúng tổng, trường hợp `known_revenue` không đổi.
- Trên bộ thật: 13 tháng, tổng 10.67 triệu GBP, 83.5% có `Customer ID`; tháng 11/2011 có 1 664 khách, 2 657 đơn,
  347 679 GBP không mã; tháng 10 → 11/2011 tăng 354 517 GBP với đóng góp khách +218 570, tần suất +133 463,
  AOV −229 535, không mã +232 018.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Doanh thu gộp nhóm trên mọi dòng hợp lệ; ba cột `known_revenue`, `customers`, `orders` nhóm trên các dòng có
`Customer ID` rồi `join` vào theo tháng, `fillna(0)` cho tháng không có khách có mã. `nunique` cho số khách và
số hoá đơn.

### Gợi ý 2

Trong `decompose`, `L = (R1 - R0) / (log R1 - log R0)` với R là `known_revenue`; đóng góp của thành phần X là
`L * log(X1 / X0)`. Vì `log(R1/R0) = log(C1/C0) + log(F1/F0) + log(A1/A0)`, ba đóng góp cộng đúng `R1 - R0`.
Khi `R1 == R0`, công thức chia cho 0: dùng `L = R0`.
