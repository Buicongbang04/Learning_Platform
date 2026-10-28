---
title: Xử lý yêu cầu "right to be forgotten" trên DuckDB
level: intermediate
services: []
files:
  - path: starter/forget.py
    note: 4 TODO
  - path: tests/test_forget.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/10-security-governance/exercises/intermediate/03-right-to-be-forgotten -q
---

## Mục tiêu

Hiện thực một job xoá dữ liệu cá nhân theo GDPR Art. 17 / LGPD trên nhiều bảng: xoá PII, pseudonymize khoá
trong bảng fact để giữ số liệu tổng hợp, crypto-shredding cho dữ liệu đã mã hoá, ghi audit log không chứa PII,
chạy trong transaction và idempotent.

## Đề bài

Database DuckDB có các bảng (test tạo sẵn):

| Bảng | Cột | Xử lý khi xoá |
| --- | --- | --- |
| `customers` | `customer_id`, `customer_unique_id`, `email`, `phone`, `customer_state` | **DELETE** các dòng của người đó |
| `orders` | `order_id`, `customer_id`, `order_status`, `order_purchase_timestamp` | **giữ dòng**, thay `customer_id` bằng pseudonym ngẫu nhiên `anon_<32 hex>` (mỗi `customer_id` cũ một pseudonym) |
| `reviews` | `review_id`, `order_id`, `review_score`, `review_comment_message` | giữ `review_score`, đặt `review_comment_message = NULL` cho các đơn của người đó |
| `user_keys` | `customer_unique_id`, `dek` | **DELETE** (crypto-shredding) |
| `pii_vault` | `customer_unique_id`, `payload` (BLOB mã hoá bằng `dek`) | **không đụng tới**, giả lập backup bất biến |
| `erasure_log` | `request_id`, `subject_hash`, `table_name`, `rows_affected`, `processed_at` | audit log |

Một khách (`customer_unique_id`) có thể có nhiều `customer_id` (mỗi đơn một id, đúng như Olist).
`ensure_tables`, `store_pii`, `read_vault` đã viết sẵn. Hoàn thiện `starter/forget.py`:

1. `subject_hash(customer_unique_id, key)`: HMAC-SHA256 hex đầy đủ. Đây là thứ duy nhất về người dùng được ghi vào log.
2. `find_customer_ids(con, customer_unique_id)`: list `customer_id` của người đó (sắp xếp tăng dần).
3. `erase_customer(con, request_id, customer_unique_id, key)` trả dict
   `{"customers": n, "orders": n, "reviews": n, "user_keys": n}` (số dòng bị tác động):
   - Nếu `request_id` đã có trong `erasure_log`: **không làm gì thêm**, trả lại dict đọc từ log (idempotent).
   - Mọi thay đổi chạy trong **một transaction**; có lỗi thì rollback và raise lại lỗi.
   - Ghi 4 dòng vào `erasure_log` (mỗi bảng một dòng) với `subject_hash`, không ghi `customer_unique_id`,
     `customer_id`, email hay phone.
4. `verify_erased(con, customer_unique_id)` trả list chuỗi mô tả vấn đề còn sót (rỗng nếu sạch): còn dòng
   trong `customers`, còn key trong `user_keys`, hoặc `read_vault` vẫn đọc được.

## Tiêu chí đạt

- Sau khi xoá: không còn PII của người đó, dữ liệu người khác nguyên vẹn, số đơn và điểm review không đổi.
- Payload trong `pii_vault` vẫn còn nhưng không giải mã được.
- Audit log không chứa định danh thô; chạy lại cùng `request_id` không đổi gì.
- Lỗi giữa chừng không để lại trạng thái nửa vời.
- Test pass.

## Gợi ý

### Gợi ý 1

Lấy danh sách `customer_id` **trước** khi xoá `customers`, vì sau đó không còn cách nối từ
`customer_unique_id` sang `orders`. Số dòng tác động: đếm bằng `SELECT count(*)` với cùng điều kiện ngay
trước câu lệnh sửa.

### Gợi ý 2

`con.begin()`, `con.commit()`, `con.rollback()`. Pseudonym ngẫu nhiên: `"anon_" + uuid.uuid4().hex`.
Đừng dùng HMAC của `customer_id` làm pseudonym: ai có key sẽ nối lại được, tức chưa thật sự "quên".
