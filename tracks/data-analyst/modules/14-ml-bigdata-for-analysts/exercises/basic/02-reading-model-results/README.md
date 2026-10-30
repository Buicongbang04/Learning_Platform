---
title: Đọc kết quả model churn - accuracy, confusion matrix và baseline trên Telco
level: basic
services: []
files:
  - path: starter/model_scorecard.ipynb
    note: 3 hàm TODO + so model với hai baseline
  - path: tests/test_model_scorecard.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py telco-churn
  - uv run jupyter lab tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/basic/02-reading-model-results/starter/model_scorecard.ipynb
  - uv run pytest tracks/data-analyst/modules/14-ml-bigdata-for-analysts/exercises/basic/02-reading-model-results -q
---

## Mục tiêu

Đọc kết quả một model phân loại như DA senior: dựng confusion matrix, so accuracy với baseline, dịch precision và
recall thành ngôn ngữ chiến dịch, thấy ngưỡng thay đổi chính sách gắn cờ thế nào, và so model với quy tắc đang dùng.

## Đề bài

Đội Data Science báo Head of Customer Care: *"Decision tree sâu 3 tầng, accuracy 77.7% trên tập test."* Head of Customer
Care hỏi bạn con số đó có tốt không, model bắt được bao nhiêu khách sắp rời, và có hơn quy tắc đang dùng (gọi khách
month-to-month gắn bó tối đa 12 tháng) không. Dữ liệu: bộ `telco-churn` (7 043 khách). Mở `starter/model_scorecard.ipynb`:

1. `confusion_table(y_true, y_pred)`: bảng 2 × 2 số đếm, index `actual` (0, 1), cột `predicted` (0, 1), luôn đủ 4 ô;
   khác độ dài thì `ValueError`.
2. `scorecard(y_true, y_pred)`: dict `n`, `accuracy`, `baseline_accuracy` (luôn đoán lớp đông nhất), `precision`,
   `recall`, `flagged_share`; chia cho 0 thì `0.0`.
3. `threshold_table(y_true, score, thresholds)`: mỗi ngưỡng một dòng, cột `threshold`, `flagged`, `tp`, `precision`,
   `recall`, `accuracy`; gắn cờ khi `score >= threshold`.
4. Chạy các cell `explore`: hai baseline trên toàn bộ khách, phân khúc hợp đồng hai năm, dựng lại tree của đội DS,
   đổi ngưỡng, so với quy tắc trên cùng tập test.

Ba hàm tự đếm bằng numpy/pandas, không dùng `sklearn.metrics`. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi
chạy notebook.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: đủ 4 ô kể cả khi model không đoán `1`, nhận bool, lỗi khi khác độ dài; baseline là lớp
  đông nhất; chia cho 0 ra `0.0`; ngưỡng tính `>=`, giữ thứ tự ngưỡng.
- Trên bộ thật: "luôn đoán ở lại" đúng 73.46% (97.17% trong nhóm hợp đồng hai năm); quy tắc có confusion matrix
  `[[4204, 970], [845, 1024]]`, precision 51.35%, recall 54.79%, gắn cờ 28.31% khách.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`np.asarray(y).astype(int)` đổi list, Series hay mảng bool về cùng một kiểu. Đếm một ô bằng `((yt == 1) & (yp == 0)).sum()`
và nhớ `int(...)` để ra kiểu `int` thuần.

### Gợi ý 2

Baseline accuracy là `max(số ca dương, số ca âm) / n`. Khi đọc bảng ngưỡng của decision tree, để ý điểm của tree chỉ
có vài giá trị (mỗi lá một tỉ lệ), nên nhiều ngưỡng cho cùng một kết quả: bạn không chọn được chính xác "gọi 400
khách" như với một model cho điểm liên tục.
