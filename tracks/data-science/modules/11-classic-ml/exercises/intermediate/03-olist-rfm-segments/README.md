---
title: Phân khúc khách Olist bằng RFM và k-means
level: intermediate
services: []
files:
  - path: starter/rfm.ipynb
    note: 5 hàm TODO + câu hỏi cuối notebook
  - path: tests/test_rfm.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/11-classic-ml/exercises/intermediate/03-olist-rfm-segments/starter/rfm.ipynb
  - uv run pytest tracks/data-science/modules/11-classic-ml/exercises/intermediate/03-olist-rfm-segments -q
---

## Mục tiêu

Phân khúc khách thật bằng RFM và k-means từ đầu tới cuối: dựng feature đúng khách, scale đúng, chọn k, mô tả
cụm cho đội CRM, và biết đánh giá khi nào phân cụm không phải công cụ đúng.

## Đề bài

Mở `starter/rfm.ipynb`. Khách là `customer_unique_id`; đơn giao xong như định nghĩa chung; snapshot 2018-09-01.

1. `rfm_table(orders, customers, payments, snapshot)`: index `customer_unique_id`, cột `recency` (ngày trọn),
   `frequency` (số đơn), `monetary` (tổng `payment_value`, đơn không có payment tính 0).
2. `prepare_features(rfm)`: `log1p` rồi chuẩn hoá.
3. `fit_kmeans(X, k, seed)`: `KMeans(n_clusters=k, n_init=10, random_state=seed)`.
4. `silhouette_by_k(X, ks, seed, sample_size=10_000)`.
5. `segment_profile(rfm, labels)`: `n`, `share`, `recency_median`, `frequency_mean`, `repeat_rate`,
   `monetary_median` theo cụm.
6. Chạy các cell `explore` (k-means không scale, silhouette theo k, hồ sơ cụm k = 2 và k = 4, PCA để vẽ, DBSCAN)
   và trả lời câu hỏi cuối notebook.

## Tiêu chí đạt

- `rfm_table` đúng trên dữ liệu nhỏ: gộp hai `customer_id` của cùng một người, bỏ đơn huỷ và đơn sau snapshot,
  cộng nhiều dòng payment, đơn không có payment.
- `fit_kmeans` tái lập được và khôi phục cụm rõ ràng (ARI > 0.95); `silhouette_by_k` chọn đúng k trên dữ liệu
  có 3 cụm.
- Trên Olist thật: 93 350 khách, 3.0% mua từ 2 đơn trở lên, monetary trung vị khoảng 107.8 R$.
- Đặt tên được 4 cụm và đề xuất hành động; giải thích vì sao silhouette chọn k = 2 không có ích.

## Gợi ý

### Gợi ý 1

Cộng payment theo `order_id` trước (`groupby("order_id").payment_value.sum()`), rồi merge `how="left"` vào đơn
và `fillna(0)`. Recency: `(snapshot - last_purchase).dt.days`.

### Gợi ý 2

`silhouette_score(X, labels, sample_size=..., random_state=seed)` khi `len(X) > sample_size`, ngược lại để
`sample_size=None`. Với `repeat_rate`, dùng `("frequency", lambda s: (s > 1).mean())` trong `agg`.
