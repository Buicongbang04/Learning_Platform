# Runbook: dịch vụ ví dụ

## db-down

### Triệu chứng

Mọi request đọc dữ liệu trả 500, `/readyz` báo `db: error`, dashboard RED của API đỏ toàn bộ.

### Chẩn đoán

Alert dựa trên truy vấn `pg_up == 0`. Mở Grafana, panel Postgres, xác nhận exporter không kết nối được database; xem log của container
postgres trong Loki để biết nó tắt hay treo.

### Khôi phục

Chạy `start postgres` (docker compose start postgres). Nếu container không lên, đọc 40 dòng log cuối rồi leo thang.

### Xác nhận

`pg_up` về 1, tỉ lệ 5xx của API về 0 trong 5 phút, `/readyz` trả 200 ổn định.

### Leo thang

Sau 15 phút chưa khôi phục: gọi người trực của team dữ liệu, mở kênh sự cố, cập nhật trang trạng thái mỗi 30 phút.

## api-slow

### Triệu chứng

Khách báo tra đơn chậm, p95 latency trên dashboard vượt 300 ms trong khi tỉ lệ lỗi vẫn thấp.

### Chẩn đoán

Truy vấn: `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[1m]))) > 0.3`. Xem trace chậm trong Jaeger để
biết thời gian nằm ở span nào.

### Khôi phục

Chạy `restart api` sau khi đã lưu trace và log làm bằng chứng. Nếu vừa deploy, rollback thay vì restart.

### Xác nhận

p95 dưới 300 ms trong 10 phút liên tục, không có span nào chậm bất thường trong Jaeger.

### Leo thang

Restart không giúp thì gọi người trực mạng và team platform, ghi lại thời điểm để tính error budget.
