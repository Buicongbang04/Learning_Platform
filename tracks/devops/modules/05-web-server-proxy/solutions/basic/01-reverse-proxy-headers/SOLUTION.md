# Lời giải: reverse proxy, header, IP client và request id

Cấu hình đầy đủ ở `nginx.conf` cạnh tệp này. Dưới đây là từng quyết định và vì sao.

## Header tới backend

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Request-ID $req_id;
```

- `Host $host`: mặc định `proxy_pass http://olist_api` gửi `Host: olist_api`. App dựng URL tuyệt đối (link trong email,
  redirect sau đăng nhập), chọn tenant theo tên miền, hay kiểm `ALLOWED_HOSTS` sẽ sai. `$host` lấy từ request line, rồi tới
  header `Host`, rồi tới `server_name`, luôn viết thường, không kèm cổng; cần cổng thì dùng `$http_host` (nhưng đó là giá trị
  client gửi nguyên văn).
- `X-Forwarded-For $remote_addr` **ghi đè** chứ không nối. Nginx ở đây là tầng ngoài cùng, nên `$remote_addr` là IP thật
  duy nhất đáng tin; client gửi `X-Forwarded-For: 6.6.6.6` để giả IP (qua mặt rate limit theo IP, allowlist admin, audit
  log). `$proxy_add_x_forwarded_for` nối IP client vào giá trị client tự gửi (`6.6.6.6, 172.20.0.1`), và app lấy phần tử
  đầu là dính bẫy. Dùng `$proxy_add_x_forwarded_for` khi Nginx đứng **sau** một proxy tin cậy (load balancer, CDN), và lúc
  đó phải bật `real_ip` (`set_real_ip_from <dải IP của LB>; real_ip_header X-Forwarded-For; real_ip_recursive on;`) để
  `$remote_addr` trở thành IP client thật trước khi dùng cho log và rate limit.
- `X-Forwarded-Proto $scheme`: app biết client dùng HTTPS hay không để đặt cookie `Secure`, sinh link `https://`, và không
  redirect vòng tròn sang HTTPS.

Header nào bạn không `proxy_set_header` thì Nginx chuyển nguyên văn: đó là lý do starter để lọt `X-Forwarded-For` và
`X-Real-IP` do client tự đặt. Lưu ý thêm: `proxy_set_header` ở một mức (server, location) thay **toàn bộ** danh sách kế
thừa từ mức trên, nên thêm một `proxy_set_header` trong location là phải lặp lại cả bộ.

## Request id

```nginx
map $http_x_request_id $req_id {
    default $request_id;
    "~^[A-Za-z0-9._-]{1,64}$" $http_x_request_id;
}
```

- Giữ id của client (frontend, mobile app, service gọi vào) để lần theo được một request từ đầu tới cuối, kể cả qua nhiều
  service.
- Không tin mù quáng: id có khoảng trắng, xuống dòng, dấu ngoặc kép hay dài vô hạn là đường cho log injection (giả một dòng
  log), phá parser log, hay làm phình index của hệ thống log. Regex giới hạn bộ ký tự và độ dài; sai dạng thì sinh mới.
- `$request_id` là 16 byte ngẫu nhiên dạng hex (32 ký tự), có sẵn từ Nginx 1.11.
- Log `rid=$req_id` (không phải `$request_id`) để log Nginx và log API cùng một id. API của Olist Shop đã trả lại header
  `X-Request-ID` của request nên không cần `add_header` ở Nginx; nếu muốn client có id cả khi backend chết (502 do Nginx
  sinh), dùng `proxy_hide_header X-Request-ID; add_header X-Request-ID $req_id always;` để không ra hai header trùng.

## Server mặc định và `server_tokens`

```nginx
server {
    listen 80 default_server;
    server_name _;
    return 444;
}
```

Không có khối này, khối đầu tiên nghe cổng 80 thành mặc định, và mọi `Host` lạ (bot quét IP, tên miền khác trỏ nhầm về IP
của bạn, tấn công DNS rebinding) được chuyển thẳng vào API. `444` là mã riêng của Nginx: đóng kết nối không trả gì, rẻ nhất
cho bot. `421 Misdirected Request` là lựa chọn "lịch sự" hơn khi muốn client biết nó gọi nhầm.

`server_tokens off;` bỏ phiên bản khỏi header `Server` và trang lỗi. Nó không làm bạn an toàn hơn khi đang chạy bản có lỗ
hổng, nhưng bớt cho scanner tự động một dữ kiện miễn phí.

## Kiểm bằng tay

```bash
curl -s -H 'Host: shop.olist.test' -H 'X-Forwarded-For: 6.6.6.6' localhost:18085/healthz | jq '{x_forwarded_for, x_real_ip, x_request_id}' &&
docker logs devops-ex-lab-nginx 2>&1 | tail -3
```

Lỗi hay gặp: đặt `proxy_set_header` ở mức `server` rồi thêm một `proxy_set_header` khác trong `location` và mất hết header
ở mức `server`; quên rằng `return` trong server mặc định chạy trước mọi `location`.
