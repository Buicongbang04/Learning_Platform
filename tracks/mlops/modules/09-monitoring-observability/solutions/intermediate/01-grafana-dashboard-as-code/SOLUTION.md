# Lời giải: dashboard Grafana as code

## Ý chính

- **Provider + JSON trong Git.** `provider.yml` nói với Grafana "nạp mọi `.json` trong thư mục này vào thư mục MLOps". Gắn
  hai tệp vào container qua volume (`/etc/grafana/provisioning/dashboards` cho provider, `/var/lib/grafana/dashboards/eta` cho JSON),
  Grafana mới hay mất volume vẫn dựng lại đúng. `allowUiUpdates: false` buộc sửa đổi phải đi qua Git; `disableDeletion: true` chặn xoá nhầm.
- **Biến datasource.** `${datasource}` làm cùng một JSON chạy ở dev, staging và production dù uid datasource khác nhau.
- **Mỗi panel trả lời một câu hỏi.** Rate, Errors, Duration cho service; phiên bản, phân phối dự đoán, tỉ lệ fallback cho model.
  Không panel nào chỉ để "trông đẹp".
- **Percentile từ histogram.** Luôn `sum by (le)` rồi mới `histogram_quantile`: lấy quantile trên từng series rồi mới gộp là sai
  về toán (không thể lấy trung bình của p95). Đây cũng là lý do metric độ trễ phải là histogram, không phải summary.
- **`$__rate_interval`** tự theo khoảng scrape và độ phân giải panel, tránh đồ thị trống khi phóng to.
- **Kiểm bằng chính Grafana.** `/api/ds/query` chạy câu truy vấn thật qua datasource; PromQL sai cú pháp bị bắt trước khi ai đó mở dashboard lúc sự cố.

## Lỗi hay gặp

- Commit bản export nguyên vẹn: có `id`, `version`, uid datasource cứng của máy bạn; import vào nơi khác thì panel trống.
- Vẽ counter thô: đường đi lên mãi, không đọc ra được gì; luôn `rate`.
- Ngưỡng màu và đơn vị bị bỏ qua: `unit: percentunit` cho tỉ lệ, `s` cho thời gian để Grafana tự định dạng.
- Dashboard quá nhiều panel: người trực không đọc nổi; để chi tiết ở dashboard con, dashboard tổng chỉ chứa tín hiệu vàng.
