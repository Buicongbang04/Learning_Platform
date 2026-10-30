---
title: Experiment brief cho voucher khách đang hoạt động, kèm readout chạy thử bằng A/A test
level: advanced
services: []
files:
  - path: starter/experiment_brief.ipynb
    note: 6 hàm TODO + tính baseline, sample size, A/A trên dữ liệu thật
  - path: starter/BRIEF.md
    note: Experiment brief cho Giám đốc kinh doanh (400-1 000 từ)
  - path: tests/test_experiment_brief.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/11-stats-experimentation/exercises/advanced/01-experiment-brief/starter/experiment_brief.ipynb
  - uv run pytest tracks/data-analyst/modules/11-stats-experimentation/exercises/advanced/01-experiment-brief -q
---

## Mục tiêu

Viết một experiment brief như DA làm thật **trước** khi thí nghiệm chạy: đối tượng, chia nhóm, metric chính và
guardrail, sample size từ baseline thật, kiểm tra bắt buộc, quy tắc quyết định viết trước; rồi chạy thử toàn bộ
quy trình readout bằng A/A test để chắc rằng cách phân tích không tự sinh ra "hiệu ứng".

## Đề bài

Tiếp nối Basic 02: trưởng nhóm CRM bỏ ý tưởng email cho khách mới và đề xuất gửi **voucher 10%** dùng trong 30
ngày cho **khách đang hoạt động** (có mua trong 90 ngày qua), bắt đầu 1/9/2011 (kịch bản giả định; dữ liệu thật:
bộ `online-retail-ii`). Mở `starter/experiment_brief.ipynb`:

1. `eligible_customers(invoices, as_of, lookback_days)`: khách đang hoạt động tại ngày bắt đầu.
2. `outcome_window(invoices, customers, start, days)`: mua hay không và doanh thu trong 30 ngày của **mọi** khách
   trong danh sách (khách không mua là 0).
3. `assign_arm(customer_ids, salt, treatment_share)`: chia nhóm ổn định bằng hash (quy tắc chính xác trong
   notebook).
4. `mean_sample_size(sd, mde_abs, alpha, power)`: cỡ mẫu cho metric trung bình.
5. `readout(outcome, arm, cap, alpha)`: bảng kết quả hai metric (tỉ lệ mua: z-test; doanh thu: Welch, có cắt đuôi).
6. `aa_false_positive_rate(outcome, salts, metric, cap, alpha)`: tỉ lệ A/A test "có ý nghĩa".
7. Chạy các cell `explore`: baseline ở nhiều ngày bắt đầu, guardrail huỷ đơn, sample size cho hai metric có và
   không cắt đuôi, readout chạy thử, 200 lần A/A. Viết `starter/BRIEF.md` theo khung có sẵn.

## Tiêu chí đạt

- Các hàm đúng trên dữ liệu nhỏ: cửa sổ nửa mở `[as_of - 90 ngày, as_of)` và `[start, start + 30 ngày)`; khách
  không mua vẫn có dòng; hash đúng quy tắc, không phụ thuộc thứ tự, đổi salt thì chia lại; cỡ mẫu khớp
  `statsmodels`; readout khớp `proportions_ztest` và `scipy.stats.ttest_ind(equal_var=False)`.
- Trên bộ thật: 1 923 khách đang hoạt động ngày 1/9/2011, tỉ lệ mua 30 ngày 37.9%, độ lệch chuẩn doanh thu 2 332
  GBP (p99 = 3 674); salt `welcome-voucher-2011` chia 958 khách vào treatment; readout chạy thử cho chênh lệch
  doanh thu −186 GBP/khách khi không cắt đuôi, −5.8 khi cắt ở p99; 200 lần A/A có 5.5% "có ý nghĩa".
- `BRIEF.md` không còn TODO, đủ mục, mục sample size có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Brief tốt trả lời được câu "nếu kết quả ra X thì ta làm gì" **trước** khi có kết quả. Bắt đầu từ quyết định
(gửi voucher cho mọi khách hay không), suy ra ngưỡng đáng làm: voucher giảm 10% giá bán của các đơn dùng voucher
nhưng giá vốn giữ nguyên, nên doanh thu phải tăng đủ để lợi nhuận (không phải doanh thu) bù được phần giảm giá.
Chọn rõ metric chính đo theo giá niêm yết hay sau voucher, rồi tính ngưỡng hoà vốn **trên đúng metric đó** (hai
cách cho hai con số khác nhau). Rồi mới hỏi: với khoảng 960 khách mỗi nhóm, thí nghiệm có đủ nhạy để phân biệt
"không tác dụng" với "đủ hoà vốn" không?

### Gợi ý 2

So `readout` không cắt và có cắt đuôi trên cùng một lần chia A/A: một khách sỉ (75 nghìn GBP trong tháng 9) rơi
vào nhóm nào thì nhóm đó "thắng". Đó là lý do ngưỡng cắt phải **ghi trong brief trước khi chạy**: chọn ngưỡng sau
khi thấy kết quả là một dạng p-hacking.
