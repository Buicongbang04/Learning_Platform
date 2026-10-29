---
title: Đọc chart doanh thu Online Retail II - tháng đỉnh, thị trường, tháng thiếu dữ liệu
level: intermediate
services: []
files:
  - path: starter/retail_reading.ipynb
    note: 3 hàm TODO + đọc 3 chart
  - path: tests/test_retail_reading.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/08-visualization-chart-reading/exercises/intermediate/02-retail-chart-reading/starter/retail_reading.ipynb
  - uv run pytest tracks/data-analyst/modules/08-visualization-chart-reading/exercises/intermediate/02-retail-chart-reading -q
---

## Mục tiêu

Duyệt một bộ chart doanh thu trước khi nó tới tay CEO: sinh dữ liệu cho chart xu hướng, chart thành phần
và một chart kiểm độ phủ dữ liệu, rồi đọc theo quy trình 5 bước để tách điểm bất thường thật khỏi điểm
bất thường do dữ liệu (kỳ dở dang, nghỉ lễ, ngày không bán hàng).

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2010-2011`** (541 910 dòng, 01/12/2010 tới 09/12/2011, 13 tháng lịch).
Cell đầu notebook tự tải bộ này nếu chưa có. Quy tắc làm sạch như bài Basic 03: bỏ hoá đơn mã bắt đầu
bằng `C`, bỏ dòng `Quantity <= 0` hoặc `Price <= 0`; doanh thu dòng là `Quantity * Price` (GBP). Mở
`starter/retail_reading.ipynb`, làm lần lượt:

1. `monthly_revenue(tx) -> Series`: doanh thu theo tháng của `InvoiceDate`, index là ngày đầu tháng,
   liên tục (tháng không có dòng hợp lệ = 0), tên `revenue`.
2. `country_share(tx, top) -> Series`: tỉ trọng doanh thu của `top` nước lớn nhất (giảm dần) và một dòng
   `"Other"` ở cuối gộp phần còn lại (không có nếu không còn nước nào); tổng bằng 1, tên `share`.
3. `month_coverage(tx) -> Series`: số ngày lịch khác nhau có ít nhất một dòng hợp lệ trong mỗi tháng,
   cùng index với `monthly_revenue`, tên `days`.
4. Vẽ chart doanh thu tháng, bar ngang tỉ trọng quốc gia, số ngày giao dịch và doanh thu mỗi ngày giao
   dịch. Đọc theo quy trình 5 bước, viết lại headline chart doanh thu tháng cho CEO và quyết định cách vẽ
   tháng 12/2011. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: làm sạch đúng, tháng trống có mặt với 0, `Other` đúng vị trí
  và tổng bằng 1, đếm ngày khác nhau chứ không đếm dòng.
- Trên bộ thật: 13 tháng từ 12/2010 tới 12/2011, tổng khoảng 10.67 triệu GBP, tháng cao nhất 1.51 triệu
  GBP; top 5 nước và `Other` cộng lại bằng 1; tháng 11/2011 có 26 ngày giao dịch.
- Notebook vẽ đủ các chart; ghi được headline và cách xử lý tháng cuối.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Viết `_clean(tx)` một lần: `tx.loc[mask].assign(revenue=...)` không sửa `tx`. Doanh thu tháng:
`set_index("InvoiceDate")["revenue"].resample("MS").sum()` tự điền 0 cho tháng trống ở giữa.

### Gợi ý 2

Ngày lịch là `InvoiceDate.dt.normalize()`; bỏ trùng rồi đếm theo tháng. Để có index ngày đầu tháng liên
tục như `monthly_revenue`, nhóm theo `dt.to_period("M").dt.to_timestamp()` rồi
`.asfreq("MS", fill_value=0)`.
