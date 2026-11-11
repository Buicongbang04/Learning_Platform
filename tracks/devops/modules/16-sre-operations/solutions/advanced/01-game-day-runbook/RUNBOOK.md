# Runbook: Olist Shop

Áp dụng cho stack Olist Shop (api, worker, postgres, redis) cộng stack observability. Mỗi phần dưới đây ứng với một entry của
`runbook.yaml`, theo đúng thứ tự máy kiểm: entry trên được xét trước.

## api-unreachable

### Triệu chứng

Khách không mở được trang tra đơn, client nhận lỗi kết nối chứ không phải 5xx. Dashboard RED trống dữ liệu của API, panel `up` đỏ.

### Chẩn đoán

Truy vấn Prometheus: `up{job="olist-api"} == 0`. Kết quả khác rỗng nghĩa là Prometheus không scrape được API. Xem trạng thái container
(`docker compose ps api`): `exited` với mã 137 là bị kill (OOM hay tín hiệu), mã khác thì đọc log cuối trong Loki
`{service_name="olist-shop-api"}`.

### Khôi phục

Chạy `start api` (`docker compose start api`). Nếu container thoát lại ngay, không lặp lệnh: lưu 40 dòng log cuối rồi chuyển sang leo
thang.

### Xác nhận

`up{job="olist-api"}` về 1 trong một chu kỳ scrape, `/readyz` trả 200, tỉ lệ 5xx của mọi route dưới 1% trong 10 phút.

### Leo thang

Sau 10 phút hay sau hai lần start thất bại: gọi người trực thứ hai, mở kênh sự cố, chỉ định incident commander, báo trạng thái cho bộ
phận chăm sóc khách hàng mỗi 30 phút.

## api-slow

### Triệu chứng

Khách báo tra đơn chậm; p95 của route tra đơn vượt 300 ms trong khi tỉ lệ lỗi vẫn thấp. Thường kéo theo mọi route khác cùng chậm.

### Chẩn đoán

Truy vấn: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="olist-api", path="/orders/{order_id}"}[1m]))) > 0.3`.
Route này chỉ chạm Postgres nên chậm ở đây là chậm ở API hoặc đường mạng của API. Mở một trace chậm trong Jaeger: thời gian nằm giữa
các span (không trong span DB) là dấu hiệu mạng hay CPU của chính API.

### Khôi phục

Lưu một trace và 5 phút log làm bằng chứng, rồi chạy `restart api`. Vừa deploy trong 30 phút trước thì rollback thay vì restart.

### Xác nhận

p95 route tra đơn dưới 300 ms trong 10 phút liên tục; trace mới không còn khoảng trống bất thường giữa các span.

### Leo thang

Restart không giúp: gọi người trực platform để kiểm node và mạng; cân nhắc chuyển traffic sang bản dự phòng nếu có.

## queue-rejected

### Triệu chứng

Nút "tính lại doanh thu" báo lỗi, `POST /jobs/recompute` trả 503; tra đơn vẫn bình thường.

### Chẩn đoán

Truy vấn Loki: `{service_name="olist-shop-api"} |= "không đẩy được job vào redis"`. Có dòng log nghĩa là API không ghi được vào Redis.
Đọc phần `exception` của dòng log: lỗi kết nối (Redis tắt) hay lỗi ghi (Redis còn sống nhưng từ chối ghi, ví dụ đĩa đầy).

### Khôi phục

Chạy `restart redis`. Redis của bài chỉ chứa hàng đợi job, mất job đang chờ chấp nhận được (người dùng bấm lại). Trên production có
dữ liệu thật thì giải phóng chỗ trước, không restart mù.

### Xác nhận

`POST /jobs/recompute` trả 202 trở lại, worker xử lý job (log `job done`), không còn dòng log lỗi Redis trong 5 phút.

### Leo thang

Redis không lên hay lỗi lặp lại trong một giờ: gọi người trực platform, xem dung lượng và cấu hình lưu trữ của Redis.

## queue-slow

### Triệu chứng

Đẩy job chậm, `POST /jobs/recompute` vượt 300 ms trong khi tra đơn vẫn nhanh.

### Chẩn đoán

Truy vấn: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{job="olist-api", path="/jobs/recompute"}[1m]))) > 0.3`.
Route tra đơn vẫn nhanh nên vấn đề nằm ở Redis hay đường tới Redis. Span `send olist:jobs` trong Jaeger dài là xác nhận.

### Khôi phục

Chạy `restart redis` sau khi lưu một trace chậm làm bằng chứng.

### Xác nhận

p95 của `/jobs/recompute` dưới 300 ms trong 10 phút, span `send olist:jobs` trở lại vài ms.

### Leo thang

Còn chậm sau restart: gọi người trực platform kiểm mạng giữa API và Redis.
