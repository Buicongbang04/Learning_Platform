---
title: Fairness theo vùng của hệ thống cảnh báo
level: intermediate
services: []
files:
  - path: starter/fairness.ipynb
    note: 5 hàm TODO + câu hỏi cuối notebook
  - path: tests/test_fairness.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/15-ml-system-design/exercises/intermediate/03-fairness-slices/starter/fairness.ipynb
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/intermediate/03-fairness-slices -q
---

## Mục tiêu

Kiểm tra một chính sách top k theo nhóm như một phần bắt buộc của đánh giá model: ai được chọn, ai bị bỏ
sót, ai bị làm phiền nhầm, và một biện pháp giảm chênh lệch tốn bao nhiêu giá trị.

## Đề bài

Nhóm là vùng của khách: Bắc / Đông Bắc (`N/NE`), São Paulo (`SP`), bang khác (`khác`). Mở
`starter/fairness.ipynb`:

1. `add_region(df, state_col="customer_state")`: thêm cột `region`, không sửa df gốc.
2. `select_top_k(scores, k)`: mặt nạ bool cho top k.
3. `slice_report(df, group_col, label_col, selected_col)`: mỗi nhóm `n`, `prevalence`, `selection_rate`,
   `precision`, `recall`, `fpr`, `share_of_selected`, `share_of_positives`; `nan` khi mẫu số bằng 0.
4. `disparity(report, metric, higher_is_better=True)`: `ratio` (min/max), `difference` (max − min),
   `worst_group`.
5. `allocate_by_need(scores, groups, k)`: chia k theo tổng xác suất của từng nhóm (largest remainder),
   chọn top trong nhóm.
6. Chạy cell `explore` (dữ liệu và model đã viết sẵn), trả lời câu hỏi cuối notebook.

## Tiêu chí đạt

- `slice_report` đúng trên ví dụ tính tay, kể cả trường hợp `nan`.
- `disparity` chọn đúng nhóm tệ nhất theo chiều của metric.
- `allocate_by_need` chọn đúng k, quota mỗi nhóm là phần nguyên hoặc phần nguyên + 1 của tỉ lệ, và là
  top trong nhóm.
- Trên Olist thật: tỉ lệ trễ N/NE 13.6%, SP 5.9%, bang khác 8.8% trên 96 470 đơn giao xong.
- Trả lời được vì sao không thể cân bằng mọi metric cùng lúc khi tỉ lệ nền khác nhau.

## Gợi ý

### Gợi ý 1

`df.groupby(group_col).groups` cho chỉ số của từng nhóm. Viết một hàm phụ chia an toàn trả `nan` khi
mẫu số bằng 0.

### Gợi ý 2

Largest remainder: `exact = need / need.sum() * k`, `quota = floor(exact)`, rồi cộng 1 cho
`k - quota.sum()` nhóm có `exact - quota` lớn nhất.
