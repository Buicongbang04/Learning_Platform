---
title: Chọn ngưỡng theo ma trận chi phí
level: basic
services: []
files:
  - path: starter/threshold.py
    note: 3 hàm TODO
  - path: tests/test_threshold.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/basic/02-cost-threshold -q
---

## Mục tiêu

Biến xác suất thành quyết định theo tiền: tính chi phí kỳ vọng tại một ngưỡng, suy ra ngưỡng tối ưu lý
thuyết, và tìm ngưỡng tối ưu trên dữ liệu validation.

## Đề bài

Bối cảnh Olist: liên hệ chủ động một đơn tốn 5 R$; bỏ lỡ một đơn sẽ bị review xấu tốn 30 R$. Chi phí cho dưới
dạng dict `{"tp": ..., "fp": ..., "fn": ..., "tn": ...}` (khoá thiếu là 0). Dự đoán dương khi `p >= threshold`.

Trong `starter/threshold.py`:

1. `expected_cost(y_true, p, threshold, costs)`: chi phí trung bình mỗi mẫu.
2. `bayes_threshold(costs)`: ngưỡng tối ưu khi p đã calibrate, giải từ điều kiện dự đoán dương khi
   $$p\,C_{TP} + (1 - p)\,C_{FP} \le p\,C_{FN} + (1 - p)\,C_{TN}$$.
3. `best_threshold(y_true, p, costs)`: ngưỡng làm `expected_cost` nhỏ nhất trên chính dữ liệu, ứng viên là mọi
   giá trị p phân biệt và `np.inf` (không liên hệ ai).

## Tiêu chí đạt

- Chi phí tính tay đúng, kể cả khi TP cũng có chi phí.
- `bayes_threshold({"fp": 5, "fn": 30}) = 5/35`; khi liên hệ đúng cũng tốn 5 thì `5/30`.
- `best_threshold` đạt đúng chi phí nhỏ nhất trên lưới; với xác suất calibrated, nằm trong 0.06 quanh 5/35
  trên 10 seed.
- Khi liên hệ đắt hơn thiệt hại, `best_threshold` chọn không liên hệ ai.

## Gợi ý

### Gợi ý 1

Liên hệ có chi phí kỳ vọng $$p\,C_{TP} + (1-p)\,C_{FP}$$, không liên hệ có $$p\,C_{FN} + (1-p)\,C_{TN}$$.
Chuyển vế, gom theo p.

### Gợi ý 2

Lặp `expected_cost` qua mọi ngưỡng là O(n²) nhưng vẫn đủ nhanh với vài nghìn dòng. Cách O(n log n): sắp p giảm
dần, `cumsum` cho TP và FP khi lấy top k, rồi FN = tổng dương − TP, TN = tổng âm − FP.
