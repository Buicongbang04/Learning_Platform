---
title: Precision@k theo ngân sách can thiệp
level: basic
services: []
files:
  - path: starter/budget.py
    note: 4 hàm TODO
  - path: tests/test_budget.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/basic/02-precision-at-budget -q
---

## Mục tiêu

Đánh giá model đúng cách nó được dùng: CSKH chỉ làm được k việc mỗi tuần, nên câu hỏi là "top k đúng
tới đâu", tuần nào cũng vậy. Thấy được vì sao ngân sách cố định cho precision rất khác nhau giữa tuần
yên ả và tuần khủng hoảng.

## Đề bài

Trong `starter/budget.py`:

1. `k_from_budget(budget, cost_per_action, n_candidates) -> int`: số hành động làm được, làm tròn
   xuống, không vượt `n_candidates`.
2. `precision_at_k(y_true, scores, k) -> float` và `recall_at_k(y_true, scores, k) -> float`: top k
   theo `scores` giảm dần. `k` lớn hơn số mẫu thì lấy hết. `k < 1` thì `ValueError`. Recall khi không có
   ca dương nào là `nan`. Thứ tự giữa các điểm bằng nhau tuỳ bạn (test dùng điểm phân biệt).
3. `weekly_at_k(df, k, week_col="week", score_col="score", label_col="label") -> pd.DataFrame`: mỗi
   tuần một dòng (index là tuần, sắp tăng dần), cột `n`, `positives`, `selected` (= min(k, n)), `hits`,
   `precision`, `recall`.

Sau khi xong, đọc lại mục 3 của lý thuyết: với số đơn trễ mỗi tuần từ vài đơn tới 565, k cố định nghĩa là gì?

## Tiêu chí đạt

- Đúng trên ví dụ tính tay, kể cả k vượt số mẫu và `ValueError` khi k < 1.
- Điểm ngẫu nhiên cho precision@k trung bình gần tỉ lệ dương; điểm hoàn hảo cho precision 1 khi k ≤ số
  ca dương.
- `weekly_at_k` đúng từng tuần, tuần ít đơn hơn k chỉ chọn n đơn.
- Tổng `hits` / tổng `selected` của `weekly_at_k` khớp precision gộp.

## Gợi ý

### Gợi ý 1

`np.argsort(-scores)[:k]` cho chỉ số top k. Nhớ ép `y_true` thành mảng numpy.

### Gợi ý 2

`df.groupby(week_col)` rồi với mỗi nhóm gọi lại `precision_at_k` / `recall_at_k` với
`min(k, len(group))`. Dựng list dict rồi `pd.DataFrame(rows).set_index(week_col)`.
