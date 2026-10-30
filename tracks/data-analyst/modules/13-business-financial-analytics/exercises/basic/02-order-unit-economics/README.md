---
title: Unit economics đơn hàng và bảng kịch bản what-if (Online Retail II)
level: basic
services: []
files:
  - path: starter/unit_economics.ipynb
    note: 6 hàm TODO (bảng đơn, unit economics, P&L, hoà vốn, kịch bản) + đọc kết quả
  - path: tests/test_unit_economics.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/13-business-financial-analytics/exercises/basic/02-order-unit-economics/starter/unit_economics.ipynb
  - uv run pytest tracks/data-analyst/modules/13-business-financial-analytics/exercises/basic/02-order-unit-economics -q
---

## Mục tiêu

Tính contribution của từng đơn hàng từ doanh thu thật và một bộ giả định chi phí ghi rõ, gộp thành P&L thu nhỏ,
rồi trả lời hai câu của CFO bằng bảng kịch bản: có nên đặt giá trị đơn tối thiểu không, và tăng giá 5% được phép
mất bao nhiêu đơn.

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2010-2011`**, quy tắc dòng hợp lệ dùng chung của track (doanh thu gộp, GBP).
Bộ dữ liệu không có giá vốn hay chi phí giao hàng, nên notebook cho sẵn `ASSUMPTIONS` (**ví dụ giả định**): giá
vốn 60% doanh thu, phí thanh toán 2%, 8 GBP mỗi đơn, 0.25 GBP mỗi dòng hàng. Mở `starter/unit_economics.ipynb`:

1. `order_table(tx)`: mỗi hoá đơn một dòng, cột `revenue`, `lines`, `country`, `customer_id`.
2. `unit_economics(orders, assumptions, price_change=0.0)`, `pnl(ue, volume_change=0.0)`,
   `breakeven_order_value(lines, assumptions)`: contribution từng đơn khi giá đổi (giá vốn **không** đổi theo
   giá bán), P&L thu nhỏ, giá trị đơn hoà vốn.
3. `scenario_table(orders, assumptions, scenarios)` và `breakeven_volume_change(orders, assumptions, price_change)`.
4. Chạy các cell `explore`: P&L cả năm, contribution theo nhóm giá trị đơn và thị trường, bảng kịch bản, tornado
   độ nhạy. Trả lời bốn câu ở cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Định nghĩa chính xác của từng cột nằm trong notebook. Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: lọc dòng hợp lệ và `Invoice` trộn kiểu, giá vốn không đổi khi tăng giá, P&L và
  margin, kịch bản ghi đè giả định / ngưỡng đơn tối thiểu tính sau khi đổi giá / đổi số đơn, hoà vốn.
- Trên bộ thật: 19 960 đơn, doanh thu 10 666 702.54 GBP, contribution khoảng 3 761 141 GBP (35.26%); 1 023 đơn
  contribution âm, tổng chỉ khoảng −4 380 GBP; đơn tối thiểu 25 GBP còn 18 896 đơn, contribution +4 338 GBP; tăng
  giá 5% được mất tới khoảng 12.2% số đơn.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`groupby("Invoice").agg(revenue=("revenue", "sum"), lines=("revenue", "size"), country=("Country", "first"),
customer_id=("Customer ID", "first"))`. Trong `unit_economics`, tách hai biến: doanh thu gốc (cho giá vốn) và doanh
thu mới (cho doanh thu và phí thanh toán).

### Gợi ý 2

Contribution tỉ lệ thuận với số đơn khi mọi đơn co đều nhau, nên số đơn hoà vốn là
`contribution_hiện_tại / contribution_ở_giá_mới − 1`. Trong `scenario_table`, ghép giả định bằng
`{**assumptions, **thay_đổi}` nhưng chỉ lấy các khoá có trong `assumptions`.
