# Lời giải: startupProbe cho model nạp chậm

Xem `eta-api.yaml`: thêm

```yaml
startupProbe:
  httpGet: {path: /healthz, port: http}
  periodSeconds: 5
  failureThreshold: 24
```

Ngân sách 5 × 24 = 120 giây, gấp 3 lần thời gian nạp 40 giây. Liveness giữ nguyên (5 + 5 × 3 = 20 giây).

## Vì sao bản gốc chết

Liveness bắt đầu sau 5 giây, mỗi 5 giây một lần, 3 lần liên tiếp thất bại thì kubelet giết container. Sau ~20 giây container bị giết, chạy lại, nạp lại từ đầu, lại bị giết: model không bao giờ nạp xong (mỗi lần restart lại tải model, tốn băng thông object storage). Sau vài lần, trạng thái thành `CrashLoopBackOff` với thời gian chờ tăng dần.

## Vì sao không chỉ tăng `initialDelaySeconds` của liveness

`initialDelaySeconds: 90` trên liveness cũng làm pod lên được, nhưng:

- Nó áp cho **mọi** lần khởi động, kể cả khi model nạp nhanh (cache ấm): service treo lúc khởi động phải chờ 90 giây mới bị phát hiện.
- Nó là một con số cố định; startupProbe thì kết thúc ngay khi service lên (thử mỗi 5 giây) và chỉ có trần là 120 giây.
- Trộn hai câu hỏi khác nhau: "đã khởi động xong chưa" (startup) và "còn sống không" (liveness).

## Ba probe

| Probe | Câu hỏi | Thất bại thì |
| --- | --- | --- |
| startupProbe | Đã khởi động xong chưa? | Hết ngân sách thì giết container |
| readinessProbe | Có nhận traffic được không? | Bỏ pod khỏi Endpoints, không giết |
| livenessProbe | Có bị treo không? | Giết container |

Liveness không nên kiểm phụ thuộc bên ngoài (database, feature store): phụ thuộc chết làm mọi pod bị giết cùng lúc mà không sửa được gì.
