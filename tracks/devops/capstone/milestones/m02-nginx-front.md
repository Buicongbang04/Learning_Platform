# M02: Nginx phía trước: reverse proxy, TLS, rate limit

## Mục tiêu

Sau M01, API Olist Shop nghe trực tiếp ở cổng `28000` bằng HTTP thường: không mã hoá, ai gọi `POST /jobs/recompute`
bao nhiêu lần cũng được (mỗi lần là một job tính lại doanh thu trên toàn bảng), và không có chỗ nào gắn một request id
chung cho cả lớp edge lẫn app. Milestone này đặt Nginx phía trước API, đúng vai trò nó giữ trong mọi milestone sau
(compose ở M03, Ingress ở M06):

- Kết thúc TLS bằng cert tự ký do script của bạn tạo, chuyển mọi request HTTP sang HTTPS.
- Reverse proxy tới API với đủ header để app biết client thật và scheme gốc.
- Rate limit riêng cho `/jobs/`, endpoint đắt nhất, mà không chặn nhầm các đường dẫn đọc.
- Một `X-Request-ID` đi suốt client → Nginx → API → log của cả hai, để lần một request khi có sự cố.

Đây là bài tích hợp sau [module 05 Web server & proxy](../../modules/05-web-server-proxy/README.md): mục 2 (header tới
backend), mục 4 (TLS termination) và mục 5 (rate limit kiểu leaky bucket). Module dạy từng mảnh trên một backend giả;
ở đây bạn ghép chúng thành một cấu hình cho đúng service mình vận hành.

## Việc cần làm

Bạn viết hai tệp trong `capstone/project/nginx/`. Test dựng mọi thứ bằng `testkit.DockerLab`: một container
`python:3.12.16-alpine3.24` chạy API giả cùng route với Olist Shop (tên mạng `api`, cổng `8000`, ghi một dòng JSON có
`request_id` cho mỗi request), và một container `nginx:1.30.6-alpine` dùng cấu hình của bạn. Container có tên
`devops-ex-...`, ghim CPU theo `DEVOPS_CPUSET`, bị dọn khi test xong. Test gửi request với `Host: olist-shop.local` và
SNI `olist-shop.local`.

Mọi quy tắc dưới đây đều được chấm. Không có quy tắc chấm nào nằm ngoài tệp này.

### 1. `nginx/gen-cert.sh`

```text
gen-cert.sh <OUT_DIR>
```

- Đúng một tham số, khác rỗng. Sai: exit 2, stderr bắt đầu bằng `Usage:`.
- Tạo `OUT_DIR` nếu chưa có, ghi `OUT_DIR/olist-shop.crt` và `OUT_DIR/olist-shop.key`, cả hai là PEM, key **không**
  đặt mật khẩu (Nginx phải đọc được khi khởi động mà không cần người gõ).
- Key chỉ chủ sở hữu đọc được: quyền không có bit nào cho group hay other (`600`).
- Cert **tự ký**: issuer trùng subject và chữ ký kiểm được bằng chính public key của cert. Key khớp cert.
- `subjectAltName` có ít nhất `DNS:olist-shop.local`, `DNS:localhost`, `IP:127.0.0.1`. Client hiện đại bỏ qua CN, chỉ
  đọc SAN.
- Đang hiệu lực, còn ít nhất 30 ngày, tổng thời hạn không quá 398 ngày (giới hạn trình duyệt áp cho cert công khai; tập
  thói quen cert ngắn hạn ngay từ local).
- Không in private key ra stdout hay stderr.
- **Idempotent:** cả hai tệp đã có, cert còn hơn 30 ngày và khớp key thì giữ nguyên **từng byte** của cả hai, exit 0.
  Ngược lại (cert hết hạn hoặc còn dưới 30 ngày, key không khớp cert, thiếu một trong hai tệp) thì tạo lại cả hai.
- Qua `shellcheck -S style` không cảnh báo. Test cần `openssl` ≥ 1.1.1 (cho `-addext`) và chạy script trong sandbox
  bubblewrap như M01.

Thư mục cert thật của bạn (`capstone/project/nginx/tls/`) đã nằm trong `.gitignore` của `project/`: không bao giờ
commit private key, kể cả key tự ký.

### 2. `nginx/olist-shop.conf`

Test mount tệp này **chỉ đọc** vào `/etc/nginx/conf.d/default.conf` của `nginx:1.30.6-alpine`. Tệp đó được `include`
trong khối `http` của `nginx.conf` mặc định, nên bạn viết các directive cấp `http` (`upstream`, `map`, `log_format`,
`limit_req_zone`) và các khối `server`, **không** viết `http {}` hay `events {}`. Cert được mount ở
`/etc/nginx/tls/olist-shop.crt` và `/etc/nginx/tls/olist-shop.key`. Test dùng một cert tự ký do test tạo ở đúng đường
dẫn đó, nên phần Nginx được chấm độc lập với `gen-cert.sh`.

| Hạng mục | Quy tắc được chấm |
| --- | --- |
| Cú pháp | `nginx -t` pass; container khởi động và trả lời ở cổng 80. |
| Upstream | API ở `api:8000` (tên service `api` trong compose của sample-app, cũng là tên mạng của API giả trong test). |
| HTTP → HTTPS | Cổng 80: mọi method và đường dẫn trả **301 hoặc 308** với `Location` đúng bằng `https://<Host>/<đường dẫn gốc kèm query>`, không kèm cổng. Test thử `GET /orders/abc?utm_source=email&x=1`, `GET /`, `POST /jobs/recompute`; ví dụ `https://olist-shop.local/orders/abc?utm_source=email&x=1`. |
| TLS | Cổng 443 bắt tay TLS với SNI `olist-shop.local` và trả đúng cert ở `/etc/nginx/tls/olist-shop.crt`. |
| Reverse proxy | `GET https://olist-shop.local/orders/abc?x=1` trả 200 từ API; API nhận đúng `/orders/abc?x=1`, `Host: olist-shop.local`, `X-Forwarded-Proto: https`, và có `X-Real-IP`, `X-Forwarded-For` (IP client). |
| Request id có sẵn | Client gửi `X-Request-ID: <id>`: API nhận đúng `<id>`, không bị thay. |
| Request id sinh mới | Client không gửi: Nginx sinh id bằng `$request_id` (32 ký tự hex) và gửi xuống API trong `X-Request-ID`. |
| Request id trả về | Response có **đúng một** header `X-Request-ID`, bằng id API đã nhận. API đã tự trả lại header này, nên đừng `add_header` thêm một bản nữa. |
| Request id trong log | id đó có trong log của API (API tự ghi) **và** trong access log của Nginx (bạn tự định nghĩa `log_format` có id; image ghi access log ra stdout của container). |
| Rate limit `/jobs/` | `limit_req` cho `location /jobs/` với `rate` tối đa `10r/s`, `burst` từ 2 tới 20, `nodelay`, và `limit_req_status 429`. Test gửi 60 `POST /jobs/recompute` liên tiếp trên một kết nối keep-alive: 3 request đầu phải 202, phải có ít nhất một 429, và chỉ có 202 hoặc 429 (mặc định Nginx trả 503, là sai: 503 nghĩa là server hỏng, 429 nghĩa là client gửi quá nhanh và nên thử lại sau). |
| Không chặn nhầm | 60 `GET /healthz` liên tiếp đều 200: rate limit chỉ áp cho `/jobs/`. |

Ngoài các quy tắc trên, nên có (không chấm, nhưng sẽ bị hỏi khi review): `ssl_protocols TLSv1.2 TLSv1.3`,
`server_tokens off`, `proxy_http_version 1.1` kèm `keepalive` ở upstream, timeout tới upstream có chủ đích. Viết lý do
cho mỗi lựa chọn trong README của bạn. HSTS cố ý không yêu cầu: bật HSTS cho `localhost` với cert tự ký làm trình duyệt
nhớ luật đó và gây phiền cho mọi dự án local khác trên cùng tên miền.

### 3. Chạy thử trước stack thật

Sau khi `bootstrap.sh` của M01 đã dựng project compose `olist-shop`, gắn Nginx vào mạng của project đó (để tên `api`
phân giải được) và mở cổng chỉ trên `127.0.0.1`. Chạy từ gốc repo, `DEVOPS_CPUSET` đặt theo
[Ghim CPU](../../README.md#ghim-cpu-trên-máy-dùng-chung) (để trống nếu không ghim):

```bash
edge=tracks/devops/capstone/project/nginx
bash "$edge/gen-cert.sh" "$edge/tls" && docker run --rm -d --name olist-shop-edge \
  --network olist-shop_default ${DEVOPS_CPUSET:+--cpuset-cpus "$DEVOPS_CPUSET"} --memory 128m \
  -p 127.0.0.1:28080:80 -p 127.0.0.1:28443:443 \
  -v "$PWD/$edge/olist-shop.conf:/etc/nginx/conf.d/default.conf:ro" -v "$PWD/$edge/tls:/etc/nginx/tls:ro" \
  nginx:1.30.6-alpine
```

Kiểm bằng `curl`, tin đúng cert của bạn thay vì tắt kiểm tra bằng `-k`:

```bash
edge=tracks/devops/capstone/project/nginx
curl -sS --cacert "$edge/tls/olist-shop.crt" --resolve olist-shop.local:28443:127.0.0.1 -H 'X-Request-ID: thu-m02' -D - https://olist-shop.local:28443/readyz
for i in $(seq 1 30); do curl -s -o /dev/null -w '%{http_code} ' --cacert "$edge/tls/olist-shop.crt" --resolve olist-shop.local:28443:127.0.0.1 -X POST https://olist-shop.local:28443/jobs/recompute; done; echo
docker logs olist-shop-edge 2>&1 | grep thu-m02 && docker compose -p olist-shop -f tracks/devops/sample-app/compose.yaml logs api | grep thu-m02
```

Ở đây redirect của cổng 28080 trỏ tới `https://olist-shop.local/...` (cổng 443), không tới 28443: đó là đúng với cấu
hình production, chỉ lệch vì lab đổi cổng. Dọn khi xong:

```bash
docker rm -f olist-shop-edge
```

### 4. Chạy test

```bash
uv run pytest tracks/devops/capstone/project/tests -q -rs -k m02
```

Trên máy dùng chung, thêm `nice -n 15 ${DEVOPS_CPUSET:+taskset -c "$DEVOPS_CPUSET"}` trước `uv run`. Test cần Docker và
hai image đã pull; thiếu thì skip kèm lệnh `docker pull` cần chạy. Test cert không cần Docker.

## Kết quả nộp

- `capstone/project/nginx/gen-cert.sh`
- `capstone/project/nginx/olist-shop.conf`
- Mục "Edge" trong README của bạn: sơ đồ client → Nginx → API, bảng các quyết định (rate và burst bạn chọn cho
  `/jobs/` và vì sao, vì sao 429 chứ không phải 503, vì sao giữ id client gửi lên và rủi ro của việc đó, vì sao Nginx
  thay vì Caddy cho dự án này).

## Tiêu chí đạt

- [ ] `uv run pytest tracks/devops/capstone/project/tests -q -rs -k m02` pass, không skip.
- [ ] `gen-cert.sh`: cert tự ký có SAN đúng, key `600` khớp cert, thời hạn ≤ 398 ngày, chạy lại không đổi tệp, tạo lại
      khi cert hết hạn hoặc key lệch; qua `shellcheck -S style`.
- [ ] `olist-shop.conf`: `nginx -t` pass, HTTP 301/308 sang HTTPS giữ nguyên đường dẫn và query, HTTPS proxy tới
      `api:8000` với `Host`, `X-Forwarded-Proto`, `X-Real-IP`, `X-Forwarded-For`.
- [ ] `X-Request-ID` giữ nguyên khi client gửi, sinh bằng `$request_id` khi không có, trả về đúng một header, có trong
      log API và access log Nginx.
- [ ] `/jobs/` bị giới hạn và trả 429; `/healthz` không bị giới hạn.
- [ ] (Tự đánh giá) Đã chạy vòng thật ở mục 3 và lần được một request id từ `curl` qua log Nginx tới log API.
- [ ] (Tự đánh giá) README có mục "Edge" như phần Kết quả nộp.
