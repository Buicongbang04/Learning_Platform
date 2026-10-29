---
title: Feature selection bên trong cross-validation
level: advanced
services: []
files:
  - path: starter/selection.py
    note: 3 hàm TODO
  - path: starter/REPORT.md
    note: Báo cáo đề xuất bộ feature rút gọn
  - path: tests/test_selection.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/advanced/02-feature-selection -q
---

## Mục tiêu

Đo được leakage do chọn feature sai chỗ, đo độ ổn định của việc chọn feature, rồi dùng các công cụ
đó để đề xuất một bộ feature rút gọn cho model review xấu của Olist, có bằng chứng.

## Đề bài

1. Trong `starter/selection.py` (bộ chọn chung: `SelectKBest(f_classif, k)`, model:
   `LogisticRegression(max_iter=1000)`, điểm: ROC-AUC trung bình qua fold):
   - `leaky_selection_auc(X, y, k, cv)`: cách **sai**, chọn k feature trên toàn bộ dữ liệu rồi mới
     cross-validate. Viết ra để đo nó sai bao nhiêu.
   - `honest_selection_auc(X, y, k, cv)`: bước chọn nằm trong pipeline, học lại ở mỗi fold.
   - `selection_frequency(X, y, k, splits)`: tỉ lệ fold mà mỗi feature được chọn, chỉ học trên phần
     train của từng fold.
2. Trên Olist, với pipeline của bài Intermediate 02: đo permutation importance trên validation,
   thử bộ feature rút gọn, đo lại. Tự chọn công cụ (permutation importance, L1, độ ổn định theo
   fold thời gian…), miễn là mọi quyết định chọn feature chỉ dựa trên train và validation.
3. Viết `REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- 2 000 feature nhiễu, nhãn ngẫu nhiên: cách sai cho AUC trên 0.75, cách đúng nằm trong 0.3–0.7.
- Khi tín hiệu là thật, hai cách cho kết quả gần như nhau (chênh dưới 0.03).
- `selection_frequency` chọn đúng 5 feature thật ở ít nhất 80% fold, không dùng phần test của fold.
- Trên Olist thật, chia 4 fold thời gian trên train: `delivery_days` và `delay_days` được chọn ở mọi fold.
- `REPORT.md` không còn TODO, ít nhất 300 từ; chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`make_pipeline(SelectKBest(f_classif, k=k), LogisticRegression(max_iter=1000))` rồi
`cross_val_score(pipe, X, y, cv=cv, scoring="roc_auc").mean()`. `splits` có thể là generator: chuyển
thành `list` trước khi đếm số fold.

### Gợi ý 2

Permutation importance trên Olist: `sklearn.inspection.permutation_importance(pipe, val[cols], val.bad_review, scoring="roc_auc")`
với `cols` là các cột đầu vào của pipeline (không phải cột sau one-hot). `delivery_days`, `delay_days`
và `promised_days` tương quan với nhau: thử hoán vị **cả nhóm** cùng lúc và so với tổng importance
từng cột.
