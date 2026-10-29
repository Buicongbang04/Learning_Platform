---
title: Nhãn review xấu và chia train/val/test theo thời gian
level: basic
services: []
files:
  - path: starter/labels.py
    note: 3 hàm TODO
  - path: tests/test_labels.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/10-feature-engineering/exercises/basic/01-olist-label-split -q
---

## Mục tiêu

Dựng đúng "khung" cho mọi bài ML trên Olist của track: một dòng mỗi đơn, nhãn review xấu, và cách
chia theo thời gian mà các module sau dùng y hệt. Sai ở bước này thì mọi con số phía sau đều sai.

## Đề bài

Trong `starter/labels.py`:

1. `label_orders(orders, reviews)`: giữ đơn giao xong (`order_status == "delivered"` và có
   `order_delivered_customer_date`), ghép với review **trả lời sau cùng** của đơn (một đơn có thể
   có nhiều review), thêm `review_score` và `bad_review = 1` khi `review_score <= 2`. Chỉ giữ đơn
   có review. Không sửa DataFrame đầu vào.
2. `time_split(df, date_col)`: train là đơn mua trước 2018-01-01, val từ 2018-01-01 tới trước
   2018-04-01, test từ 2018-04-01 tới hết 2018-08-31. Bỏ đơn mua từ 2018-09-01. Giữ index gốc.
3. `split_summary(splits)`: bảng index `train`, `val`, `test` với cột `n`, `bad_rate`,
   `start`, `end`.

Sau khi xong, chạy trên Olist thật và nhìn bảng tóm tắt: tỉ lệ review xấu ở ba giai đoạn có giống
nhau không? Điều đó nói gì về việc dùng validation để chọn ngưỡng quyết định?

## Tiêu chí đạt

- Loại đơn huỷ, đơn chưa có ngày giao; một đơn một dòng; review mới nhất được dùng.
- Mốc chia đúng tới từng giây ở cả ba ranh giới.
- Trên Olist thật: 95 824 đơn, tỉ lệ review xấu 12.8%; ba phần có 43 362 / 20 468 / 31 994 đơn,
  tỉ lệ review xấu 12.1% / 18.0% / 10.4%.

## Gợi ý

### Gợi ý 1

`reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")`, rồi
`merge(..., how="inner")`.

### Gợi ý 2

So sánh `Series` datetime với chuỗi `"2018-01-01"` hoạt động, nhưng dùng hằng `pd.Timestamp` ở
đầu tệp cho rõ. Ranh giới trái đóng, phải mở: `(t >= TRAIN_END) & (t < VAL_END)`.
