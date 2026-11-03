# Runbook dịch vụ ETA

Mỗi alert trong `monitoring/rules/eta.rules.yml` có `runbook_url` trỏ vào một mục dưới đây. Mỗi mục theo cùng thứ tự:
triệu chứng người dùng thấy, các bước kiểm tra (lệnh chạy được), hành động theo từng kết quả kiểm tra, và khi nào leo
thang. Dashboard: Grafana, thư mục ETA, "ETA service - RED và model". Mọi lệnh chạy từ thư mục project.

Thông tin chung:

- API: `http://127.0.0.1:28080` (`/healthz`, `/readyz`, `/metrics`, `POST /admin/reload` cần `X-Admin-Token`).
- Registry: model `eta`, alias `champion` (đang phục vụ) và `challenger` (shadow hoặc canary).
- Rollback chuẩn: `MlflowClient().set_registered_model_alias("eta", "champion", "<version cũ>")` rồi
  `curl -X POST -H "X-Admin-Token: $ETA_ADMIN_TOKEN" http://127.0.0.1:28080/admin/reload`, kiểm `/readyz` báo version cũ.
  Không rebuild, không restart; mất dưới một phút.
- On-call chính xử lý mọi alert `critical` trong 15 phút; `warning` xử lý trong giờ làm việc.

## EtaHighErrorRate

### Triệu chứng

Hơn 5% request `POST /predict` trả 5xx trong 5 phút liên tục. Ứng dụng gọi ETA hiện "không ước tính được thời gian";
lỗi 422 (input sai) không tính vào đây vì đó là lỗi của bên gọi.

### Kiểm tra

1. Panel "Request /predict theo status": lỗi là 500 hay 503? 503 nghĩa là API chưa sẵn sàng (`/readyz` 503, thiếu bảng
   tốc độ hoặc đang nạp), 500 nghĩa là model ném lỗi khi chấm.
2. `curl -s http://127.0.0.1:28080/readyz` và `docker compose logs --since 15m api | grep -E "reload|not_ready|error"`.
3. Panel "Model đang chạy": version có vừa đổi không (deploy hay reload trong 30 phút gần nhất)?
4. Panel "Fallback canary và lỗi shadow": canary lỗi thì đã fallback, nên 5xx thường đến từ champion.

### Hành động

- Version vừa đổi và lỗi bắt đầu ngay sau đó: rollback về version trước (lệnh ở đầu trang), xác nhận tỉ lệ lỗi về 0
  trong 10 phút, mở ticket cho version lỗi.
- `/readyz` 503 vì thiếu `ETA_SPEED_TABLE`: đặt lại biến, `docker compose up -d api`, chờ `/readyz` 200.
- Lỗi do input lạ (zone mới, giờ lạ) mà model chưa từng thấy: ghi lại `request_id` mẫu từ log, rollback nếu version mới,
  nếu không thì leo thang cho người sở hữu model.

### Leo thang

Sau 30 phút tỉ lệ lỗi vẫn trên 5% hoặc rollback không giúp: gọi người sở hữu service ETA và báo kênh sự cố. Ghi dòng
thời gian ngay từ đầu để viết postmortem.

## EtaHighLatencyP95

### Triệu chứng

p95 thời gian xử lý `/predict` trên 0.3 giây suốt 10 phút; ứng dụng gọi bị chậm, có thể timeout ở phía client.

### Kiểm tra

1. Panel p50/p95 theo variant: chỉ canary chậm hay cả champion? Chỉ canary chậm thì đó là tiêu chí dừng canary.
2. `docker stats` của container API: CPU chạm giới hạn `cpuset` hay RAM gần 512 MB?
3. Request/giây có tăng đột biến không (panel đầu tiên)? Có reload vừa xảy ra (request đầu sau reload có warmup)?

### Hành động

- Canary chậm: đặt `ETA_CANARY_WEIGHT=0` và reload, ghi số đo vào ticket của challenger.
- Tải tăng thật: tăng số worker uvicorn hoặc thêm replica; chạy lại k6 (`loadtest/eta.js`) để xác nhận p95.
- Model mới nặng hơn (nhiều cây hơn): rollback và mở ticket tối ưu model.

### Leo thang

p95 trên 1 giây hoặc kèm `EtaHighErrorRate`: xử lý như sự cố `critical`, leo thang ngay.

## EtaMetricsAbsent

### Triệu chứng

Prometheus không còn thấy `eta_model_info` của job `eta-api` trong 5 phút: API chết, không nạp được model, hoặc
Prometheus không scrape được. Có thể người dùng vẫn được phục vụ (lỗi phía monitoring) hoặc mất dịch vụ hoàn toàn.

### Kiểm tra

1. `curl -s http://127.0.0.1:28080/healthz` và `/readyz` từ máy chủ.
2. `docker compose ps api`: container có đang restart lặp không, exit code là gì?
3. Prometheus UI, trang Targets: target `api:8000` báo lỗi gì (DNS, connection refused, timeout)?

### Hành động

- API chết: `docker compose logs --tail 200 api`, sửa nguyên nhân (thiếu biến môi trường, registry không truy cập được),
  `docker compose up -d api`.
- API sống nhưng Prometheus không scrape: kiểm mạng Compose và `monitoring/prometheus.yml`, rồi reload Prometheus.
- API sống nhưng `eta_model_info` trống: model chưa nạp xong (`/readyz` 503), xử lý như mục EtaHighErrorRate.

### Leo thang

Không có metric quá 15 phút nghĩa là đang mù: leo thang cho người sở hữu nền tảng monitoring song song với service ETA.

## EtaPredictionShift

### Triệu chứng

Trung vị ETA dự đoán lệch hơn 30% so với cùng thời điểm 7 ngày trước, kéo dài 1 giờ. Chưa có nhãn để biết đúng hay sai:
đây là tín hiệu proxy, không phải bằng chứng chất lượng giảm.

### Kiểm tra

1. Version có đổi trong 7 ngày qua không? Nếu có, so dự đoán shadow và champion trên cùng request trong log dự đoán.
2. Phân phối đầu vào có đổi không: chạy `drift_table` trên log dự đoán 24 giờ gần nhất so với cùng kỳ tuần trước
   (`trip_distance`, giờ đón, `eta_s`).
3. Có sự kiện bên ngoài không (lễ, bão, đóng đường, phong toả)? Ghi vào ticket.

### Hành động

- Lệch đến từ version mới: rollback, mở ticket cho challenger.
- Lệch đến từ dữ liệu đầu vào có lý do mùa vụ: giữ model, theo dõi; quyết định thật chờ nhãn (chậm một tháng).
- Khi nhãn của giai đoạn này về: chạy `eta.cli replay` cho tháng đó, ghi quyết định `retrain`, `rollback` hoặc `keep`
  vào `reports/decisions/<tháng>.yaml` kèm số liệu.

### Leo thang

Lệch trên 50% kéo dài một ngày, hoặc kèm phản ánh của người dùng: mời người sở hữu model và DS vào xem cùng.

## Quyết định hằng tháng sau khi nhãn về

Mỗi đầu tháng, nhãn của tháng trước công bố. Chạy phát lại, mở `reports/replay/summary.parquet`, và đi qua bốn bước
phát hiện, xác minh, tác động, quyết định: drift không đồng nghĩa với train lại; chỉ train lại khi MAE trên nhãn đã về
xấu đi có ý nghĩa và một challenger chứng minh tốt hơn trên dữ liệu gần nhất; rollback khi có version trước tốt hơn
trên cùng lưu lượng; ngược lại giữ nguyên và ghi lý do.
