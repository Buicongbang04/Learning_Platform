---
title: Bắt drift đa biến bằng classifier phân biệt hai tập dữ liệu
level: intermediate
services: []
files:
  - path: starter/multivariate.py
    note: 4 hàm TODO (và hàm trợ giúp), có sẵn PSI từng feature
  - path: tests/test_multivariate.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py nyc-tlc
  - uv run python data/download_dataset.py nyc-tlc-2020
  - uv run pytest tracks/mlops/modules/10-drift-incidents/exercises/intermediate/02-multivariate-domain-classifier -q
---

## Mục tiêu

Dựng phép đo drift đa biến: huấn luyện một classifier phân biệt "dữ liệu tham chiếu" với "dữ liệu hiện tại"; AUC cao nghĩa là hai tập khác nhau theo cách nào đó, kể cả khi từng cột riêng lẻ trông giống hệt.

## Đề bài

Trong `starter/multivariate.py` đã có `feature_psi` và `max_feature_psi` (PSI từng cột, chạy được). Điền các hàm còn lại:

- `_domain_data(reference, current, features, seed, max_rows)` (hàm trợ giúp; test không gọi trực tiếp): mỗi tập lấy `n = min(len, max_rows)` dòng bằng `sample(n=n, random_state=seed)`; ghép hai tập,
  chỉ giữ cột `features`, NaN thành `-1`; nhãn `0` cho reference, `1` cho current (thứ tự ghép: reference trước).
- `domain_auc(reference, current, features, seed=0, n_splits=5, max_rows=20_000)`: `RandomForestClassifier(n_estimators=100, max_depth=8, random_state=seed, n_jobs=1)`,
  `StratifiedKFold(n_splits, shuffle=True, random_state=seed)`, `cross_val_predict(..., method="predict_proba")` lấy xác suất lớp 1, rồi `roc_auc_score`. Trả `float`. AUC cross-validated, không phải AUC trên dữ liệu đã học.
- `driver_features(reference, current, features, seed=0, max_rows=20_000)`: cùng dữ liệu miền và cùng loại model, fit trên toàn bộ; trả danh sách `(feature, importance)` (importance là `float`), giảm dần.
- `multivariate_verdict(reference, current, features, seed=0)`: dict có `max_psi` (từ `max_feature_psi`), `auc` (từ `domain_auc`) và `hidden_drift` là `bool`: `max_psi < 0.1` **và** `auc >= 0.7`.

Test dùng dữ liệu sinh: hai tập có phân phối biên giống nhau nhưng tương quan giữa `x` và `y` đổi từ +0.9 sang -0.9 (PSI từng cột gần 0, AUC trên 0.85). Test cuối dùng NYC TLC thật (mẫu 20 000 dòng, `seed=0`,
bốn feature `trip_distance`, `hour`, `PULocationID`, `passenger_count`): 2019-07 với 2019-12 và 2020-02 với 2020-04; tự skip nếu chưa tải.

## Tiêu chí đạt

- Tương quan đổi dấu: `max_feature_psi` dưới 0.1 và `domain_auc` trên 0.85; cùng phân phối: AUC trong 0.45 đến 0.55.
- Kết quả tất định theo `seed`; `max_rows` thật sự giới hạn số dòng mỗi tập; NaN được thay bằng `-1` (một cột chỉ khác ở tỉ lệ NaN vẫn phân biệt được).
- `driver_features`: cột nhiễu đứng cuối, tổng importance bằng 1, sắp giảm dần.
- Dữ liệu thật: đổi mùa AUC dưới 0.6, COVID trong 0.65 đến 0.85 và cao hơn đổi mùa ít nhất 0.1.

## Gợi ý

### Gợi ý 1

`pd.concat([ref[features], cur[features]]).fillna(-1)` và `np.r_[np.zeros(len(ref)), np.ones(len(cur))]`. `cross_val_predict(...)[:, 1]` là xác suất thuộc `current`.

### Gợi ý 2

`model.feature_importances_` khớp thứ tự cột của `X`; ghép với `features` rồi `sorted(..., key=lambda p: -p[1])`.
