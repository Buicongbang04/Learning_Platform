---
title: Isolation forest, autoencoder tuyến tính và PR-AUC trên gian lận thẻ
level: intermediate
services: []
files:
  - path: starter/fraud.ipynb
    note: 5 hàm TODO + nhận xét
  - path: tests/test_fraud.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py creditcard-fraud
  - uv run jupyter lab tracks/data-science/modules/12-advanced-ml/exercises/intermediate/03-fraud-anomaly/starter/fraud.ipynb
  - uv run pytest tracks/data-science/modules/12-advanced-ml/exercises/intermediate/03-fraud-anomaly -q
---

## Mục tiêu

Đo đúng một bộ phát hiện bất thường khi lớp dương chỉ chiếm 0.15%: tự viết average precision
(PR-AUC), đo precision/recall theo ngân sách cảnh báo, và so isolation forest với một autoencoder
tuyến tính (PCA reconstruction). Thấy tận mắt vì sao ROC-AUC 0.95 vẫn có thể là một hệ thống không
dùng được, và vì sao dữ liệu huấn luyện lẫn bất thường làm hỏng bộ phát hiện.

## Đề bài

Bộ `creditcard-fraud` (284 807 giao dịch, 492 gian lận). Mở `starter/fraud.ipynb`:

1. `day_split(df)`: ngày 1 (`Time < 86 400`) là train, ngày 2 là test.
2. `average_precision(y, score)`: $$\mathrm{AP} = \sum_n (R_n - R_{n-1}) P_n$$, tự viết, các điểm bằng
   nhau xét cùng một ngưỡng (khớp `sklearn.metrics.average_precision_score`).
3. `alert_metrics(y, score, n_alerts) -> {"precision", "recall"}` của `n_alerts` giao dịch điểm cao
   nhất.
4. `isolation_forest_scores(X_train, X_test, seed=0, n_estimators=200)`: điểm **cao = bất thường**.
5. `pca_reconstruction_scores(X_train, X_test, n_components=15)`: `StandardScaler` và `PCA` fit trên
   train; điểm là tổng bình phương sai số dựng lại.
6. Chạy cell so sánh và trả lời 3 câu hỏi ở cell cuối.

## Tiêu chí đạt

- AP khớp sklearn tới `1e-12`, kể cả khi có nhiều điểm bằng nhau; điểm ngẫu nhiên cho AP xấp xỉ tỉ
  lệ dương tính.
- `alert_metrics` đúng ví dụ tính tay.
- Isolation forest đúng chiều (bất thường điểm cao hơn) và bắt được outlier xa tâm; PCA bắt được
  điểm lệch khỏi mặt phẳng dữ liệu (AP > 0.95 trên dữ liệu mô phỏng).
- Điểm của một dòng không phụ thuộc các dòng khác trong test; chuẩn hoá theo thống kê của train.
- Trên dữ liệu thật: 144 786 / 140 021 giao dịch (281 / 211 gian lận); AP isolation forest trong
  khoảng 0.05–0.25; PCA học trên giao dịch sạch có AP ≈ 0.209 và PCA học trên mọi giao dịch train
  dưới 0.08.

## Gợi ý

### Gợi ý 1

Sort giảm dần, `tp = np.cumsum(y_sorted)`. Vị trí cuối của mỗi nhóm điểm bằng nhau là nơi
`s_sorted[i] != s_sorted[i + 1]` (và phần tử cuối cùng). Precision tại đó là `tp / (i + 1)`, recall
là `tp / y.sum()`.

### Gợi ý 2

`IsolationForest.score_samples` trả giá trị **cao cho điểm bình thường** (độ dài đường đi trung
bình lớn). Đổi dấu. Với PCA, `pca.inverse_transform(pca.transform(z))` là bản dựng lại của `z` từ
`n_components` thành phần chính.
