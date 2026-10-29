---
title: Báo cáo chất lượng dữ liệu tự động cho Olist
level: intermediate
services: []
files:
  - path: starter/quality.ipynb
    note: 5 hàm TODO + phần đọc báo cáo
  - path: tests/test_quality.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run jupyter lab tracks/data-science/modules/09-eda-storytelling/exercises/intermediate/01-olist-quality-report/starter/quality.ipynb
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/intermediate/01-olist-quality-report -q
---

## Mục tiêu

Viết một báo cáo chất lượng dữ liệu chạy lại được cho cả 8 bảng Olist: các kiểm tra có tên, có mức
độ (error / warning / info), có mẫu số rõ ràng, và một hàm quyết định kiểm tra nào chặn pipeline.
Đây là phiên bản "notebook" của thứ bạn sẽ viết bằng dbt tests hay Great Expectations ở công ty.

## Đề bài

Mở `starter/quality.ipynb`:

1. Ba khối xây dựng: `count_duplicated(df, key)` (số dòng có key lặp, đếm mọi bản),
   `count_orphans(child, child_key, parent, parent_key)` (dòng của child có key khác null nhưng không
   có trong parent), `count_order_violations(df, earlier, later) -> (n_failed, n_checked)` (chỉ kiểm
   dòng có cả hai cột, vi phạm khi `earlier > later`).
2. `quality_report(tables) -> DataFrame` cột `check, table, severity, n_failed, n_total, fail_rate`,
   đủ 15 dòng theo đúng thứ tự `CHECKS` trong notebook, theo định nghĩa:

   | check | n_failed | n_total |
   | --- | --- | --- |
   | `orders_pk_duplicated` | dòng `orders` có `order_id` lặp | số dòng `orders` |
   | `delivered_missing_delivery_date` | đơn `delivered` thiếu `order_delivered_customer_date` | số đơn `delivered` |
   | `delivered_missing_approved_at` | đơn `delivered` thiếu `order_approved_at` | số đơn `delivered` |
   | `carrier_after_customer_delivery` | `order_delivered_carrier_date > order_delivered_customer_date` | đơn có cả hai ngày |
   | `approved_before_purchase` | `order_approved_at < order_purchase_timestamp` | đơn có cả hai ngày |
   | `orders_without_items` | dòng `orders` không có `order_id` trong `items` | số dòng `orders` |
   | `items_orphan_order` | dòng `items` có `order_id` không có trong `orders` | số dòng `items` |
   | `items_orphan_product` | dòng `items` có `product_id` không có trong `products` | số dòng `items` |
   | `orders_without_review` | dòng `orders` không có `order_id` trong `reviews` | số dòng `orders` |
   | `review_id_duplicated` | dòng `reviews` có `review_id` lặp | số dòng `reviews` |
   | `products_missing_category` | sản phẩm thiếu `product_category_name` | số sản phẩm |
   | `category_not_translated` | sản phẩm có category nhưng category không có trong `translation` | sản phẩm có category |
   | `customer_zip_not_in_geolocation` | khách có zip không có trong `geolocation` | số dòng `customers` |
   | `payment_items_mismatch` | đơn có tổng `payment_value` lệch tổng `price + freight_value` **quá 1 BRL** | đơn có cả payment lẫn item |
   | `freight_zero` | item có `freight_value == 0` | số dòng `items` |

   `fail_rate = n_failed / n_total` (0 nếu `n_total = 0`). Cột ngày của `orders` đã là datetime;
   zip đọc dưới dạng chuỗi.
3. `blocking_checks(report) -> list[str]`: tên các kiểm tra severity `error` có `n_failed > 0`, giữ
   thứ tự trong báo cáo.
4. Chạy trên Olist thật (cell `explore`) và viết phần "Đọc báo cáo" ở cuối notebook.

## Tiêu chí đạt

- Ba hàm khối xây dựng đúng, kể cả khoá null không bị tính là mồ côi và khoá ghép.
- Báo cáo đúng cấu trúc, đúng thứ tự, đúng `n_failed`/`n_total` cho cả 15 kiểm tra trên bộ dữ liệu
  nhỏ trong test (mỗi kiểm tra có ít nhất một ca lỗi).
- `payment_items_mismatch` không bị nhân dòng khi một đơn có nhiều item và nhiều payment.
- Trên Olist thật: khớp toàn bộ `n_failed` (ví dụ 23 đơn timeline sai, 775 đơn không có item, 1 603
  dòng `review_id` lặp, 13 sản phẩm có category chưa dịch, 249 đơn lệch thanh toán), và kiểm tra chặn
  duy nhất là `carrier_after_customer_delivery`.
- Phần "Đọc báo cáo" phân biệt được lỗi chặn, cảnh báo có hệ quả và thông tin (so với lời giải mẫu).

## Gợi ý

### Gợi ý 1

`df.duplicated(subset=key, keep=False)` cho khoá lặp; `child[key].notna() & ~child[key].isin(parent[pkey])`
cho mồ côi. "Duyệt trước lúc đặt" là `count_order_violations(o, "order_purchase_timestamp",
"order_approved_at")`.

### Gợi ý 2

Với `payment_items_mismatch`: cộng payment theo đơn, cộng `price + freight_value` theo đơn, **rồi
mới** ghép hai Series (`pd.concat(..., axis=1, join="inner")`). Join thẳng hai bảng chi tiết sẽ tạo
2 item × 2 payment = 4 dòng và nhân đôi cả hai tổng.
