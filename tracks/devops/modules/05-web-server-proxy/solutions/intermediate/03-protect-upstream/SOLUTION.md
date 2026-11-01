# Lời giải: rate limit, cache và timeout

Cấu hình đầy đủ ở `nginx.conf` cạnh tệp này.

## Rate limit `/jobs/`

```nginx
limit_req_zone $binary_remote_addr zone=jobs:10m rate=1r/s;

location /jobs/ {
    proxy_pass http://olist_api;
    limit_req zone=jobs burst=5 nodelay;
    limit_req_status 429;
}
```

- `limit_req` là **leaky bucket**: request "rò" ra với tốc độ `rate`; `burst` là kích thước hàng chờ. Không có `nodelay`,
  request trong burst bị **giữ lại** cho tới lượt (người dùng thấy độ trễ tăng, không thấy lỗi); có `nodelay`, chúng được
  phục vụ ngay nhưng vẫn chiếm chỗ trong bucket, chỗ trống lại sau mỗi `1/rate` giây. Vì vậy 15 request dồn dập cho đúng
  `1 + 5 = 6` cái qua.
- Với `rate=1r/s burst=5 nodelay`, 100 request trong 10 giây: khoảng 6 cái đầu qua ngay, sau đó khoảng 1 cái mỗi giây, tổng
  khoảng 15 cái; 85 cái còn lại nhận 429.
- `$binary_remote_addr` (4 byte cho IPv4, 16 cho IPv6) thay vì `$remote_addr` (tới 39 byte chuỗi): zone 10 MB chứa khoảng
  160.000 trạng thái IP. Zone đầy thì Nginx xoá trạng thái cũ, hết chỗ nữa thì trả lỗi cho request mới.
- `429 Too Many Requests` đúng ngữ nghĩa và client biết retry có backoff; `503` mặc định làm người trực tưởng backend chết và
  làm load balancer phía trước tưởng Nginx hỏng.
- Sau load balancer mà chưa cấu hình `real_ip`, `$binary_remote_addr` là IP của LB: **mọi người dùng chung một bucket**, cả
  site bị chặn ở 1 request/giây. Ngược lại, khoá theo IP phạt oan cả công ty sau một NAT; với API có đăng nhập, khoá theo id
  người dùng hoặc API key (`limit_req_zone $http_x_api_key ...`) công bằng hơn. Nhiều tầng cùng lúc là bình thường: WAF/CDN
  chặn flood, Nginx giới hạn theo IP, app giới hạn theo tài khoản.
- `limit_req_dry_run on` (từ 1.17.1) để đo trước khi bật thật: Nginx ghi log những request lẽ ra bị chặn.

## Cache `/stats/revenue-by-state`

```nginx
proxy_cache_path /var/cache/nginx/olist levels=1:2 keys_zone=olist_cache:10m max_size=100m inactive=10m use_temp_path=off;

location = /stats/revenue-by-state {
    proxy_pass http://olist_api;
    proxy_cache olist_cache;
    proxy_cache_valid 200 30s;
    proxy_cache_bypass $http_x_cache_bypass;
    proxy_cache_lock on;
    proxy_cache_use_stale error timeout updating http_502 http_503 http_504;
    add_header X-Cache-Status $upstream_cache_status always;
}
```

- `keys_zone` giữ khoá và metadata trong RAM (1 MB khoảng 8.000 khoá), nội dung nằm trên đĩa, `max_size` giới hạn đĩa,
  `inactive` xoá mục không ai đọc dù còn hạn.
- Khoá cache mặc định là `$scheme$proxy_host$request_uri`: query khác là mục khác. Thêm header vào khoá (ngôn ngữ, tenant)
  bằng `proxy_cache_key` khi response phụ thuộc header đó, nếu không bạn trả bản tiếng Bồ của người này cho người kia.
- `proxy_cache_bypass` bỏ qua bản cache nhưng **vẫn lưu** response mới: đúng nhu cầu "làm tươi" sau khi worker tính lại.
  `proxy_no_cache` thì ngược lại: không lưu. Trong production, giới hạn ai được bypass (chỉ IP nội bộ, hoặc một header bí
  mật), nếu không bất kỳ ai cũng biến cache thành vô dụng.
- `proxy_cache_lock on`: khi nhiều request cùng hỏi một mục đang thiếu, chỉ một request đi tới backend, các request khác chờ.
  `proxy_cache_use_stale updating` trả bản cũ trong lúc một request đang làm tươi; `error timeout http_5xx` giữ trang chạy
  bằng bản cũ khi backend chết. Ba chỉ thị này chống thundering herd đúng lúc cache hết hạn trên endpoint đông người đọc.
- Không cache: response có `Set-Cookie` (Nginx mặc định không cache chúng, đừng tắt hành vi đó bằng `proxy_ignore_headers`),
  response phụ thuộc người dùng (`/orders/{id}`, giỏ hàng, mọi thứ có `Authorization`), response lỗi tạm (5xx). Backend gửi
  `Cache-Control: private` hoặc `no-store` thì Nginx tôn trọng, trừ khi bạn bảo nó bỏ qua.
- 30 giây là quyết định nghiệp vụ: dashboard chấp nhận số trễ tối đa 30 giây; đổi lại backend chỉ nhận khoảng 1 request mỗi 30
  giây cho endpoint này thay vì hàng trăm.

## Timeout

```nginx
proxy_connect_timeout 2s;
proxy_read_timeout 3s;
```

- `proxy_connect_timeout`: thời gian bắt tay TCP tới upstream. Trong cùng data center, kết nối mất dưới 1 ms; 2 giây là đủ
  phát hiện máy treo hoặc gói tin bị firewall nuốt, rồi thử backend khác.
- `proxy_read_timeout`: khoảng chờ **giữa hai lần đọc** từ upstream, không phải tổng thời gian response. Một response stream
  từng mẩu mỗi 2 giây có thể sống mãi. Hết hạn thì 504.
- Giá trị theo SLO của route, không một con số cho tất cả: API đọc 3–5 giây, export báo cáo đặt ở location riêng với timeout
  dài hơn (hoặc chuyển sang job nền trả kết quả sau). Timeout của Nginx phải **dài hơn** timeout của app với DB (để app tự
  trả lỗi có nghĩa) và **ngắn hơn** timeout của LB phía trước (để không có 504 của LB che mất log của Nginx).
- 502 khác 504: 502 là không nói chuyện được (từ chối kết nối, upstream đóng kết nối giữa chừng, header response hỏng); 504
  là không có câu trả lời kịp.
- Timeout không giết request ở backend: backend vẫn chạy truy vấn 6 giây đó. Ở tải cao, client retry sau 504 làm tải nhân
  lên; cần cả timeout ở app và DB (`statement_timeout`).
