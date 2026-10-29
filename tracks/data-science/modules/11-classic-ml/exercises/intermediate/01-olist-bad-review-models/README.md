---
title: So sánh model kinh điển trên bài review xấu của Olist
level: intermediate
services: []
files:
  - path: starter/models.ipynb
    note: 4 hàm TODO + phân tích trong cell explore
  - path: tests/test_models.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/11-classic-ml/exercises/intermediate/01-olist-bad-review-models/starter/models.ipynb
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/intermediate/01-olist-bad-review-models -q
---

## Mục tiêu

Làm trọn một vòng modeling trên dữ liệu thật: dựng bảng đúng thời điểm dự đoán, chia theo thời gian, so năm họ
model kinh điển bằng nhiều metric, nhận ra overfitting và drift giữa validation và test, rồi chọn ngưỡng theo
chi phí.

## Đề bài

Dự đoán, lúc đơn vừa giao tới khách, đơn đó có bị review 1–2 sao không (định nghĩa chung của track: đơn giao
xong, review mới nhất, chia theo thời gian 2018-01-01 / 2018-04-01 / 2018-09-01). Mở `starter/models.ipynb`:

1. `build_dataset(orders, reviews, items, payments)`: một dòng mỗi đơn, 8 feature theo bảng trong notebook,
   nhãn `bad_review`.
2. `time_split(df)`: `(train, val, test)`.
3. `evaluate(y, p)`: dict `roc_auc`, `pr_auc`, `log_loss`, `brier` (dùng `sklearn.metrics`).
4. `compare_models(models, train, val)`: fit, chấm trên validation, thêm `train_roc_auc`, sắp theo `pr_auc`
   giảm dần.
5. Chạy các cell `explore`: so tỉ lệ nhãn và tỉ lệ trễ giữa ba tập, bảng so sánh model, chấm model tốt nhất
   trên test, chọn ngưỡng theo chi phí (liên hệ 5 R$, bỏ lỡ 30 R$). Trả lời các câu hỏi cuối notebook.

## Tiêu chí đạt

- `build_dataset` đúng trên dữ liệu nhỏ: lọc đơn, review mới nhất, gộp item và payment, đơn vị ngày là số thực.
- Biên chia thời gian đúng tới từng phút.
- `compare_models` phát hiện cây đầy đủ overfit (train ROC-AUC gần 1, validation thấp hơn nhiều).
- Trên Olist thật: 95 824 đơn, tỉ lệ review xấu 12.8%; train / validation / test là 43 362 / 20 468 / 31 994
  đơn; validation có 18.0% review xấu.
- Trả lời được vì sao ROC-AUC trên test thấp hơn validation nhiều.

## Gợi ý

### Gợi ý 1

`(a - b) / pd.Timedelta(days=1)` cho số ngày dạng thực. Gộp item: `groupby("order_id").agg(n_items=("order_item_id", "size"), n_sellers=("seller_id", "nunique"), ...)`.
Payment: merge `how="left"` rồi `fillna(1)`.

### Gợi ý 2

`log_loss` của sklearn cần `labels=[0, 1]` khi tập nhỏ chỉ có một lớp; clip p để cây đầy đủ (p = 0 hoặc 1)
không cho vô cực. Với `compare_models`, `pd.DataFrame(rows).T.sort_values("pr_auc", ascending=False)` với
`rows` là dict tên model → dict metric.
