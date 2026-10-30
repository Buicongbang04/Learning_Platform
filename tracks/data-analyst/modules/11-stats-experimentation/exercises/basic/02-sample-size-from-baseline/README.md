---
title: Sample size và thời lượng thí nghiệm từ baseline thật của Online Retail II
level: basic
services: []
files:
  - path: starter/sample_size.ipynb
    note: 5 hàm TODO + trả lời trưởng nhóm CRM
  - path: tests/test_sample_size.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/11-stats-experimentation/exercises/basic/02-sample-size-from-baseline/starter/sample_size.ipynb
  - uv run pytest tracks/data-analyst/modules/11-stats-experimentation/exercises/basic/02-sample-size-from-baseline -q
---

## Mục tiêu

Trả lời câu "chạy A/B bao lâu thì biết?" bằng số thật thay vì cảm giác: đo baseline của metric chính và lưu
lượng người đủ điều kiện từ dữ liệu, tính sample size, số tuần và MDE, rồi nói "không" một cách có căn cứ khi
thí nghiệm không khả thi.

## Đề bài

Trưởng nhóm CRM muốn A/B test email chào mừng kèm voucher cho **khách mới** và tin rằng "chạy 4 tuần là biết".
Metric chính: tỉ lệ khách mới mua lần hai trong 60 ngày sau đơn đầu. Dữ liệu: bộ `online-retail-ii` (hai
sheet, 12/2009 tới 09/12/2011); notebook có sẵn hàm nạp dữ liệu (cache parquet trong thư mục tạm, dùng chung với
module 03). Mở `starter/sample_size.ipynb`, làm lần lượt:

1. `repeat_rate(invoices, window_days, cohort_start, data_end) -> (rate, n_eligible)`: baseline tỉ lệ quay lại,
   chỉ tính khách đã đủ cửa sổ quan sát (quy tắc chi tiết trong notebook). `customer_invoices` (một dòng mỗi
   hoá đơn hợp lệ có mã khách) đã viết sẵn.
2. `weekly_new_customers(invoices, start, end) -> Series`: số khách mới mỗi tuần thứ Hai-Chủ nhật.
3. `sample_size_per_arm(p0, mde_abs, alpha, power) -> int`: công thức hai tỉ lệ, hai phía, làm tròn lên.
4. `weeks_needed(n_per_arm, weekly_eligible, arms, share, min_weeks) -> int`: số tuần trọn, tối thiểu 2.
5. `mde_for_weeks(p0, weekly_eligible, weeks, ...) -> float`: MDE nhỏ nhất đạt được trong số tuần cho trước.
6. Chạy các cell `explore`: baseline 30/60/90 ngày, khách mới mỗi tuần năm 2011, bảng MDE → số tuần, đường
   MDE theo số tuần. Viết ba câu trả lời cho trưởng nhóm CRM. Báo cáo bài học: làm phần trắc nghiệm trong app
   sau khi chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: khách chưa đủ cửa sổ hoặc mua đầu trước `cohort_start` bị loại; hoá đơn cùng
  giờ với đơn đầu không tính là quay lại; sample size khớp giá trị tham chiếu và lệch dưới 1% so với
  `statsmodels`; số tuần làm tròn lên và có tối thiểu; MDE tìm được là nhỏ nhất thoả cỡ mẫu.
- Trên bộ thật: 36 969 hoá đơn có mã khách của 5 878 khách; baseline 60 ngày **35.2%** trên 4 563 khách đủ cửa
  sổ; 47 tuần năm 2011 có 1 488 khách mới; MDE +5 điểm % cần 1 474 khách mỗi nhóm, tức **94 tuần**.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Ngày mua đầu: `invoices.groupby("customer_id")["invoice_date"].min()`. Ghép lại vào `invoices` bằng
`join(first.rename("first"), on="customer_id")`, lọc hoá đơn `> first` và `<= first + pd.Timedelta(days=...)`,
lấy tập khách duy nhất, rồi `eligible.index.isin(...)`. Tuần: `.dt.to_period("W-SUN").value_counts().sort_index()`.

### Gợi ý 2

`norm.ppf(1 - alpha / 2)` và `norm.ppf(power)`; `math.ceil` cho cỡ mẫu và số tuần. Với MDE: cỡ mẫu giảm khi MDE
tăng, nên tìm nhị phân trên khoảng `(0, 1 - p0)`: nếu `sample_size_per_arm(p0, mid) <= available` thì thu `hi`
về `mid`, ngược lại đẩy `lo` lên `mid`.

### Đọc thêm

Bài DS [03/basic/02-power-sample-size](../../../../../../data-science/modules/03-ab-testing/exercises/basic/02-power-sample-size/README.md)
đi sâu power và phân phối thống kê kiểm định; bài này dừng ở việc biến baseline thật thành kế hoạch và câu trả
lời cho stakeholder.
