# Runbook Olist Shop

Mỗi mục dưới đây ứng với một entry của `runbook.yaml` (phần máy chạy được) hoặc một alert trỏ `runbook_url` vào đây. Lệnh compose
chạy từ thư mục deploy, `docker compose -p olist-shop-prod ...`; trên Kubernetes thay bằng lệnh tương ứng trong phần Khôi phục. SLO
liên quan: `api-availability` 99,5%/30 ngày, 216 phút error budget (`sre/slo.yaml`).

Thứ tự entry trong `runbook.yaml` là thứ tự chẩn đoán: từ thành phần mà mọi triệu chứng khác phụ thuộc (API sống không, mạng của API) tới
thành phần sau nó (Postgres, rồi Redis). Một sự cố ở API làm cả tra đơn lẫn đẩy job chậm; nếu đọc entry Postgres trước sẽ restart nhầm
database.

## slo-burn

### Triệu chứng

Alert `OlistApiErrorBudgetBurn` bắn: page khi đốt budget nhanh (mức 1h gấp 14,4 lần, mức 6h gấp 6 lần), ticket khi đốt đều (mức 1d
gấp 3 lần). Đây là alert theo triệu chứng của khách, không nói thành phần nào hỏng.

### Tác động

Mức 1h nghĩa là 2% budget 30 ngày đã mất trong một giờ, khoảng 4 phút trên 216; để vậy hai ngày là hết budget. Khách tra đơn hay đẩy
job tính lại nhận 5xx.

### Chẩn đoán

Mở dashboard Olist Shop, panel tỉ lệ lỗi theo path, rồi đi lần lượt các mục dưới đây theo thứ tự trong tệp: `up{job="olist-api"}`,
`scrape_duration_seconds` của API, 5xx và p95 của `/orders/{order_id}` (Postgres), rồi của `/jobs/recompute` (Redis). Kiểm deploy gần
nhất trong lịch sử ArgoCD: lỗi bắt đầu đúng lúc rollout thì nghi bản mới trước.

### Khôi phục

Đi theo mục cụ thể vừa tìm ra. Nếu lỗi bắt đầu cùng lúc với một rollout: rollback bằng `git revert` commit đổi version (M07) thay vì
restart; restart không chữa được bản lỗi.

### Xác nhận

`olist:slo_api_errors:ratio_rate5m` về 0 trong 5 phút và alert mức page tự tắt (cửa sổ ngắn hết vượt ngưỡng). Ghi lại số phút budget
đã tiêu vào kênh sự cố.

### Leo thang

Sau 15 phút chưa rõ thành phần nào: gọi người trực thứ hai. Budget còn dưới 25%: báo product owner, áp dụng policy đóng băng deploy tính
năng cho tới khi budget hồi.

## api-unreachable

### Triệu chứng

Prometheus không scrape được API, khách nhận lỗi kết nối hay 502 từ Nginx. Dashboard trống ở mọi panel của API vì không còn metric.

### Tác động

Mọi hành trình của khách hỏng hoàn toàn. SLI đo ở server không thấy những request này (API chết thì không đếm được), nên budget thật
đang tiêu nhanh hơn số trên dashboard.

### Chẩn đoán

Truy vấn `up{job="olist-api"} == 0` trên Prometheus. Rồi `docker compose ps api`: trạng thái `exited` kèm exit code 137 là bị kill
(OOM hay lệnh từ ngoài), exit code khác thì đọc `docker compose logs --tail 100 api`.

### Khôi phục

`start api` (`docker compose start api`). Container bị kill từ ngoài không được restart policy `unless-stopped` dựng lại; Docker coi đó
là dừng có chủ đích. Nếu container khởi động rồi chết lại ngay: đừng lặp lại, sang Leo thang.

### Xác nhận

`/readyz` trả 200, `up{job="olist-api"}` về 1, tra một đơn có thật trả 200 dưới 0,5 giây, `olist:api_requests:rate1m` có lại dữ liệu.

### Leo thang

Chết lại trong 5 phút sau khi start, hay exit code 137 kèm `OOMKilled: true`: gọi người trực thứ hai, cân nhắc rollback bản gần nhất
và tăng giới hạn RAM có kế hoạch, không tăng tay trên máy production.

## api-network-slow

### Triệu chứng

Mọi route của API chậm cùng lúc, kể cả tra đơn và đẩy job, trong khi Postgres và Redis không có dấu hiệu quá tải. Prometheus mất nhiều
thời gian để scrape `/metrics` của API.

### Tác động

Khách chờ quá 0,5 giây cho mọi thao tác; request vượt timeout của client hay Nginx thành lỗi và tiêu budget.

### Chẩn đoán

Truy vấn `max(scrape_duration_seconds{job="olist-api"}) > 0.5`. `/metrics` không chạm database nên scrape chậm chỉ do chính API hay
mạng của container API. So `scrape_duration_seconds` của worker: bình thường thì lỗi nằm ở API, không phải cả host.

### Khôi phục

`restart api` (`docker compose restart api`): container chạy lại với network namespace mới. Trước khi restart, lưu `docker compose
logs api` và `docker inspect` để còn bằng chứng cho postmortem.

### Xác nhận

`scrape_duration_seconds{job="olist-api"}` về mức vài chục mili giây, p95 của `/orders/{order_id}` dưới 0,3 giây trong 1 phút.

### Leo thang

Chậm lại sau restart: vấn đề nằm ở host hay mạng Docker. Gọi người trực hạ tầng, kiểm `tc qdisc show` và tải mạng của host.

## db-errors

### Triệu chứng

Tra đơn trả 500, `/readyz` báo `"db": "error"`; đẩy job vẫn 202 nhưng worker không ghi được bảng `revenue_by_state`.

### Tác động

Hành trình tra đơn hỏng hoàn toàn, mỗi phút như vậy tiêu khoảng 1/216 budget nếu toàn bộ traffic là tra đơn.

### Chẩn đoán

Truy vấn `sum(rate(http_requests_total{job="olist-api", path="/orders/{order_id}", status=~"5.."}[30s])) > 0`. Rồi `docker compose ps
postgres` và log của API: `OperationalError` kèm "could not translate host name" hay "connection refused" là Postgres không chạy.

### Khôi phục

`restart postgres` (`docker compose restart postgres`, chạy được cả khi container đang dừng). Dữ liệu nằm trong volume `pgdata` nên
còn nguyên. API và worker tự nối lại nhờ `pool_pre_ping`.

### Xác nhận

`/readyz` trả 200, tra đơn có thật trả 200, `pg_isready` trong container báo accepting connections, đẩy một job và thấy
`jobs_processed_total` tăng.

### Leo thang

Postgres không lên hay log báo hỏng dữ liệu: dừng ngay mọi thao tác ghi, gọi người trực database, khôi phục từ backup của M01
(`backup.sh`, `pg_restore`) theo runbook khôi phục, không xoá volume.

## db-slow

### Triệu chứng

Tra đơn chậm (p95 trên 0,3 giây) nhưng không lỗi; đẩy job vẫn nhanh. `/readyz` chậm theo.

### Tác động

Khách tra đơn chờ lâu; request vượt timeout thành lỗi và tiêu budget. Worker tính lại doanh thu chậm theo.

### Chẩn đoán

Truy vấn `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="olist-api", path="/orders/{order_id}"}[30s]))) > 0.3`.
Trace của request chậm trong Jaeger: span DB chiếm gần hết thời gian thì nghi Postgres hay đường mạng tới nó. Kiểm `pg_stat_activity`
tìm query chạy lâu hay lock trước khi restart.

### Khôi phục

Có query giữ lock: huỷ đúng query đó bằng `pg_cancel_backend`. Không có: `restart postgres` (`docker compose restart postgres`); API
mất kết nối vài giây rồi tự nối lại.

### Xác nhận

p95 của `/orders/{order_id}` dưới 0,3 giây trong 1 phút, span DB trong Jaeger về mức mili giây.

### Leo thang

Chậm lại sau restart: gọi người trực database, kiểm đĩa và tải của host, cân nhắc chuyển traffic đọc sang bản sao nếu có.

## queue-errors

### Triệu chứng

`POST /jobs/recompute` trả 503 "redis unavailable", `/readyz` báo `"redis": "error"`; tra đơn vẫn bình thường.

### Tác động

Khách không yêu cầu tính lại doanh thu được; số liệu doanh thu theo bang đứng yên. Mỗi request 503 là một request xấu của SLI.

### Chẩn đoán

Truy vấn `sum(rate(http_requests_total{job="olist-api", path="/jobs/recompute", status=~"5.."}[30s])) > 0`. Log API có dòng
"không đẩy được job vào redis"; `docker compose ps redis` cho biết Redis đang dừng hay đang chạy mà không trả lời.

### Khôi phục

`restart redis` (`docker compose restart redis`, chạy được cả khi container đang dừng). AOF trong volume `redisdata` giữ các job đã
xếp hàng; worker tự nối lại sau vài giây.

### Xác nhận

`POST /jobs/recompute` trả 202, `redis-cli ping` trả PONG, `jobs_processed_total` của worker tăng trong 1 phút.

### Leo thang

Redis không lên hay AOF hỏng (`Bad file format reading the append only file`): gọi người trực thứ hai, chạy `redis-check-aof --fix`
trên bản sao của tệp, không trên tệp gốc.

## queue-slow

### Triệu chứng

Đẩy job chậm (p95 trên 0,3 giây), có lúc 503 vì vượt timeout 1 giây của client Redis trong API; tra đơn bình thường.

### Tác động

Khách bấm tính lại doanh thu phải chờ; request vượt timeout thành 503 và tiêu budget.

### Chẩn đoán

Truy vấn `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="olist-api", path="/jobs/recompute"}[30s]))) > 0.3`.
`redis-cli --latency` từ container API: độ trễ cao mà Redis không bận (`INFO stats`) thì nghi đường mạng tới Redis.

### Khôi phục

`restart redis` (`docker compose restart redis`): container chạy lại với network namespace mới; job đã xếp hàng còn trong AOF.

### Xác nhận

p95 của `/jobs/recompute` dưới 0,3 giây trong 1 phút, `redis-cli --latency` dưới 1 mili giây.

### Leo thang

Chậm lại sau restart: gọi người trực hạ tầng kiểm mạng Docker và tải của host; tạm báo khách tính lại doanh thu sẽ trễ.
