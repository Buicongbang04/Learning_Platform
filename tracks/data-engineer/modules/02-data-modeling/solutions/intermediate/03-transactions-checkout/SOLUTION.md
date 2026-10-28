# Lời giải: đặt hàng nguyên tử và chống bán quá

## place_order

1. **Kiểm tra đầu vào trước khi ghi** (`items` rỗng, `qty <= 0`): lỗi nghiệp vụ rẻ nhất là lỗi
   không cần rollback.
2. **Một transaction** bằng `with con:`. Mọi exception bên trong (`OutOfStock`, `IntegrityError` do
   trùng `order_id`, lỗi `CHECK`) đều dẫn tới `ROLLBACK`, nên sản phẩm đã trừ trước đó trong cùng
   đơn được hoàn lại. Đây là chữ **A** (atomicity) trong ACID.
3. **Atomic conditional update** `UPDATE ... SET qty = qty - ? WHERE ... AND qty >= ?` rồi kiểm
   `rowcount`: một câu vừa kiểm tra vừa trừ, không có khe hở giữa "đọc" và "ghi" nên không có lost
   update. `rowcount = 0` gộp luôn hai trường hợp "không đủ hàng" và "không có sản phẩm".
4. `CHECK (qty >= 0)` là lưới an toàn cuối cùng (chữ **C**): kể cả khi code sai, database không
   cho tồn kho âm.

Lưu ý với `sqlite3` của Python (chế độ mặc định): transaction tự mở trước câu DML đầu tiên; `with
con` lo phần commit/rollback. Nếu dùng `autocommit=True`/`isolation_level=None` thì phải tự
`BEGIN`.

## reserve_pg

Cùng ý tưởng trên PostgreSQL. Ở Read Committed (mặc định), khi hai transaction cùng `UPDATE` một
dòng, transaction sau **chờ** transaction trước commit rồi **đánh giá lại điều kiện `WHERE`** trên
phiên bản dòng mới nhất. Vì vậy điều kiện `qty >= 1` luôn được kiểm trên giá trị thật, và đúng 10
trên 20 request thành công.

Mẫu sai và vì sao sai:

```python
qty = conn.execute("SELECT qty FROM ex_stock WHERE product_id = %s", (pid,)).fetchone()[0]
if qty >= 1:
    conn.execute("UPDATE ex_stock SET qty = %s WHERE product_id = %s", (qty - 1, pid))
```

Hai thread cùng đọc `qty = 10`, cùng ghi `9` → bán 2 cái nhưng chỉ trừ 1. Cách sửa khác: `SELECT
... FOR UPDATE` (khoá dòng), optimistic lock bằng cột `version`, hoặc `SERIALIZABLE` + retry khi gặp
lỗi `40001`. Khi một đơn khoá nhiều sản phẩm, sắp xếp `product_id` trước khi update để tránh deadlock.
