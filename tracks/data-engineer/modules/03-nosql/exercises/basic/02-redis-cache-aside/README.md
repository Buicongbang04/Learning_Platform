---
title: Cache-aside cho trang sản phẩm bằng Redis
level: basic
services: []
files:
  - path: starter/cache.py
    note: 4 TODO
  - path: tests/test_cache_aside.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/basic/02-redis-cache-aside -q
---

## Mục tiêu

Cài đặt pattern cache-aside đúng cách: đọc cache trước, miss thì nạp từ nguồn và ghi cache có TTL, cập nhật
nguồn thì xoá cache, và cache cả kết quả "không tồn tại" (negative caching) để chống cache penetration. Test chạy
offline bằng `fakeredis`.

## Đề bài

Lớp `ProductCache` trong `starter/cache.py` bọc một client Redis (`decode_responses=True`) và một hàm
`loader(product_id) -> dict | None` đọc sản phẩm từ database chính (MongoDB, PostgreSQL... — trong test là một
hàm giả có đếm số lần gọi).

Hoàn thiện:

1. `key(product_id)`: trả về `"product:<product_id>"`.
2. `get(product_id)`:
   - Có trong cache → trả dict đã giải mã JSON, **không** gọi `loader`.
   - Không có → gọi `loader`. Nếu có sản phẩm, lưu JSON với TTL `self.ttl` giây. Nếu `loader` trả `None`, lưu
     chuỗi `"__none__"` với TTL `self.negative_ttl` và trả `None`. Lần gọi sau trong TTL cũng trả `None` mà không
     gọi `loader`.
3. `invalidate(product_id)`: xoá key, trả về `True` nếu có key bị xoá.
4. `update(product_id, fields, saver)`: gọi `saver(product_id, fields)` để ghi vào database chính **trước**, rồi
   xoá cache. Không ghi giá trị mới vào cache ở đây (lần `get` kế tiếp sẽ nạp lại).

## Tiêu chí đạt

- Hai lần `get` liên tiếp chỉ gọi `loader` một lần, và lần hai trả cùng dữ liệu.
- Key có TTL dương, không vượt `ttl`.
- Sản phẩm không tồn tại được negative-cache với TTL `negative_ttl`, `loader` chỉ bị gọi một lần.
- Sau `update`, database đã đổi và `get` trả dữ liệu mới (loader được gọi lại).
- Nếu `saver` ném lỗi thì cache **không** bị xoá (thứ tự: ghi DB trước, xoá cache sau).

## Gợi ý

### Gợi ý 1

`self.r.get(key)` trả `None` khi miss. `self.r.set(key, json.dumps(doc), ex=self.ttl)` ghi kèm TTL.
`self.r.delete(key)` trả số key đã xoá.

### Gợi ý 2

Phân biệt "cache có giá trị `__none__`" với "cache miss (`None`)". Vì sao xoá cache thay vì ghi giá trị mới
khi update? Hãy nghĩ tới hai request ghi đồng thời và thứ tự chúng tới Redis.
