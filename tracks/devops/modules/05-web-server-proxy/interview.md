# Câu hỏi phỏng vấn: Web server & proxy

## Forward proxy và reverse proxy khác nhau thế nào? Cho một ví dụ bạn cần cả hai trong cùng hệ thống.

Forward proxy đứng phía **client** và đại diện cho client: client biết và cấu hình nó (`HTTPS_PROXY`), server đích thấy IP
của proxy. Reverse proxy đứng phía **server** và đại diện cho server: client không biết nó tồn tại, nó nhận request rồi chuyển
cho backend.

Ví dụ ở Olist Shop: người dùng vào qua load balancer và Nginx (reverse proxy: TLS, định tuyến, cache, rate limit). Worker
gọi API cổng thanh toán qua một forward proxy (Squid hoặc Envoy egress) có allowlist hai tên miền, ghi log mọi kết nối ra, và
đi ra qua NAT có IP cố định để cổng thanh toán đưa vào allowlist. Security group chỉ lọc được theo IP; allowlist theo tên
miền cần forward proxy. Với HTTPS, forward proxy chỉ thấy tên miền trong `CONNECT`/SNI, không thấy nội dung, trừ khi chặn TLS
bằng CA riêng.

## L4 và L7 load balancer khác nhau ra sao? Khi nào bạn chọn L4?

L4 chỉ thấy IP và cổng, chia **kết nối**; L7 đọc HTTP, chia **request**, định tuyến theo host/path/header, thêm header, retry,
cache, và bắt buộc kết thúc TLS. Chọn L4 khi giao thức không phải HTTP (Postgres, Redis, MQTT), khi cần TLS passthrough
(mTLS tới tận backend, cert không được rời khỏi tay bạn), khi cần IP tĩnh và hiệu năng rất cao, hoặc làm lớp ngoài cùng trước
một lớp L7 của chính bạn. Bẫy hay gặp: gRPC/HTTP/2 qua L4 thì một client giữ một kết nối dài, mọi request của nó dính vào một
backend, tải lệch hẳn; cần L7 hiểu HTTP/2 để chia theo request.

## Nginx xử lý hàng chục nghìn kết nối với vài tiến trình bằng cách nào? Reload diễn ra thế nào mà không rớt request?

Master đọc cấu hình, bind cổng, sinh worker (thường một mỗi core). Mỗi worker chạy một event loop không chặn trên epoll:
một tiến trình giữ hàng nghìn socket, chỉ làm việc khi socket có sự kiện, không có tiến trình hay thread riêng cho mỗi kết
nối như Apache prefork. Vì vậy kết nối chậm và keep-alive gần như miễn phí. Điểm yếu: một thao tác chặn (đọc đĩa chậm, module
tồi) chặn mọi kết nối của worker đó.

Reload (`HUP`): master kiểm cấu hình mới, sai thì giữ nguyên và ghi lỗi; đúng thì sinh worker mới, worker cũ thôi nhận kết
nối mới và thoát khi xong việc. Hệ quả cần biết: kết nối dài (WebSocket) giữ worker cũ sống lâu; reload quá thường xuyên làm
tồn nhiều thế hệ worker và tốn RAM; trạng thái trong shared memory zone (cache key, bộ đếm rate limit) giữ qua reload, trạng
thái riêng của worker thì không.

## Sau khi đổi cấu hình, `/api/orders/1` trả 404 dù API có route `/orders/{id}`. Bạn nghi điều gì?

Gần như chắc là quy tắc URI của `proxy_pass`. `location /api/ { proxy_pass http://olist_api; }` (không có phần URI) chuyển
nguyên `/api/orders/1` cho backend. `proxy_pass http://olist_api/;` (có `/`) thay phần khớp `/api/` bằng `/`, backend nhận
`/orders/1`. Biến thể: `location /api` (thiếu `/`) với `proxy_pass .../` cho `//orders/1`; `proxy_pass` có biến thì không có
thay thế nào và phải tự dựng URI.

Cách xác nhận mà không đoán: log của app (path nó thật sự nhận), hoặc dòng `upstream:` trong error log của Nginx, hoặc tạm
log `$upstream_addr` và `$uri`. Và vì sao lọt tới production: `nginx -t` không biết route của app; chỉ smoke test gọi thật mới
bắt được.

## Kể một sự cố proxy bạn đã gặp hoặc có thể gặp, và cách bạn xử lý.

Ví dụ (bài Intermediate 01 và Advanced 01 của module): sau một change chép cấu hình Nginx từ staging, mọi `/api/...` trả 502
ngay lập tức, trang tĩnh vẫn 200, health check của LB xanh, log API trống. Thứ tự xử lý:

1. Khoanh vùng: Nginx sống (trang tĩnh), API sống (container chạy) mà không có request: hỏng ở chặng Nginx → API. 502 trả
   ngay nghĩa là kết nối bị từ chối, không phải treo. Rollback API là vô ích.
2. Error log Nginx: `connect() failed (111: Connection refused)` tới `:8080`, trong khi API production nghe 8000. Sửa cổng.
3. Hết 502, xuất hiện 404 từ API: `proxy_pass` không có URI chuyển nguyên `/api/...`. Sửa thành `proxy_pass http://olist_api/;`.
4. Vì sao không ai bị page: `/healthz` trả thẳng `200` từ Nginx; cảnh báo 5xx chỉ đo lỗi của LB.

Việc sau sự cố: smoke test trong pipeline dựng Nginx với upstream giả và gọi các route chính, cấu hình sinh từ template theo
môi trường, health check đi qua tới API, cảnh báo 5xx theo target, rollout từng máy. Điểm cốt lõi khi kể: đọc log của proxy
trước khi đoán, và mỗi tầng phòng thủ đã không chặn được vì sao.

## Phân biệt 502, 503, 504 và 499 ở Nginx. Mỗi loại bạn kiểm gì đầu tiên?

- **502**: Nginx không nói chuyện được với upstream: kết nối bị từ chối (cổng sai, app chết), app đóng kết nối giữa chừng
  (crash, OOM kill), header response vượt `proxy_buffer_size`. Kiểm error log Nginx (`connect() failed`, `prematurely closed`,
  `too big header`) và log/sự kiện restart của app.
- **503**: Nginx tự từ chối: `no live upstreams` (mọi backend bị `max_fails` rút) hoặc `limit_req`/`limit_conn` với mã mặc
  định. Kiểm error log và cấu hình rate limit.
- **504**: upstream nhận nhưng không trả lời trong `proxy_read_timeout`, hoặc kết nối bị firewall nuốt im lặng tới hết
  `proxy_connect_timeout`. Kiểm route nào, thời gian có đúng bằng timeout không, truy vấn chậm ở DB.
- **499**: client đóng kết nối trước khi Nginx trả lời; thường là client timeout ngắn hơn backend. Không phải lỗi của Nginx
  nhưng là dấu hiệu backend chậm.

Đọc `$upstream_status`, `$upstream_response_time`, `$upstream_addr` trong access log để biết lỗi do Nginx sinh hay do app trả,
và Nginx đã thử những backend nào.

## Nginx đứng sau AWS ALB. Làm sao app biết IP thật của client, và làm sao để header đó không bị giả?

ALB nối IP nó thấy vào `X-Forwarded-For`. Ở Nginx: `set_real_ip_from <CIDR các subnet của ALB>; real_ip_header
X-Forwarded-For; real_ip_recursive on;`. Nginx đọc từ phải sang trái, bỏ các IP thuộc dải tin cậy, lấy IP đầu tiên không tin
cậy làm `$remote_addr`; từ đó log, `limit_req` và `allow/deny` dùng IP thật. Chuyển tiếp bằng `$proxy_add_x_forwarded_for`;
app cũng đọc từ phải sang trái và bỏ đúng số proxy tin cậy, không bao giờ lấy phần tử đầu (client tự đặt được).

Để không bị giả: security group của Nginx chỉ nhận từ security group của ALB, nếu không ai đó gọi thẳng Nginx và tự đặt
`X-Forwarded-For`. `X-Forwarded-Proto` cũng lấy từ ALB vì `$scheme` của Nginx luôn là `http`. Nếu Nginx là tầng ngoài cùng
(không có LB) thì ngược lại: ghi đè `X-Forwarded-For $remote_addr`, không nối.

## Passive và active health check khác nhau thế nào? Nginx open source có gì?

Passive đếm lỗi của request thật: `max_fails` lỗi trong `fail_timeout` thì rút backend trong `fail_timeout`. Rẻ, không tốn
request riêng, nhưng chỉ phát hiện khi có người dùng gặp lỗi, phát hiện backend treo chậm (mỗi lần thử tốn trọn timeout), và
không biết backend "sống nhưng hỏng" (mất DB). Active gọi định kỳ `/readyz` của từng backend kể cả không có traffic, rút
trước khi người dùng thấy.

Nginx open source chỉ có passive; `health_check` là của NGINX Plus. Thực tế active check do LB cloud, Kubernetes readiness
probe, HAProxy hoặc Envoy làm. Hai chi tiết senior: dùng `zone` để mọi worker chia sẻ trạng thái (không thì mỗi worker tự thử
backend chết), và cẩn thận khi health check phụ thuộc DB: DB chết làm mọi node fail cùng lúc, LB có thể fail open hoặc trả
503 cho tất cả.

## Giải thích `limit_req` với `rate=10r/s burst=20` có và không có `nodelay`. Bạn chọn khoá nào để giới hạn?

Leaky bucket: request "rò" ra 10 cái mỗi giây, hàng chờ chứa 20. Không `nodelay`: một đợt 25 request dồn dập thì 1 cái đi
ngay, 20 cái xếp hàng và được thả mỗi 100 ms (cái cuối chờ 2 giây), 4 cái bị từ chối; người dùng thấy chậm. Có `nodelay`: 21
cái được phục vụ ngay, 4 cái bị từ chối, chỗ trong bucket trống lại dần theo tốc độ 10/giây. `nodelay` hợp với API (độ trễ
quan trọng hơn làm mượt), không `nodelay` hợp khi muốn san tải đều lên backend. Đặt `limit_req_status 429`, mặc định 503 làm
người trực và LB tưởng backend chết.

Khoá: theo IP (`$binary_remote_addr`) cho trang công khai, nhưng sau LB mà chưa có `real_ip` thì mọi người chung một bucket,
và nhiều người sau một NAT bị chặn oan. API có đăng nhập thì khoá theo API key hoặc user id. Mỗi máy Nginx đếm riêng: N máy
thì giới hạn thực tế gấp N; cần giới hạn toàn cục thì dùng gateway hoặc WAF. Bật `limit_req_dry_run` để đo trước.

## Bạn cache `/stats/revenue-by-state` ở Nginx. Những gì có thể sai, và bạn phòng thế nào?

- **Trả dữ liệu của người này cho người kia**: response phụ thuộc người dùng hoặc header mà khoá cache không có. Chỉ cache
  endpoint công khai, đưa header quyết định vào `proxy_cache_key` hoặc `Vary`, giữ hành vi mặc định không cache response có
  `Set-Cookie`.
- **Thundering herd** khi bản cache hết hạn: `proxy_cache_lock on`, `proxy_cache_use_stale updating`,
  `proxy_cache_background_update on`.
- **Dữ liệu cũ quá lâu**: thời hạn là quyết định nghiệp vụ (30 giây cho dashboard); làm tươi bằng `proxy_cache_bypass` từ
  nguồn tin cậy sau khi worker tính xong, vì xoá theo khoá chỉ có ở NGINX Plus.
- **Cache lỗi**: chỉ `proxy_cache_valid 200`; dùng `proxy_cache_use_stale error timeout http_5xx` để phục vụ bản cũ khi backend
  chết thay vì cache chính lỗi.
- **Bypass bị lạm dụng**: ai cũng gửi được header bypass thì cache vô dụng và backend bị đánh thẳng; giới hạn theo IP nội bộ.
- **Không quan sát được**: thêm `X-Cache-Status` và `$upstream_cache_status` vào log, theo dõi tỉ lệ HIT.

## Vì sao chọn Nginx thay vì Caddy, HAProxy hay Envoy cho lớp edge của Olist Shop? Khi nào bạn đổi ý?

Nginx cho Olist Shop vì cần một thứ làm được cả bốn việc ở một chỗ: kết thúc TLS, phục vụ SPA tĩnh, reverse proxy có cache và
rate limit theo route, load balancing cơ bản; cấu hình là tệp văn bản review được trong git; team và thị trường tuyển dụng
quen; ingress-nginx và tài liệu vận hành phong phú.

Đổi ý khi ràng buộc đổi:

- **Caddy** khi team rất nhỏ quản lý nhiều tên miền và muốn HTTPS tự động là mặc định, không cần cache hay rate limit phức tạp.
- **HAProxy** khi việc chính là load balancing (cả TCP cho Postgres/Redis), cần active health check, runtime API để rút
  backend lúc deploy, và thống kê chi tiết mà không trả tiền NGINX Plus.
- **Envoy** khi có hàng trăm service, endpoint đổi liên tục, cần cấu hình động qua xDS, retry/circuit breaking/mTLS đồng
  nhất: tức là khi đã có control plane (Istio, Envoy Gateway).
- **Chỉ dùng LB của cloud** khi cache và rate limit đã chuyển lên CDN/WAF: bớt một tầng phải vá và giám sát.

Câu trả lời tốt nêu cả cái giá của Nginx: cần reload để đổi upstream (hoặc `resolve` từ 1.27.3), active health check và
dashboard phải trả phí, nhiều cấu hình sai ngầm (`proxy_pass`, kế thừa `add_header`).

## Thiết kế lớp edge cho Olist Shop chịu Black Friday gấp 10 lần lưu lượng (từ 300 lên 3.000 request/giây).

Từ ngoài vào:

1. **CDN** cho tài nguyên tĩnh của SPA (tên tệp có hash, `immutable`), có thể cả `/stats/revenue-by-state` với thời hạn
   ngắn. Giảm phần lớn request trước khi tới hạ tầng của bạn.
2. **WAF + ALB** hai AZ, cert ACM, health check gọi qua Nginx tới API. WAF chặn bot và rate limit toàn cục.
3. **Nginx** hai máy trở lên (mỗi AZ), `real_ip` từ ALB, cache với `proxy_cache_lock` và `use_stale`, `limit_req` theo IP và
   theo API key với mã 429, timeout lồng nhau (DB 4s < app < Nginx 5s < ALB 60s), keep-alive tới upstream, `zone` cho
   upstream, log JSON có request id.
4. **API** tự scale theo CPU và độ trễ; tính trước: nếu mỗi bản chịu 150 req/s và cache gánh 60% thì cần khoảng 8 bản, scale
   sẵn từ hôm trước vì autoscale phản ứng chậm hơn đợt tăng đột ngột.
5. **Bảo vệ backend khỏi chính mình**: `/jobs/recompute` rate limit chặt, hàng đợi có giới hạn, trang lỗi thân thiện khi quá
   tải thay vì để mọi thứ timeout. Load shedding sớm tốt hơn sập dây chuyền.
6. **Firewall**: chỉ 80/443 từ Internet vào ALB; Nginx chỉ nhận từ ALB; DB/Redis chỉ từ app; egress qua forward proxy.
7. **Chuẩn bị**: load test với lưu lượng thật đã ghi lại, game day tắt một AZ, đóng băng thay đổi cấu hình edge 48 giờ trước,
   dashboard 5xx/p99/cache HIT/429 và người trực.

Nêu đánh đổi: thêm CDN là thêm một tầng cache cần quy tắc làm tươi; cache dài hơn giảm tải nhưng số liệu người bán thấy trễ
hơn; rate limit chặt bảo vệ hệ thống nhưng có thể chặn oan người mua thật sau NAT của nhà mạng di động.

## HSTS là gì, rủi ro khi bật sai là gì?

`Strict-Transport-Security: max-age=31536000` bảo trình duyệt trong một năm chỉ dùng HTTPS với tên miền này và không cho người
dùng bỏ qua lỗi cert, chặn tấn công hạ cấp xuống HTTP (SSL stripping) ở lần truy cập sau. Đặt với `always` để có cả trên
404/5xx; chỉ có nghĩa trên response HTTPS.

Rủi ro: trình duyệt nhớ, bạn không rút lại được trước khi `max-age` hết. `includeSubDomains` làm chết mọi subdomain chỉ có HTTP
(công cụ nội bộ, thiết bị); `preload` đưa tên miền vào danh sách cứng của trình duyệt, gỡ ra mất hàng tháng. Cert hết hạn khi
đã có HSTS thì người dùng không có nút "vẫn tiếp tục". Bật dần: `max-age=300`, rồi một tuần, rồi một năm; chỉ thêm
`includeSubDomains` và `preload` sau khi kiểm kê mọi subdomain.

## Docker publish cổng 8080 trên một máy đã bật `ufw deny incoming`. Cổng có lộ ra Internet không?

Có. Docker thêm rule NAT (DNAT) và rule FORWARD của riêng nó; lưu lượng tới container đi qua chain FORWARD, không qua chain
INPUT mà ufw quản lý, nên `ufw status` nói chặn nhưng cổng vẫn mở. Cách đúng: publish trên `127.0.0.1` (`-p
127.0.0.1:8080:80`) khi chỉ dùng nội bộ hoặc đứng sau Nginx trên cùng máy; đặt rule trong chain `DOCKER-USER` (Docker không
đụng tới chain này); hoặc chặn bằng firewall của cloud ở ngoài máy. Bài học chung: phải kiểm từ **bên ngoài** (quét cổng từ
máy khác), không tin cấu hình của một lớp khi có lớp khác cũng ghi rule.

## Security group và Network ACL khác nhau thế nào? Bạn đặt rule cho Nginx, API và Postgres ra sao?

Security group gắn vào network interface, có trạng thái (kết nối đã cho vào thì chiều về tự đi qua), chỉ có allow, và nguồn
có thể là một security group khác. NACL gắn vào subnet, không trạng thái (phải mở cả dải cổng tạm cho chiều về), có allow và
deny theo thứ tự số. Dùng security group làm lớp chính, NACL cho chặn thô (một dải IP xấu, cô lập subnet).

Rule: `0.0.0.0/0` → ALB cổng 443 (và 80 để chuyển hướng); `sg-alb` → `sg-nginx` cổng 80; `sg-nginx` → `sg-api` 8000;
`sg-api, sg-worker` → `sg-db` 5432 và `sg-redis` 6379; không có rule SSH từ Internet (SSM hoặc bastion từ VPN). Tham chiếu
security group thay vì CIDR để autoscale không làm rule lỗi thời. Chiều ra: worker chỉ tới forward proxy; proxy ra Internet
443. Mỗi rule có lý do ghi trong IaC (module 08), review như code.
