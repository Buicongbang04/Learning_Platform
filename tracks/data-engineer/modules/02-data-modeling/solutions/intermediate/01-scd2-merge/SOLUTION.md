# Lời giải: SCD type 2 cho dim_customer

## Thuật toán

1. **Stage**: nạp snapshot vào bảng tạm `stg_customer` để làm việc theo tập bằng SQL.
2. **Đóng** (`UPDATE`): mọi dòng `is_current` mà khách đã đổi thuộc tính *hoặc* không còn trong
   snapshot → `valid_to = as_of`, `is_current = FALSE`.
3. **Chèn** (`INSERT`): mọi khách trong snapshot không có dòng `is_current`. Sau bước 2, tập này
   gồm đúng khách mới + khách vừa bị đóng vì đổi. Khách bị xoá không có trong snapshot nên không
   được chèn lại.
4. Bước 2 và 3 trong **một transaction**: nếu bước 3 lỗi mà bước 2 đã commit, khách sẽ mất dòng hiện hành.

Thứ tự "đóng trước, chèn sau" giúp điều kiện chèn rất đơn giản và tự nhiên idempotent: chạy lại,
không dòng nào đổi nên bước 2 không đóng gì, và mọi khách đều đã có dòng hiện hành nên bước 3 không
chèn gì.

## Các chi tiết dễ sai

- `IS DISTINCT FROM` thay vì `<>`: `NULL <> 'SP'` cho NULL (không phải true) nên thay đổi từ NULL
  sang giá trị sẽ bị bỏ sót.
- Khoảng nửa mở `[valid_from, valid_to)`: dòng cũ kết thúc đúng ngày dòng mới bắt đầu, không ngày
  nào thuộc hai phiên bản. Tra cứu bằng `valid_from <= at AND at < valid_to`, **không** dùng `BETWEEN`.
- `valid_to = 9999-12-31` thay vì NULL: điều kiện tra cứu không cần `OR valid_to IS NULL`.
- Nhiều cột theo dõi: so sánh hash, ví dụ `md5(concat_ws('|', city, state))` lưu sẵn ở cột `row_hash`.
- Khách "sống lại" sau khi bị xoá: bước 3 cấp phiên bản mới với key mới, lịch sử vẫn có khoảng trống.

## Nạp fact

```sql
SELECT o.order_id, c.customer_key
FROM stg_orders o
LEFT JOIN dim_customer c
  ON c.customer_id = o.customer_id
 AND c.valid_from <= o.purchase_date AND o.purchase_date < c.valid_to;
-- customer_key NULL → gán -1 (Unknown) hoặc inferred member
```

## Bản PostgreSQL/MERGE

PostgreSQL 15+ có `MERGE`, nhưng một câu `MERGE` không thể vừa update dòng cũ vừa insert dòng mới
cho **cùng** khoá khớp; mẹo thường dùng là `UNION ALL` nguồn với chính nó (một bản có khoá merge
NULL để buộc nhánh INSERT). Cách hai câu như trên dễ đọc và dễ kiểm hơn. Trong dbt, dùng
`snapshot` với `strategy='check'` hoặc `'timestamp'`.
