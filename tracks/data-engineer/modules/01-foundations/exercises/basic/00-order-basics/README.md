---
title: Nhập môn Python và SQL qua đơn hàng nhỏ
level: basic
services: []
files:
  - path: starter/basics.py
    note: 3 TODO
  - path: tests/test_basics.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/01-foundations/exercises/basic/00-order-basics -q
---

## Mục tiêu

Đọc dict, viết hàm, bắt lỗi có chủ đích, dùng Decimal cho tiền và giữ cả khách chưa có đơn bằng LEFT JOIN.
Làm bài này trước generator nếu bạn mới học Python/SQL.

## Đề bài

Hoàn thiện ba hàm trong `starter/basics.py`:

1. `parse_price(value)`: nhận chuỗi số thập phân theo dấu chấm, bỏ khoảng trắng hai đầu, trả Decimal.
   Giá phải hữu hạn và không âm; sai dữ liệu thì raise ValueError. Không nhận dấu phẩy tiền tệ.
2. `clean_orders(rows)`: đọc mỗi dict có `order_id` và `price`. ID phải là chuỗi không rỗng sau strip,
   giá qua parse_price. Trả `(valid, rejected)`: valid là list tuple `(order_id, Decimal)`;
   rejected là list tuple `(row_number, reason)`, số dòng bắt đầu 1, reason là chuỗi giải thích không rỗng.
   ID lặp sau khi strip bị từ chối, giữ dòng hợp lệ đầu tiên. Dòng lỗi không giữ chỗ cho ID.
   Không sửa dict đầu vào; không dừng cả lô vì một dòng sai.
3. `customer_totals(con)`: connection SQLite có `customers(customer_id)` và
   `orders(order_id, customer_id, amount_cents)`. Trả list tuple `(customer_id, orders, amount_cents)`
   theo customer_id tăng dần, giữ khách chưa có đơn với số đơn và tổng bằng 0.

`price` ở hai hàm đầu là tiền dạng Decimal; `amount_cents` ở bài SQL là số nguyên đơn vị nhỏ nhất
để SQLite không phải lưu tiền bằng float. 100 cents = 1 đơn vị tiền. Đây là dữ liệu luyện tập rút gọn.

## Tiêu chí đạt

- Không chấp nhận `NaN`, `Infinity`, giá âm hoặc chuỗi rỗng.
- Mỗi dòng lỗi có số dòng và lý do; input không bị sửa.
- Tổng dùng đúng đơn vị, khách chưa có đơn không bị mất hoặc bị đếm là một đơn.
- Test pass; giải thích được vì sao dùng COUNT(order_id) thay COUNT(*).

## Gợi ý

### Gợi ý 1

Decimal có `is_finite()`. Lỗi parse phải được đổi thành ValueError để clean_orders xử lý thống nhất.

### Gợi ý 2

LEFT JOIN giữ mọi khách. COALESCE xử lý tổng NULL; GROUP BY và ORDER BY theo customer_id.
