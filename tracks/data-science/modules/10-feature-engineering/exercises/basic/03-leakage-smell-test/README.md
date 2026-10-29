---
title: Hai phép kiểm nhanh phát hiện leakage
level: basic
services: []
files:
  - path: starter/leak_check.py
    note: 3 hàm TODO
  - path: tests/test_leak_check.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/basic/03-leakage-smell-test -q
---

## Mục tiêu

Có sẵn hai công cụ chạy trước mọi lần train: (1) "AUC một mình" của từng feature để bắt feature tốt
tới mức đáng ngờ; (2) kiểm tra thời điểm ghi nhận để bắt feature chỉ có sau lúc dự đoán.

## Đề bài

Trong `starter/leak_check.py`:

1. `single_feature_auc(X, y)`: với mỗi cột số, ROC-AUC khi dùng chính cột đó làm điểm, lấy
   `max(AUC, 1 − AUC)` (feature tương quan âm cũng là tín hiệu). Bỏ dòng NaN của cột đang xét. Cột
   hằng hoặc chỉ còn một lớp cho 0.5. Sắp giảm dần.
2. `suspicious_features(X, y, threshold=0.9)`: tên các cột có AUC một mình từ ngưỡng trở lên.
3. `available_after(df, known_at, prediction_col)`: với mỗi feature, tỉ lệ dòng mà **thời điểm
   ghi nhận** của feature (cột trong `known_at`) muộn hơn thời điểm dự đoán. Chỉ tính dòng có đủ hai
   mốc, so sánh chặt.

Sau khi xong, chạy trên Olist thật với thời điểm dự đoán là lúc đơn vừa giao. Cột nào bị bắt? Vì sao
`order_estimated_delivery_date` có giá trị muộn hơn ngày giao ở 92% đơn mà vẫn hợp lệ?

## Tiêu chí đạt

- Bản sao nhiễu của nhãn (kể cả dấu âm) cho AUC gần 1 và bị gắn cờ; feature yếu không bị gắn cờ.
- NaN và cột hằng xử lý đúng.
- Trên Olist thật: `review_score` chỉ biết sau lúc giao ở 95.1% đơn, nội dung review 91.5%; ngày
  hẹn giao 0%; `comment_len` có AUC một mình 0.756, cao hơn cả `delay_days` (0.657).

## Gợi ý

### Gợi ý 1

`sklearn.metrics.roc_auc_score(y[ok], x[ok])` với `ok = ~np.isnan(x)`. Kiểm `len(np.unique(y[ok])) < 2`
trước khi gọi, vì AUC không xác định khi chỉ có một lớp.

### Gợi ý 2

AUC một mình cao chưa chắc là leakage (`delivery_days` thật sự mạnh), và leakage chưa chắc có AUC
cao (rò rỉ yếu vẫn làm điểm validation lạc quan). Đây là phép **sàng lọc**: cột bị gắn cờ phải được
giải thích bằng câu "giá trị này được ghi nhận lúc nào".
