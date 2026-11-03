# Lời giải: instrument service ETA

## Ý chính

- **Registry riêng cho mỗi app.** Registry toàn cục của `prometheus_client` báo `Duplicated timeseries` khi `create_app()` chạy
  lần hai (test, reload, nhiều worker import). Truyền `registry=` cho mọi metric và `generate_latest(registry)` cho `/metrics`.
- **Một middleware đo mọi thứ.** Nó bọc `call_next` để thấy cả ngoại lệ. Route lấy sau khi `call_next` chạy xong, vì FastAPI chỉ
  gắn `scope["route"]` lúc khớp đường dẫn. Đường dẫn không khớp thì gom về `unmatched`: nếu dùng `request.url.path` làm label, một
  con bot quét `/wp-admin/...` đủ làm nổ số series.
- **Không đo `/metrics`.** Mỗi lần Prometheus scrape 15 giây một lần sẽ cộng thêm vào `Rate` và kéo trung bình độ trễ xuống.
- **Bucket chọn theo ngưỡng.** Từ 5 ms tới 2.5 s phủ độ trễ của service nhỏ và có bucket quanh SLO 250 ms; bucket của
  `eta_prediction_seconds` theo thang phút (1 phút tới 1 giờ) vì đây là giá trị nghiệp vụ, không phải thời gian xử lý.
- **Info metric** cho phiên bản model: một series giá trị 1, đổi phiên bản thì series cũ biến mất sau khi tiến trình khởi động lại.
  Join nó vào dashboard bằng `* on() group_left(version) eta_model_info`.

## Lỗi hay gặp

- Đặt `request_id` hoặc `user_id` làm label: mỗi giá trị là một series, số series tăng vô hạn, Prometheus hết RAM. Chi tiết
  của từng yêu cầu thuộc về log có cấu trúc (bài 02), không phải metric.
- Quên đếm 500 vì ngoại lệ thoát khỏi middleware trước dòng `inc()`: đúng lúc có lỗi thì số lỗi lại không tăng.
- `status` truyền vào `labels()` là số nguyên: nên ép thành chuỗi (`str(response.status_code)`) cho nhất quán giữa các nơi ghi.
