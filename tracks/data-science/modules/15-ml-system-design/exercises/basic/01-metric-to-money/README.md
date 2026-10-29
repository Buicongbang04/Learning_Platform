---
title: Đổi metric model ra tiền
level: basic
services: []
files:
  - path: starter/value.py
    note: 4 hàm TODO
  - path: tests/test_value.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/basic/01-metric-to-money -q
---

## Mục tiêu

Trả lời câu hỏi đầu tiên của mọi dự án ML có hành động: ở precision nào thì hành động có lãi, và một
ngưỡng cụ thể mang lại bao nhiêu tiền so với không làm gì. Khác module 11, ở đây hành động chỉ cứu được
**một phần** thiệt hại (uplift), nên một model hoàn hảo vẫn có thể lỗ.

## Đề bài

Bối cảnh Olist: hành động trên một đơn tốn `cost_action`; một review xấu thiệt `loss_event`; hành động
trên một đơn **thật sự** trễ giảm xác suất review xấu đi `effect` (số tuyệt đối, ví dụ 0.15). Hành động
trên đơn không trễ không có lợi gì. So với không làm gì: TP mang lại `effect * loss_event - cost_action`,
FP mang lại `-cost_action`, FN và TN mang lại 0. Dự đoán dương khi `p >= threshold`.

Trong `starter/value.py`:

1. `confusion_counts(y_true, p, threshold) -> dict` với khoá `tp`, `fp`, `fn`, `tn` (số nguyên).
2. `expected_value(y_true, p, threshold, cost_action, loss_event, effect) -> float`: **tổng** giá trị
   (R$) của chính sách so với không làm gì.
3. `break_even_precision(cost_action, loss_event, effect) -> float`: precision tối thiểu để có lãi.
   Trả về đúng công thức, kể cả khi lớn hơn 1 (nghĩa là không bao giờ có lãi).
4. `best_threshold_value(y_true, p, cost_action, loss_event, effect) -> (threshold, value)`: ngưỡng làm
   `expected_value` lớn nhất, ứng viên là mọi giá trị p phân biệt và `np.inf` (không hành động, giá
   trị 0).

Sau đó thử với giả định của lý thuyết: `loss_event=30`, `effect=0.15`, gọi điện 5 R$ và tin nhắn 0.5 R$.

## Tiêu chí đạt

- Đếm confusion và giá trị đúng trên ví dụ tính tay.
- `break_even_precision(0.5, 30, 0.15)` bằng 1/9; `break_even_precision(5, 30, 0.15)` lớn hơn 1.
- Giá trị dương khi và chỉ khi precision của nhóm được chọn vượt break-even.
- `best_threshold_value` đạt đúng giá trị lớn nhất (so với vét cạn) trên 10 seed; khi break-even > 1
  thì chọn `np.inf` với giá trị 0.

## Gợi ý

### Gợi ý 1

`expected_value = tp * (effect * loss_event - cost_action) - fp * cost_action`. Viết lại theo số đơn
được chọn k và precision π: `k * (π * effect * loss_event - cost_action)`. Giải `= 0` theo π.

### Gợi ý 2

Vét cạn mọi ngưỡng là O(n²) nhưng đủ nhanh với vài nghìn dòng. Cách O(n log n): sắp p giảm dần,
`np.cumsum(y)` cho TP khi lấy top i đơn; nhớ gộp các p bằng nhau (chọn ngưỡng t là chọn **mọi** đơn có
`p >= t`).
