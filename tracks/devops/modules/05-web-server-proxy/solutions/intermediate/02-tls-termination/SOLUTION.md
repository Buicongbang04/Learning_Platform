# Lời giải: kết thúc TLS ở Nginx

Cấu hình đầy đủ ở `nginx.conf` cạnh tệp này.

## Cổng 80: ACME và chuyển hướng

```nginx
location ^~ /.well-known/acme-challenge/ {
    root /var/www/acme;
    default_type text/plain;
}

location / {
    return 308 https://$host$request_uri;
}
```

- `^~` làm location tiền tố này thắng mọi location regex, nên không regex nào (ví dụ chặn đường dẫn bắt đầu bằng dấu chấm)
  nuốt mất đường ACME.
- ACME HTTP-01 luôn bắt đầu bằng HTTP cổng 80. Let's Encrypt có đi theo redirect sang HTTPS (và cố ý không kiểm cert ở chặng
  đó), nhưng khi đó việc gia hạn phụ thuộc khối 443 còn chạy đúng: một lỗi cấu hình TLS, `ssl_reject_handshake` với tên mới
  chưa khai báo, hay một CA ACME khác không theo redirect là bạn không xin được cert để sửa chính lỗi đó. Phục vụ ACME thẳng
  trên HTTP bỏ phụ thuộc vòng này.
- `301` cho phép client đổi `POST` thành `GET` khi đi theo redirect (trình duyệt làm vậy), nên một form hay client API cũ
  `POST` qua HTTP mất body. `308` giữ nguyên method và body. Với API, chọn `308`; với trang web thuần đọc, `301` vẫn ổn.
- `$host$request_uri` giữ path và query. Dùng `$server_name` thay `$host` khi muốn redirect luôn về tên chính tắc.

## Cổng 443

```nginx
server {
    listen 443 ssl default_server;
    server_name _;
    ssl_reject_handshake on;
}

server {
    listen 443 ssl;
    http2 on;
    server_name shop.olist.test;
    ssl_certificate /etc/nginx/tls/fullchain.pem;
    ssl_certificate_key /etc/nginx/tls/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1h;
    ssl_session_tickets off;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    ...
}
```

- `ssl_reject_handshake on` (từ 1.19.4) cắt bắt tay khi SNI không khớp server nào: không lộ cert (và danh sách tên miền
  trong SAN) cho scanner quét IP, không trả nhầm cert của site khác. Cái giá: client không gửi SNI (thiết bị rất cũ, một số
  health check) bị từ chối; phục vụ chúng bằng một IP hoặc cổng riêng có server mặc định trả đúng cert.
- `ssl_certificate` phải là **fullchain** (cert lá + intermediate), như bạn đã thấy ở module 04.
- TLS 1.0 và 1.1 đã bị RFC 8996 loại bỏ. Bộ cipher mặc định của Nginx với OpenSSL 3 đã ổn; chỉ cấu hình `ssl_ciphers`
  khi có yêu cầu tuân thủ cụ thể (PCI DSS, cấu hình "intermediate" của Mozilla).
- `ssl_session_cache` giúp client kết nối lại bỏ qua bắt tay đầy đủ. `ssl_session_tickets off` vì Nginx không tự xoay khoá
  ticket: một khoá sống mãi phá forward secrecy của TLS 1.2.
- `http2 on;` từ 1.25.1 (trước đó là `listen 443 ssl http2;`, giờ đã cũ). HTTP/2 chỉ được thương lượng qua ALPN trong TLS.
- Header `X-Forwarded-Proto $scheme` giờ là `https`, nên app đặt cookie `Secure` và sinh link `https://`.

## HSTS

- `always` là bắt buộc: không có nó, `add_header` bỏ qua 404, 5xx, đúng những response trình duyệt hay gặp đầu tiên khi có
  sự cố.
- `max-age=31536000`: trình duyệt nhớ một năm, từ chối HTTP và từ chối bỏ qua lỗi cert. Bật dần: `max-age=300` vài ngày,
  rồi một tuần, rồi một năm, vì một khi trình duyệt đã nhớ, bạn không rút lại được trước khi `max-age` hết.
- `includeSubDomains` áp cho mọi subdomain: một `intranet.olist.test` chỉ có HTTP sẽ chết với mọi người đã ghé trang chính.
  `preload` đưa tên miền vào danh sách cứng trong trình duyệt; rút ra mất hàng tháng. Chỉ bật khi chắc mọi subdomain có
  HTTPS.
- Bẫy kế thừa: một `add_header` bất kỳ trong `location` làm mọi `add_header` ở mức `server` không áp vào location đó nữa
  (ví dụ thêm `add_header Cache-Control ...` cho tệp tĩnh là mất HSTS ở đó). Nginx 1.29.3 có `add_header_inherit merge`
  để gộp; với bản cũ, lặp lại header hoặc dùng `include` một tệp chung.

## Vận hành cert trong production

- Certbot hoặc lego chạy theo lịch, ghi cert vào thư mục, rồi `nginx -t && nginx -s reload` (reload không làm rớt kết nối).
  Theo dõi ngày hết hạn **và** xác minh chuỗi bằng client nghiêm ngặt (bài postmortem của module 04).
- Khoá riêng quyền `600`, thuộc root; worker của Nginx không cần đọc khoá, chỉ master đọc lúc nạp cấu hình.
- Cert ngắn hạn: CA/Browser Forum đã thông qua lộ trình hạ thời hạn tối đa xuống 47 ngày vào 2029; tự động hoá gia hạn là bắt
  buộc, không phải tuỳ chọn.
