---
title: Sự cố - service phân đoạn ngừng trả lời sau giờ cao điểm
level: intermediate
services: []
files:
  - path: starter/service.py
    note: Service đang chạy trên production, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/device.py
    note: Card production mô phỏng trên CPU, chỉ đọc
  - path: tests/fixtures/service_incident.py
    note: Bản gốc lúc sự cố, chỉ đọc
run:
  - uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/04-incident-service-dies-under-load -q
---

## Mục tiêu

Chẩn đoán một sự cố của service model ảnh chạy trên GPU từ triệu chứng, tái hiện được trên máy không có GPU, sửa tối thiểu và có test chứng minh.

## Đề bài

`pet-seg` là service phân đoạn ảnh thú cưng chạy trên một card RTX 3050 4 GB. Tối thứ Sáu, app di động chạy chiến dịch "khoe thú cưng", rồi:

- Trong ngày bình thường service trả lời ổn định hàng tuần liền, p95 khoảng 40 ms.
- Khoảng 20:05, ngay khi push notification gửi đi, hàng loạt request nhận **504** sau 2 giây. Từ đó **mọi** request `/segment` đều 504, kể cả khi lưu lượng đã về mức bình thường.
- `GET /healthz` vẫn 200 suốt thời gian đó nên orchestrator không restart pod. Process vẫn sống, CPU gần 0%, GPU utilization 0%.
- Restart pod bằng tay thì service chạy lại bình thường, cho tới đợt push tiếp theo.
- Máy dev không có GPU; đội đã dựng `tests/fixtures/device.py` mô phỏng card production trên CPU (suy luận vẫn chạy thật bằng ONNX Runtime, API đặt tên theo `torch.cuda`). Gửi tuần tự hàng trăm request vào bản mô phỏng không thấy lỗi gì.

`starter/service.py` là mã đang chạy (bản gốc lúc sự cố ở `tests/fixtures/service_incident.py`). `create_app(model_path, device, model_version)` nhận đối tượng `device` có `run(session, pixel_values)`, `mem_get_info()`, `max_memory_allocated()`, `reset_peak_memory_stats()`; test truyền bản mô phỏng từ `tests/fixtures/device.py` (một số test dùng card nhỏ hơn, 2 GB).

Hợp đồng không đổi: `POST /segment` (multipart, trường `file`) trả mask PNG đúng kích thước ảnh gốc, header `X-Model-Version`, mask **đúng từng pixel** như hiện tại; `GET /healthz` như cũ; request chờ quá `REQUEST_TIMEOUT_S` trả 504. Service gom các request đến gần nhau để chạy chung một lần trên card: giữ nguyên hành vi đó (test kiểm có lần chạy nhiều hơn một ảnh). Lỗi khi chạy model trả **500 ngay** cho các request bị ảnh hưởng, không để chúng chờ tới 504, và request sau đó phải 200.

Chỉ sửa `starter/service.py`. Một test chạy bản lúc sự cố và đòi nó tái hiện triệu chứng. Test của bạn: hai đợt 32 request đồng thời (24 trên card 2 GB) đều 200 với mask đúng của từng request, request sau đợt vẫn 200.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/04-incident-service-dies-under-load -q` pass.
- Chỉ ra được hai nguyên nhân tách biệt: vì sao service gặp lỗi khi có đợt request, và vì sao sau lỗi đó nó không bao giờ tự hồi phục.
- Đề xuất ít nhất hai tín hiệu giám sát mà nếu có thì đã phát hiện sự cố trong vài giây, và một thay đổi cho `/healthz` hoặc `/readyz`.

## Gợi ý

### Gợi ý 1

Tái hiện trước khi đọc mã: gửi 5 request tuần tự, rồi 48 request cùng lúc (`ThreadPoolExecutor` với `TestClient`), rồi 1 request nữa. Log hiện tại không in gì; tìm cho ra lỗi **đầu tiên** xảy ra ở đâu và nó là gì.

### Gợi ý 2

So từng lần chạy model trong đợt request đồng thời với lúc gửi tuần tự: input của lần chạy đó khác gì, và card còn bao nhiêu tài nguyên cho nó.
