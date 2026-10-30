---
title: Phân phối giá trị hoá đơn Online Retail II - mean vs median, histogram log, ECDF
level: basic
services: []
files:
  - path: starter/order_values.ipynb
    note: 3 hàm TODO + đọc 4 chart
  - path: tests/test_order_values.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/08-visualization-chart-reading/exercises/basic/03-order-value-distribution/starter/order_values.ipynb
  - uv run pytest tracks/data-analyst/modules/08-visualization-chart-reading/exercises/basic/03-order-value-distribution -q
---

## Mục tiêu

Trả lời câu hỏi "một hoá đơn điển hình đáng bao nhiêu?" trên dữ liệu bán lẻ thật có đuôi dài: làm
sạch đúng quy tắc trước khi cộng, tóm tắt phân phối bằng median và phân vị thay vì chỉ mean, và chọn
cách vẽ (histogram bin log, boxplot, ECDF) để người xem thấy được cả khối giá trị điển hình lẫn đuôi.

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2009-2010`** (525 461 dòng, 01/12/2009–09/12/2010; lý thuyết
module dùng sheet năm sau nên số liệu khác). Cell đầu notebook tự tải bộ này nếu chưa có
(`ensure("online-retail-ii")`). Mở `starter/order_values.ipynb`, làm lần lượt:

1. `invoice_totals(tx) -> Series`: tổng `Quantity * Price` mỗi hoá đơn, index là mã hoá đơn dạng
   chuỗi (tên `Invoice`). Bỏ hoá đơn huỷ (mã bắt đầu bằng `C`) và mọi dòng có `Quantity <= 0` hoặc
   `Price <= 0`, rồi mới cộng.
2. `summary_stats(s) -> dict` với khoá `mean`, `median`, `p90`, `p99`, `skew` (mặc định của pandas).
3. `log_bins(s, n) -> np.ndarray`: `n + 1` biên bin cách đều trên log10 từ min tới max;
   `ValueError` nếu có giá trị `<= 0`.
4. Chạy cell vẽ 4 cách nhìn cùng một phân phối: histogram tuyến tính, histogram bin log trên trục
   log, boxplot trên log10, ECDF; phóng to đoạn ECDF dốc bất thường.
5. Đọc chart theo quy trình 5 bước, chọn **một** chart và viết headline cho slide của Head of Sales.
   Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: bỏ đúng hoá đơn huỷ và dòng âm/0, mã hoá đơn `int`
  và `str` lẫn lộn đều thành chuỗi; thống kê khớp tính tay; biên bin log đúng và `np.histogram` đếm
  đủ mọi giá trị.
- Trên bộ thật: 20 951 hoá đơn hợp lệ, tổng khoảng 10.31 triệu GBP; median 300.84, p90 920.70,
  p99 4 098.96 GBP; skew khoảng 17.6.
- Notebook vẽ đủ 4 chart; ghi được chart nào bạn chọn cho slide và vì sao.
- Trắc nghiệm trong app: đúng ít nhất 5/7 câu.

## Gợi ý

### Gợi ý 1

`invoice = tx["Invoice"].astype(str)` trước, rồi tạo mặt nạ
`~invoice.str.startswith("C") & (tx["Quantity"] > 0) & (tx["Price"] > 0)`. Lọc **dòng** bằng mặt nạ
rồi `groupby(invoice[mask])`: hoá đơn có một dòng trả hàng vẫn giữ các dòng còn lại.

### Gợi ý 2

`np.logspace(np.log10(lo), np.log10(hi), n + 1)` cho biên cách đều trên log. Sai số làm tròn có thể
làm biên cuối nhỏ hơn `max` một chút và `np.histogram` bỏ sót điểm lớn nhất: gán lại
`edges[0], edges[-1] = lo, hi`.
