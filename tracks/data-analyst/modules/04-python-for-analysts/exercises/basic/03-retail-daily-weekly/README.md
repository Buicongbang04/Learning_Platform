---
title: Trung bình mỗi ngày bán bao nhiêu - lưới lịch, resample tuần và kỳ chưa đủ trên Online Retail II
level: basic
services: []
files:
  - path: starter/retail_calendar.ipynb
    note: 4 hàm TODO (làm sạch, doanh thu theo ngày lịch, trung bình hai mẫu số, báo cáo tuần) + đọc kết quả
  - path: tests/test_retail_calendar.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/04-python-for-analysts/exercises/basic/03-retail-daily-weekly/starter/retail_calendar.ipynb
  - uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/basic/03-retail-daily-weekly -q
---

## Mục tiêu

Trả lời hai câu hỏi vận hành rất thường gặp, "trung bình mỗi ngày bán bao nhiêu?" và "doanh thu theo tuần kèm xu hướng",
bằng chuỗi thời gian pandas đặt trên **lưới lịch** đầy đủ: biết ngày không có dòng nghĩa là gì, chọn mẫu số có chủ
đích, và đánh dấu tuần chưa đủ thay vì để nó thành "kỷ lục".

## Đề bài

Bộ `online-retail-ii`, sheet **`Year 2010-2011`** (541 910 dòng, 01/12/2010 tới 09/12/2011). Quy tắc làm sạch dùng chung
của track: bỏ hoá đơn bắt đầu bằng `C`, bỏ dòng `Quantity <= 0` hoặc `Price <= 0`; doanh thu = `Quantity * Price`
(GBP, doanh thu gộp). Trưởng bộ phận vận hành cần số cho kế hoạch nhân sự kho. Mở `starter/retail_calendar.ipynb`:

1. `clean_sales(tx)` và `daily_revenue(tx)`: doanh thu mỗi ngày lịch, ngày không có đơn bằng 0.
2. `daily_average(daily)`: số ngày lịch, số ngày có bán, trung bình theo từng mẫu số.
3. `weekly_report(daily)`: tuần kết thúc Chủ nhật, số ngày có bán, số ngày lịch, cờ `complete`, trung bình 4 tuần chỉ
   trên tuần đủ.
4. Chạy các cell `explore` (ngày không bán theo thứ, trung bình theo thứ, tuần cao nhất, hoá đơn lớn tuần cuối, chart
   tuần), trả lời ba câu ở phần 4 notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: làm sạch theo dòng, lưới lịch có ngày 0, hai mẫu số, tuần đầu và tuần cuối chưa đủ,
  trung bình 4 tuần bỏ qua tuần chưa đủ.
- Trên bộ thật: 374 ngày lịch, 305 ngày có đơn, 69 ngày không có đơn (53 thứ Bảy); 28 520.60 GBP mỗi ngày lịch và
  34 972.80 GBP mỗi ngày có bán; 54 tuần, 52 tuần đủ; tuần cuối (kết thúc 11/12/2011) chỉ có 5 ngày và 504 328 GBP; tuần
  đủ cao nhất kết thúc 20/11/2011.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`clean_sales(tx).set_index("InvoiceDate")["revenue"].resample("D").sum()` tự tạo lưới ngày từ ngày đầu tới ngày cuối
và điền 0 cho ngày không có dòng. Đặt lại tên index và tên Series cho đúng yêu cầu.

### Gợi ý 2

Trong `weekly_report`, `daily.resample("W-SUN").size()` đếm số ngày lịch của mỗi tuần nằm trong dữ liệu;
`(daily > 0).resample("W-SUN").sum()` đếm ngày có bán. Với `rolling_4w`, `revenue.where(complete)` biến tuần chưa đủ
thành `NaN`, và `rolling(4).mean()` trả `NaN` cho mọi cửa sổ có `NaN`.
