# Lời giải: retry và timeout bằng HTTPRoute của Linkerd

## Cách làm

Hai route trên cùng Service `freight`:

- `freight-quote` khớp `GET` và path `Exact /quote`, với `retry.linkerd.io/http: 5xx`, `retry.linkerd.io/limit: "3"`,
  `retry.linkerd.io/timeout: 300ms`, `timeout.linkerd.io/request: 2s`.
- `freight-reserve` khớp `POST /reserve`, chỉ có `timeout.linkerd.io/request: 3s` (lớn hơn 2,5 s của lần chậm nhất, để không cắt một lần
  giữ chỗ đang thành công), không có annotation retry.

## Vì sao

- **Retry 5xx một mình không đủ.** Request treo 2,5 giây không phải 5xx, nên không được retry; client chờ hết 2,5 giây. Timeout mỗi lần
  thử biến lần treo thành một lần thất bại có thể retry: proxy bỏ lần thử sau 300 ms và gửi lần mới. Timeout cả request là trần cuối
  cùng cho người gọi.
- **Chọn 300 ms**: lần nhanh của freight dưới 10 ms; 300 ms đủ rộng để không cắt nhầm request bình thường khi node bận, đủ hẹp để 4 lần
  thử vẫn dưới 2 s. Ở production, chọn theo p99 thật của backend cộng một khoảng, không đoán.
- **Giới hạn số lần thử.** Mỗi lần thử có xác suất hỏng khoảng 0,3 (503 hay quá 300 ms), 4 lần thử thì xác suất cả bốn hỏng khoảng
  0,3 mũ 4, dưới 1%. Tải lên backend trung bình khoảng 1 + 0,3 + 0,09 + 0,027, tức 1,4 lần; lần chạy kiểm chứng đo được 262 request cho 200
  request. Khi `freight` sập hẳn, mỗi request thành đúng 4 lần thử: giới hạn là thứ ngăn retry storm. Linkerd không có retry budget
  theo tỉ lệ cho HTTPRoute (khác ServiceProfile cũ), nên giữ `limit` nhỏ.
- **Không retry POST /reserve.** Proxy không biết lần đầu đã giữ chỗ hay chưa (503 có thể trả sau khi đã ghi; timeout thì càng không biết).
  Retry ở mesh sẽ giữ chỗ hai lần. Muốn retry phải có idempotency key ở ứng dụng (bài Basic 02) và server lưu kết quả theo key.
- **404 khi chỉ có route cho GET.** Theo Gateway API, khi Service đã có HTTPRoute, request không khớp rule nào bị từ chối với 404. Bản nháp
  bắt mọi path nên không bị 404, nhưng lại retry cả POST. Phải có route riêng cho mỗi nhóm hành vi.

## Đọc số liệu

- `outbound_http_route_retry_requests_total` trên proxy của checkout đếm số lần thử lại; `outbound_http_route_request_statuses_total`
  đếm kết quả cuối mà ứng dụng nhận. Đặt cạnh số request backend nhận (inbound của freight) là thấy hệ số khuếch đại.
- Status `Accepted=False` thường do `parentRefs` sai `group` (Service là `core`) hay `port`.

## Lỗi hay gặp

- `retry.linkerd.io/limit` không đặt: mặc định chỉ 1 lần thử lại, khoảng 4% request vẫn nhận 503 (0,2 bình phương). Đã đo: 100 request
  thành 117 lần gọi backend, 2 request lỗi.
- Đặt annotation ở `spec` thay vì `metadata.annotations`.
- Một route có hai rule (GET /quote, POST /reserve) cộng annotation retry: POST cũng bị retry.
- Timeout mỗi lần thử nhỏ hơn độ trễ bình thường: mọi lần thử đều hết giờ, tỉ lệ thành công tụt và tải nhân 4.
