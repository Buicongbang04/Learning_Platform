---
title: Bagging và out-of-bag estimate
level: basic
services: []
files:
  - path: starter/bagging.py
    note: 2 hàm TODO
  - path: tests/test_bagging.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/basic/02-bagging-oob -q
---

## Mục tiêu

Tự cài bagging để thấy tận mắt hai điều: lấy trung bình nhiều cây sâu (variance cao, bias thấp)
làm giảm mạnh sai số; và mỗi cây bỏ sót khoảng 37% dữ liệu, đủ để ước lượng sai số test **miễn
phí** (out-of-bag) mà không cần tập validation riêng.

## Đề bài

Trong `starter/bagging.py`:

1. `expected_oob_fraction(n) -> float`: xác suất một điểm không có mặt trong một mẫu bootstrap
   cỡ n (rút có hoàn lại n lần). Giới hạn khi n lớn là bao nhiêu?
2. `bagging_fit_predict(X_train, y_train, X_test, n_estimators=100, seed=0, max_features=None)`
   trả `(test_pred, oob_pred)`:
   - `rng = np.random.default_rng(seed)`; mỗi cây lấy chỉ số bootstrap `rng.integers(0, n, n)` và
     một `random_state` nguyên rút từ `rng`.
   - Cây là `DecisionTreeRegressor(max_features=max_features, random_state=...)`, **không** giới hạn
     độ sâu (bagging cần base learner variance cao).
   - `test_pred`: trung bình dự đoán của mọi cây.
   - `oob_pred[i]`: trung bình dự đoán của **chỉ những cây không thấy điểm i** khi train; `NaN` nếu
     không có cây nào như vậy.

`max_features < 1` biến bagging thành random forest: mỗi lần tách nút chỉ xét một phần feature,
làm các cây bớt giống nhau.

## Tiêu chí đạt

- `expected_oob_fraction` đúng với n = 1, 2, 10 và tiến về $$e^{-1}$$.
- Cùng seed cho cùng kết quả; khác seed cho kết quả khác.
- Một cây: khoảng 63% điểm có `oob_pred` là NaN.
- 100 cây bagging có MSE test dưới 75% MSE của một cây sâu (3 seed).
- OOB MSE lệch MSE test không quá 25% (3 seed), và không có NaN với 100 cây.
- `max_features=0.5` cho dự đoán khác bagging thường.

## Gợi ý

### Gợi ý 1

Mặt nạ out-of-bag của một cây: `out = np.ones(n, bool); out[idx] = False`. Giữ hai mảng cộng dồn
`oob_sum` và `oob_count`, chia ở cuối.

### Gợi ý 2

Đừng tính OOB bằng cách cho mọi cây dự đoán trên train rồi lấy trung bình: cây sâu thuộc lòng các
điểm nó đã thấy, nên sai số đó thấp hơn sai số thật rất nhiều. Test so OOB MSE với MSE trên tập
test riêng để bắt đúng lỗi này.
