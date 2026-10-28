# Lời giải: rate limiter, leaderboard và HyperLogLog

## Fixed window

`INCR` trả về giá trị sau khi tăng nên một lệnh vừa đếm vừa ghi, nguyên tử. `EXPIRE` đặt cùng pipeline
transaction để không bao giờ có key đếm mà không có TTL (rò bộ nhớ). Gọi `EXPIRE` mỗi lần cũng không sao vì khoá
gắn với số thứ tự cửa sổ, cửa sổ sau là key khác.

Nhược điểm được test `test_fixed_window_boundary_leak` chỉ ra: 3 request cuối cửa sổ và 3 request đầu cửa sổ sau
đều lọt, tức 6 request trong 2 giây dù giới hạn là 3/phút.

## Sliding window log

Sorted set giữ timestamp mọi request còn trong cửa sổ. Mỗi lần: xoá request cũ (`ZREMRANGEBYSCORE`), đếm
(`ZCARD`), nếu còn chỗ thì `ZADD`. Chính xác tuyệt đối nhưng tốn bộ nhớ O(limit) mỗi client. Request bị từ chối
không được thêm vào (nếu thêm, client spam sẽ bị khoá mãi).

**Race condition**: bước đếm và bước thêm là hai round-trip; hai request đồng thời có thể cùng thấy `count = 2` và
cùng được thêm, vượt limit. Cách đúng là Lua script:

```lua
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1] - ARGV[2])
if redis.call('ZCARD', KEYS[1]) < tonumber(ARGV[3]) then
  redis.call('ZADD', KEYS[1], ARGV[1], ARGV[4])
  redis.call('EXPIRE', KEYS[1], ARGV[2])
  return 1
end
return 0
```

(`fakeredis` cần thư viện `lupa` để chạy Lua nên bài này dùng pipeline.) Các thay thế khác: sliding window counter
(nội suy giữa hai fixed window, O(1) bộ nhớ) hoặc token bucket.

## Leaderboard

`ZINCRBY` cộng điểm nguyên tử, `ZREVRANGE ... WITHSCORES` lấy top-k với O(log N + k). Điểm trong sorted set là
float nên đổi sang `int`. Một key cho mỗi ngày + TTL giúp dữ liệu tự dọn. Gộp nhiều ngày bằng `ZUNIONSTORE` (cộng
điểm), đọc, rồi xoá key tạm — tất cả trong một transaction. Trong Redis Cluster, các key phải cùng hash slot
(dùng hash tag như `top:{shop}:2018-05-01`), nếu không `ZUNIONSTORE` báo `CROSSSLOT`.

## HyperLogLog

Đếm khách unique chính xác cần lưu mọi id (Set: hàng chục MB cho vài triệu khách). HyperLogLog chỉ dùng tối đa
12 KB mỗi key với sai số chuẩn khoảng 0,81%, và `PFCOUNT k1 k2 ...` đếm trên hợp nhiều ngày mà không cần
lưu lại id. Với tập nhỏ như trong test, Redis dùng biểu diễn sparse nên kết quả gần như chính xác. Đây cũng là
thuật toán đứng sau `APPROX_COUNT_DISTINCT` của BigQuery/Snowflake/DuckDB.
