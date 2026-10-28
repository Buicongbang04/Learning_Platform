---
title: Bảng serving incremental luôn khớp full rebuild
level: advanced
services: []
files:
  - path: starter/refresh.py
    note: 2 TODO
  - path: tests/test_refresh.py
    note: Không sửa
  - path: tests/fixtures/olist_small.sql
    note: Dữ liệu Olist thu nhỏ, không sửa
run:
  - uv run pytest tracks/data-engineer/modules/09-serving-bi/exercises/advanced/02-incremental-serving -q
---

## Mục tiêu

Thiết kế cơ chế refresh incremental cho một bảng pre-computation: chỉ tính lại phần bị ảnh hưởng, nhưng kết quả
phải luôn bằng full rebuild, kể cả khi có cập nhật trạng thái, đơn mới, xoá cứng và timestamp đến trễ. Đây là bài
toán mà materialized view incremental và dbt incremental model giải quyết bên dưới.

## Đề bài

Bảng serving `agg_daily_sales(order_date, customer_state, orders, revenue)` phục vụ dashboard, refresh mỗi 15 phút.
Full rebuild trên dữ liệu thật mất 20 phút, nên phải làm incremental. Hợp đồng với hệ thống nguồn:

- `orders.updated_at` tăng mỗi khi đơn hoặc item của đơn thay đổi.
- Đơn bị xoá cứng được ghi vào `orders_deleted(order_id, order_purchase_timestamp, deleted_at)` (tombstone).
- Chỉ tính đơn không `canceled`/`unavailable`.

Viết trong `starter/refresh.py`:

1. `full_rebuild(con)`: tính lại toàn bộ và đặt watermark.
2. `incremental_refresh(con, lookback=timedelta(0))`: tìm các **ngày bị ảnh hưởng** kể từ `watermark - lookback`, xoá
   và tính lại đúng các ngày đó, cập nhật watermark trong cùng transaction, trả danh sách ngày đã tính lại. Lần chạy
   đầu tiên xử lý như full rebuild.

Ngoài code, viết một đoạn ngắn (docstring đầu tệp hoặc tệp `NOTES.md` của bạn trong `starter/`) trả lời: vì sao
tính lại cả ngày thay vì cộng/trừ delta; watermark nên lấy từ đâu; `lookback` bao nhiêu là hợp lý; điều gì xảy ra
nếu nguồn vi phạm hợp đồng (quên cập nhật `updated_at`); khi nào nên chạy full rebuild định kỳ.

## Tiêu chí đạt

- 7 test pass: lần đầu như full rebuild; không có thay đổi thì không làm gì; cập nhật trạng thái, đơn mới, xoá cứng,
  thay đổi có timestamp đến muộn (với `lookback`) đều cho kết quả bằng full rebuild.
- Ngày không còn đơn nào thì không còn dòng trong bảng.
- Watermark và dữ liệu cập nhật nguyên tử: lỗi giữa chừng thì cả hai giữ nguyên.
- Có phần ghi chú thiết kế trả lời các câu hỏi trên.

## Gợi ý

### Gợi ý 1

Đơn vị tính lại là **partition ngày**, không phải từng đơn. Khi đơn `o2` chuyển sang `canceled`, không thể "trừ" nó
ra khỏi dòng aggregate một cách an toàn (`COUNT DISTINCT` không trừ được); xoá và tính lại cả ngày `2018-08-01` thì
luôn đúng. Lưu danh sách ngày bị ảnh hưởng vào một bảng tạm rồi dùng cho cả `DELETE` lẫn `INSERT … WHERE … IN`.

### Gợi ý 2

Watermark nên là giá trị lớn nhất của `updated_at`/`deleted_at` đã thấy **trong dữ liệu nguồn**, đọc trong cùng
transaction, không phải `now()` của máy chạy job (đồng hồ hai máy có thể lệch). Dùng
`INSERT OR REPLACE INTO _refresh_state …` để ghi watermark. `lookback` cho phép quét lại một khoảng trước watermark
để bắt thay đổi có timestamp nhỏ hơn watermark (replica trễ, clock skew); vì tính lại cả ngày nên quét trùng vẫn an
toàn.
