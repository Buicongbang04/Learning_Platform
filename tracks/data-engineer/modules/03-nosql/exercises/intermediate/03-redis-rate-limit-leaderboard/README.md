---
title: Rate limiter, leaderboard và đếm khách unique bằng Redis
level: intermediate
services: []
files:
  - path: starter/limiter.py
    note: 6 TODO
  - path: tests/test_redis_structures.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/03-nosql/exercises/intermediate/03-redis-rate-limit-leaderboard -q
---

## Mục tiêu

Dùng đúng cấu trúc dữ liệu Redis cho từng bài toán: String + `INCR`/`EXPIRE` cho fixed window, Sorted Set cho
sliding window và leaderboard, `ZUNIONSTORE` để gộp nhiều ngày, HyperLogLog để đếm unique với bộ nhớ cố định.
Hiểu vì sao mỗi thao tác cần nguyên tử (pipeline/`MULTI`). Test chạy offline bằng `fakeredis`.

## Đề bài

Mọi hàm nhận `r` là client Redis (`decode_responses=True`). Thời gian `now` (giây, float) được truyền vào để test
được, thay vì gọi `time.time()` bên trong.

1. `fixed_window_allow(r, client_id, limit, window, now)`: key `rl:fixed:<client_id>:<int(now // window)>`.
   Tăng bộ đếm và đặt TTL `window` giây **trong cùng một pipeline transaction**. Trả `True` nếu số request trong
   cửa sổ (tính cả request này) `<= limit`.
2. `sliding_window_allow(r, client_id, limit, window, now, request_id)`: key `rl:sliding:<client_id>`, sorted set
   với member là `request_id`, score là `now`. Xoá các request có score `<= now - window`, đếm số còn lại; nếu
   `< limit` thì thêm request này, đặt TTL `window` và trả `True`; ngược lại trả `False` và **không** thêm.
3. `record_sale(r, product_id, qty, day)`: cộng `qty` vào điểm của `product_id` trong sorted set
   `top:<day>` (`day` là chuỗi `YYYY-MM-DD`), đặt TTL 8 ngày cho key.
4. `top_sellers(r, day, k)`: trả list `(product_id, qty)` với `qty` là `int`, điểm cao trước, tối đa `k`.
5. `top_sellers_over(r, days, k)`: như trên nhưng gộp nhiều ngày. Dùng `ZUNIONSTORE` vào một key tạm, đọc kết
   quả rồi **xoá key tạm** (sau khi gọi không để lại key mới nào ngoài các key `top:<day>` có sẵn).
6. `track_visit(r, day, visitor_id)` và `count_visitors(r, days)`: dùng HyperLogLog key `uv:<day>`;
   `count_visitors` trả số khách unique (xấp xỉ) trên **hợp** các ngày.

## Tiêu chí đạt

- Fixed window: request thứ `limit + 1` trong cùng cửa sổ bị chặn, sang cửa sổ mới được phép lại; key có TTL.
- Sliding window: không cho vượt `limit` trong mọi khoảng `window` giây liên tiếp, kể cả ở ranh giới mà fixed
  window để lọt; request bị từ chối không chiếm chỗ.
- Leaderboard đúng thứ tự, `qty` là số nguyên, key có TTL.
- `top_sellers_over` gộp đúng điểm nhiều ngày và không để lại key tạm.
- `count_visitors` đếm đúng khách unique khi một khách ghé nhiều ngày.

## Gợi ý

### Gợi ý 1

`pipe = r.pipeline()` (mặc định `transaction=True`, tức `MULTI`/`EXEC`), gọi `pipe.incr(key)`,
`pipe.expire(key, window)`, rồi `count, _ = pipe.execute()`. Sliding window: `zremrangebyscore(key, "-inf", now - window)`,
`zcard`, `zadd(key, {request_id: now})`.

### Gợi ý 2

`zrevrange(key, 0, k - 1, withscores=True)` trả `[(member, score_float)]`. `zunionstore(dest, keys)` cộng điểm
mặc định. Key tạm có thể là `f"tmp:top:{uuid4().hex}"`. HyperLogLog: `pfadd`, `pfcount(*keys)` trả kích thước của
hợp. Trong production, sliding window nên viết bằng Lua script để bước "đếm rồi thêm" là nguyên tử — hãy giải
thích vì sao trong comment.
