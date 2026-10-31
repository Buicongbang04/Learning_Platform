# Lời giải: load balancing và passive health check

```nginx
upstream olist_api {
    zone olist_api 64k;
    server olist-api-1:8000 max_fails=3 fail_timeout=30s;
    server olist-api-2:8000 weight=3 max_fails=3 fail_timeout=30s;
}
```

## Weight

Round robin của Nginx là **smooth weighted round robin**: với trọng số 1:3, chu kỳ bốn request là `api-2, api-1, api-2,
api-2`, rải đều chứ không dồn ba request liền vào một máy. 40 request ra đúng 10 và 30. Weight hợp khi các máy khác cấu hình (máy cũ, máy
mới) hoặc khi chạy canary (`weight=1` cho bản mới trên tổng 20 là khoảng 5% lưu lượng). Nếu request có thời gian xử lý rất
khác nhau (một số request báo cáo nặng), `least_conn` thường tốt hơn: nó đếm kết nối đang mở thay vì đếm lượt.

## `max_fails` và `fail_timeout`

- Một lần thử **lỗi** là lỗi kết nối, timeout, hoặc response bị coi là lỗi theo `proxy_next_upstream` (mặc định
  `error timeout`; `http_500`, `http_502`... chỉ được tính khi bạn liệt kê chúng). 404 hay 500 bình thường của app không
  tính.
- Trong cửa sổ `fail_timeout`, đủ `max_fails` lần lỗi thì server bị coi là **không khả dụng** trong `fail_timeout` tiếp
  theo. Hết thời gian đó Nginx cho một request thật đi thử; thành công thì server quay lại vòng quay.
- Mặc định là `max_fails=1 fail_timeout=10s`: một lỗi thoáng qua (một lần timeout do GC pause) rút backend ra 10 giây. Với
  hai backend, rút một là dồn gấp đôi tải lên bản còn lại. `max_fails=3` chịu được lỗi lẻ; `fail_timeout=30s` đủ lâu để
  không thử lại liên tục một máy đang khởi động lại.
- Trong test bạn thấy trong error log vài dòng `connect() failed (111: Connection refused)` rồi `upstream server
  temporarily disabled`; người dùng không thấy gì vì mỗi request lỗi được Nginx thử tiếp trên `olist-api-1` trong cùng request.

## Vì sao `zone`

Không có `zone`, mỗi worker giữ bộ đếm lỗi và vị trí round robin **riêng**. Với `worker_processes auto` trên máy 16 core,
một backend chết có thể bị thử `16 x max_fails` lần, và tỉ lệ weight chỉ đúng trong từng worker. `zone` đặt trạng thái
upstream vào shared memory cho mọi worker dùng chung. Bài để `worker_processes 1` để kết quả test xác định được; trong
production luôn có `zone` khi có nhiều worker.

## Passive health check làm được và không làm được gì

- Làm được: rút backend chết dựa trên lưu lượng thật, không tốn request riêng.
- Không làm được: phát hiện backend hỏng khi không có traffic (sự cố lúc 3 giờ sáng bị người dùng đầu tiên buổi sáng gặp);
  phát hiện backend **treo** nhanh (mỗi lần thử tốn trọn `proxy_connect_timeout` hoặc `proxy_read_timeout`, mặc định 60
  giây); phát hiện backend sống nhưng hỏng nghiệp vụ (`/readyz` trả 503 vì mất DB).
- Active health check (`health_check` trong `location`) chỉ có ở NGINX Plus. Với Nginx open source, active check do lớp
  khác làm: load balancer cloud gọi `/readyz`, Kubernetes readiness probe rút pod khỏi Service, Consul/HAProxy/Envoy có
  active check sẵn.

Backend treo: nên đặt `proxy_connect_timeout` ngắn (1–2 giây trong cùng data center) để lỗi kết nối được phát hiện nhanh,
còn `proxy_read_timeout` theo SLO của route. `POST` không được Nginx tự thử lại trên backend khác khi đã gửi request đi
(từ 1.9.13, trừ khi có `non_idempotent`): thử lại một `POST /jobs/recompute` là chạy job hai lần.

## Keep-alive tới upstream

Từ Nginx 1.29.7 (có trong nhánh stable 1.30), `keepalive` trong `upstream` bật sẵn, `proxy_http_version` mặc định là 1.1
và Nginx không còn gửi `Connection: close`. Trên các bản cũ hơn (1.24, 1.26, 1.28 vẫn còn rất phổ biến trong distro), mỗi
request mở một kết nối TCP mới tới backend, dễ cạn cổng nguồn (`TIME_WAIT`) khi tải cao; phải tự thêm `keepalive 32;` trong
`upstream` cùng `proxy_http_version 1.1;` và `proxy_set_header Connection "";` trong `location`. Kiểm bản bạn đang chạy
trước khi chép cấu hình từ blog.
