---
title: KFold, GroupKFold và cross-validation theo thời gian
level: intermediate
services: []
files:
  - path: starter/validation.ipynb
    note: 3 hàm TODO + câu hỏi cuối
  - path: tests/test_validation.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/10-feature-engineering/exercises/intermediate/03-time-group-cv/starter/validation.ipynb
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/intermediate/03-time-group-cv -q
---

## Mục tiêu

Biết chọn cách chia cross-validation theo cách model sẽ được dùng: dự đoán cho tương lai thì chia
theo thời gian, dự đoán cho khách mới thì chia theo khách. Thấy trên dữ liệu thật và mô phỏng rằng
KFold ngẫu nhiên có thể cho con số đẹp, ổn định và sai.

## Đề bài

Trong `starter/validation.ipynb`:

1. `time_cv_splits(dates, n_splits=5, gap=0)`: list `(train_idx, test_idx)` là vị trí trong
   `dates` (có thể chưa sắp xếp), chia như `TimeSeriesSplit(n_splits, gap=gap)` trên thứ tự thời gian.
2. `cv_auc(make_model, X, y, splits)`: mỗi fold gọi `make_model()` lấy model mới, fit trên train,
   ROC-AUC trên test; trả mảng AUC theo fold.
3. `compare_schemes(make_model, X, y, dates, groups, n_splits=5, seed=0)`: DataFrame index
   `kfold`, `group_kfold`, `time`, cột `mean`, `std`. `kfold` là `KFold(n_splits, shuffle=True, random_state=seed)`.
4. Chạy các cell `explore` trên Olist (train + val làm dữ liệu phát triển) và trả lời bốn câu hỏi ở
   cell cuối.

## Tiêu chí đạt

- Mọi dòng train của một fold ở trước mọi dòng test; `gap` bỏ đúng số dòng; dữ liệu không sắp xếp
  vẫn đúng.
- `cv_auc` dùng model mới mỗi fold, khớp tính tay.
- Dữ liệu mô phỏng có drift theo thời gian: KFold cao hơn chia thời gian trên 0.1 AUC.
- Dữ liệu mô phỏng mỗi khách 10 dòng: KFold cao hơn GroupKFold trên 0.25 AUC; chia theo thời gian
  không chữa được rò rỉ này.
- Trên Olist thật: fold thời gian đầu tiên bắt đầu 2017-05-29, fold cuối kết thúc 2018-03-31.

## Gợi ý

### Gợi ý 1

`order = np.argsort(np.asarray(dates), kind="stable")`, rồi
`[(order[tr], order[te]) for tr, te in TimeSeriesSplit(n_splits, gap=gap).split(order)]`. `order[tr]`
đổi vị trí trong thứ tự thời gian về vị trí gốc.

### Gợi ý 2

`GroupKFold(n_splits).split(X, y, groups)` cần `groups`; `KFold(...).split(X)` thì không (truyền
`groups` cho KFold chỉ sinh cảnh báo). Std của AUC theo fold không phải khoảng tin cậy, nhưng std lớn
ở chia thời gian là thông tin: hiệu năng phụ thuộc giai đoạn.
