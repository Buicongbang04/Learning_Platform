---
title: Label delay và monitoring trên cohort chưa chín
level: basic
services: []
files:
  - path: starter/labels.py
    note: 3 hàm TODO
  - path: tests/test_labels.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/15-ml-system-design/exercises/basic/03-label-delay -q
---

## Mục tiêu

Biết **khi nào** nhãn của một dự đoán có mặt, và vì sao metric tính trên nhãn "đã có" của cohort gần
đây bị lệch. Đây là việc phải làm trước khi dựng dashboard monitoring cho bất kỳ model nào có nhãn về
chậm.

## Đề bài

Nhãn "giao trễ" (định nghĩa chung: đơn `delivered` có `order_delivered_customer_date`, trễ khi ngày giao
thực tế > ngày hẹn, so nguyên timestamp) được **biết** ở hai thời điểm khác nhau:

- Đơn đúng hẹn: biết khi đơn tới tay khách (`order_delivered_customer_date`).
- Đơn trễ: biết ngay khi qua ngày hẹn mà chưa giao (`order_estimated_delivery_date`).

Trong `starter/labels.py`:

1. `late_label_known_at(orders) -> pd.DataFrame`: chỉ đơn giao xong; index `order_id`, cột
   `purchase_ts`, `late` (bool), `known_at`.
2. `observed_late_rate(labels, as_of) -> (share_known, observed_rate)`: trên **mọi** dòng của `labels`
   (thường là một cohort đơn mua), tỉ lệ đơn đã có nhãn tại `as_of` (`known_at <= as_of`) và tỉ lệ trễ
   tính chỉ trên các đơn đã có nhãn (`nan` nếu chưa đơn nào có nhãn).
3. `maturity_days(labels, coverage=0.95) -> float`: số ngày d nhỏ nhất (theo quantile) sao cho
   `coverage` phần đơn có nhãn trong vòng d ngày kể từ lúc mua.

Chạy trên Olist thật: nhìn cohort đơn mua tháng 02/2018 ở các ngày 2018-03-01, 03-15, 03-29.

## Tiêu chí đạt

- Thời điểm biết nhãn đúng cho cả đơn trễ và đúng hẹn; đơn chưa giao xong bị loại.
- Tỉ lệ đã có nhãn và tỉ lệ trễ nhìn thấy đúng trên ví dụ tính tay; `nan` khi chưa có nhãn nào.
- Trên Olist thật: 96 470 đơn giao xong; cohort 02/2018 có tỉ lệ trễ thật khoảng 16.0% nhưng nhìn tại
  2018-03-01 chỉ khoảng 1.4%; 95% nhãn có trong khoảng 25 ngày sau khi mua.

## Gợi ý

### Gợi ý 1

`delivered.where(~late, estimated)` chọn giữa hai cột theo từng dòng.

### Gợi ý 2

`maturity_days`: `((known_at - purchase_ts) / pd.Timedelta(days=1)).quantile(coverage)`.
