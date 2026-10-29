---
title: Tự cài metric phân loại
level: basic
services: []
files:
  - path: starter/metrics.py
    note: 5 hàm TODO
  - path: tests/test_metrics.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/basic/01-classification-metrics -q
---

## Mục tiêu

Hiểu metric phân loại tới mức tự cài được bằng numpy: precision, recall, F1, ROC-AUC, PR-AUC, log loss. Khi
đã cài một lần, bạn sẽ không còn nhầm "PR-AUC của model đoán bừa là 0.5" hay "ROC-AUC đo chất lượng xác suất".

## Đề bài

Trong `starter/metrics.py` (chỉ dùng numpy và scipy, **không** import sklearn):

1. `confusion_counts(y_true, y_pred)` trả dict `{"tp", "fp", "fn", "tn"}` kiểu `int`.
2. `precision_recall_f1(y_true, y_pred)`; mẫu số bằng 0 thì đại lượng đó là 0.0.
3. `roc_auc(y_true, scores)`: bằng thứ hạng (thống kê Mann-Whitney), tie tính 1/2, không lặp đôi một:

   $$
   \text{AUC} = \frac{\sum_{i:\,y_i = 1} r_i - n_+(n_+ + 1)/2}{n_+\, n_-}
   $$

   với $$r_i$$ là hạng (hạng trung bình cho các score bằng nhau), $$n_+$$, $$n_-$$ là số ca dương, âm.
4. `average_precision(y_true, scores)`: $$\text{AP} = \sum_k (R_k - R_{k-1})\,P_k$$ trên các ngưỡng là giá trị
   score phân biệt, từ cao xuống thấp; các ca cùng score vào cùng lúc. Khớp `sklearn.metrics.average_precision_score`.
5. `log_loss(y_true, p, eps=1e-15)`, clip p vào [eps, 1 − eps].

## Tiêu chí đạt

- Khớp sklearn (sai khác dưới 1e-9) trên dữ liệu ngẫu nhiên, kể cả khi có nhiều score trùng nhau.
- ROC-AUC không đổi khi biến đổi đơn điệu score; log loss thì đổi.
- Trên score ngẫu nhiên: ROC-AUC ≈ 0.5, PR-AUC ≈ tỉ lệ dương.
- Không import sklearn trong `metrics.py`.

## Gợi ý

### Gợi ý 1

`scipy.stats.rankdata` cho hạng trung bình khi có tie. Với PR-AUC, sắp score giảm dần
(`np.argsort(-s, kind="mergesort")`), tính `np.cumsum(y)` để có TP tại mỗi vị trí.

### Gợi ý 2

Để gom tie: vị trí cuối của mỗi nhóm score bằng nhau là `np.flatnonzero(np.diff(s_sorted))` cộng thêm vị
trí cuối mảng. Chỉ tính precision, recall tại các vị trí đó. Recall bắt đầu từ 0:
`np.diff(np.r_[0, recall])`.
