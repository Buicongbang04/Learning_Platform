# Lời giải: chọn web server, proxy và load balancer

| Câu | Đáp án | Ràng buộc quyết định |
| --- | --- | --- |
| `forward-vs-reverse` | b. Forward proxy cho egress | Kiểm soát kết nối **đi ra** của client nội bộ |
| `l4-vs-l7` | b. HAProxy chế độ TCP | Giao thức Postgres không phải HTTP; cần health check biết vai trò node |
| `small-team-auto-tls` | a. Caddy | HTTPS tự động là mặc định, team nhỏ không muốn vận hành certbot |
| `java-war` | b. Tomcat/Jetty, Nginx phía trước | `.war` cần servlet container |
| `shared-hosting-htaccess` | c. Apache httpd | `.htaccess` cho phép cấu hình theo thư mục không cần reload |
| `mesh-dynamic-config` | a. Envoy | Cấu hình động qua xDS, retry, circuit breaking, mTLS |
| `error-502-vs-504` | b. Upstream không trả lời kịp | 504 là timeout đọc; đúng 60 giây là `proxy_read_timeout` mặc định |
| `passive-vs-active` | b. Chỉ biết khi request thật lỗi | Nginx open source không có active health check |
| `who-terminates-tls` | a, c, d | Tin header đúng nguồn và chặn đường vòng qua LB |

## Giải thích từng câu

### `forward-vs-reverse`: forward proxy

Forward proxy đứng phía client: worker cấu hình `HTTPS_PROXY=http://egress-proxy:3128`, proxy kiểm tên miền đích trong
`CONNECT` (hoặc SNI) với allowlist, ghi log, và cho mọi kết nối ra đi từ một IP cố định (đối tác hay yêu cầu allowlist IP
nguồn). Reverse proxy (a) đứng phía server, nhận kết nối **đi vào**, không chặn được worker gọi ra. Load balancer (c) và CDN
(d) cũng là thành phần phía server của người khác.

### `l4-vs-l7`: HAProxy chế độ TCP

Postgres nói giao thức riêng trên TCP, nên cần L4. HAProxy `mode tcp` có health check tuỳ biến (`option httpchk` gọi một
agent như Patroni REST API trả 200 chỉ trên primary) để tách backend ghi và backend đọc; PgBouncer hay pgcat là lựa chọn
khác khi cần thêm connection pooling. Nginx cũng làm L4 được nhưng bằng khối `stream`, không phải khối `http` như phương án
a, và Nginx open source không có active health check. Caddy (c) là web server HTTP. DNS round robin (d) không biết node nào
là primary và không rút node chết.

### `small-team-auto-tls`: Caddy

Caddy tự xin cert ACME, tự gia hạn, tự chuyển HTTP sang HTTPS, cấu hình kiểu `shop.example.com { reverse_proxy api:8000 }`.
Với team rất nhỏ, đó là ít việc vận hành nhất. Nginx với certbot cũng tốt nhưng là hai thứ phải chạy. Apache (b) với cert
mua theo năm là việc tay hằng năm, đúng loại việc sẽ có ngày quên. Tomcat (c) và IIS (d) không hợp cho landing page trên
Linux.

### `java-war`: servlet container

Tệp `.war` là ứng dụng Java theo chuẩn Jakarta Servlet; cần một servlet container (Tomcat, Jetty, WildFly) chạy JVM. Nginx
không chạy Java; thực tế đặt Nginx phía trước để kết thúc TLS, phục vụ tệp tĩnh và giới hạn request. Ứng dụng Spring Boot
mới thường nhúng sẵn Tomcat trong jar nên không cần cài Tomcat riêng.

### `shared-hosting-htaccess`: Apache httpd

`.htaccess` được Apache đọc theo thư mục ở mỗi request, nên mỗi khách tự sửa rewrite, auth, redirect mà không cần quyền
reload server. Cái giá là hiệu năng (đọc tệp ở mọi request trên mọi thư mục cha). Nginx cố ý không có cơ chế này: cấu hình
tập trung, nạp một lần. Đó là lý do Apache vẫn thống trị hosting chia sẻ (cPanel) dù Nginx nhanh hơn với tệp tĩnh.

### `mesh-dynamic-config`: Envoy

Envoy sinh ra để làm proxy cho microservice: nhận cấu hình động qua API xDS (listener, route, cluster, endpoint) từ control
plane mà không reload, có retry, timeout, circuit breaking, outlier detection, mTLS, và observability chi tiết. Istio, AWS
App Mesh, Gloo, Contour, Envoy Gateway đều dùng Envoy. Nginx open source cần reload để đổi upstream (NGINX Plus có API).

### `error-502-vs-504`: upstream không trả lời kịp

`504 Gateway Timeout` là Nginx đã gửi request nhưng không nhận được response trong `proxy_read_timeout` (mặc định 60 giây,
đúng con số trong đề). Chỉ một route bị nghĩa là backend chạy, nhưng truy vấn của route đó chậm (thiếu index, khoá bảng).
Không kết nối được (a) cho `502` ngay lập tức (hoặc `504` sau `proxy_connect_timeout` nếu gói tin bị firewall nuốt). Body
quá lớn (c) là `413`. Rate limit (d) là `503` mặc định hoặc mã bạn đặt bằng `limit_req_status`.

### `passive-vs-active`: chỉ biết khi request thật lỗi

`max_fails`/`fail_timeout` là passive: Nginx chỉ đếm lỗi của request thật. Không có traffic thì không có lỗi để đếm; người
dùng đầu tiên buổi sáng gặp lỗi (hoặc timeout dài nếu backend treo), dù sau đó Nginx thử backend khác. Active health check
(`health_check`) chỉ có ở NGINX Plus. Nginx không đọc Docker API (c). `max_fails=3` (d) là ngưỡng đếm lỗi trước khi rút
backend, không phải số lần thử lại.

### `who-terminates-tls`: a, c, d

- (a) Đúng: sau LB, `$remote_addr` là IP của LB. `real_ip` thay nó bằng IP client lấy từ header, **chỉ** khi request đến từ
  dải tin cậy. `real_ip_recursive on` bỏ qua các IP tin cậy ở cuối chuỗi.
- (b) Sai: client đặt được mọi header, kể cả `X-Forwarded-For`. LB chỉ nối thêm vào giá trị client gửi.
- (c) Đúng: Nginx nhận HTTP từ LB nên `$scheme` luôn là `http`; truyền nguyên `X-Forwarded-Proto` của LB (hoặc `map` từ
  nó) để app biết client dùng HTTPS.
- (d) Đúng: nếu ai đó gọi thẳng cổng của Nginx, bỏ qua LB, họ tự đặt được mọi header "tin cậy". Security group của Nginx
  chỉ nhận từ security group của LB.
- (e) Sai: HSTS là header cho trình duyệt, vẫn cần (đặt ở LB hoặc ở Nginx, một chỗ). Trình duyệt không biết và không quan
  tâm TLS kết thúc ở đâu.
