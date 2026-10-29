---
title: Stacking theo thời gian cho Olist và quyết định có đưa vào production
level: advanced
services: []
files:
  - path: starter/stacking.ipynb
    note: 4 hàm TODO + phân tích tự do
  - path: starter/REPORT.md
    note: Khuyến nghị cho Head of DS
  - path: tests/test_stacking.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/12-advanced-ml/exercises/advanced/01-olist-stacking/starter/stacking.ipynb
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/advanced/01-olist-stacking -q
---

## Mục tiêu

Cài stacking **đúng cách trên dữ liệu theo thời gian** (không rò rỉ tương lai vào dự đoán
out-of-fold), rồi làm việc khó hơn: quyết định nó có đáng chi phí vận hành không, bằng con số có
khoảng tin cậy chứ không bằng cảm giác "ensemble luôn tốt hơn".

## Đề bài

Bài toán review xấu của Olist, cùng định nghĩa, cùng điểm dự đoán (lúc đơn vừa giao xong) và cùng
mốc thời gian với module 10, 11 và bài Intermediate 01. "Dev" là train + validation (mua trước
2018-04-01); test giữ nguyên (2018-04 tới 2018-08). Mở `starter/stacking.ipynb`:

1. `expanding_folds(order, n_folds=4)`: sắp theo thời gian, chia `n_folds + 1` khối; fold k học
   trên khối 0…k, dự đoán khối k + 1. Trả list `(fit_idx, pred_idx)` theo vị trí.
2. `oof_predictions(models, X, y, folds)`: DataFrame OOF, mỗi cột một model, NaN ở khối đầu.
3. `to_logit(P, eps=1e-6)` và `fit_meta(oof, y)`: logistic regression trên logit của OOF, bỏ dòng
   NaN.
4. Phân tích trên dữ liệu thật: ít nhất 3 model tầng 1 khác bản chất; so model đơn, trung bình đơn
   giản và stacking trên test; bootstrap khoảng tin cậy cho chênh lệch giữa stacking và model đơn
   tốt nhất; tương quan OOF; chi phí vận hành.
5. Viết `starter/REPORT.md` theo khung có sẵn.

## Tiêu chí đạt

- Mỗi fold chỉ học trên dữ liệu **trước** khối nó dự đoán (test dùng một model "gián điệp" ghi lại
  thời điểm lớn nhất nó thấy); cửa sổ mở rộng dần; khối đầu không được dự đoán.
- OOF giữ đúng index của `X`; một model học thuộc lòng (1-NN) không đạt độ chính xác cao trên OOF.
- Meta-model là `LogisticRegression`, tin model có thông tin và gần như bỏ qua model nhiễu.
- `to_logit` đúng và không trả vô cực tại 0 hoặc 1.
- `REPORT.md` không còn TODO, ít nhất 300 từ; nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`out.iloc[pred_idx, out.columns.get_loc(name)] = ...` ghi theo vị trí mà không phụ thuộc index của
`X` (index của Olist sau `concat` không liên tục). Tạo model **mới** bằng `factory()` cho mỗi fold;
fit lại cùng một object sẽ khó kiểm soát trạng thái.

### Gợi ý 2

Meta-model học trên OOF của dev, nhưng khi dự đoán test, các model tầng 1 phải được **fit lại trên
toàn bộ dev**. Model fit trên nhiều dữ liệu hơn cho xác suất hơi khác phân phối OOF; với meta-model
tuyến tính ít tham số thì ảnh hưởng nhỏ, với meta-model phức tạp thì đáng lo. Bootstrap tập test
(resample dòng, tính lại cả hai AUC trên cùng mẫu) cho khoảng tin cậy của **chênh lệch**.
