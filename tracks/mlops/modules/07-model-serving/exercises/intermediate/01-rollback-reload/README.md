---
title: Rollback bằng đổi alias và reload, không restart
level: intermediate
services: []
files:
  - path: starter/service.py
    note: Thêm POST /admin/reload
  - path: tests/test_reload.py
    note: Không sửa, dựng registry MLflow SQLite trong tmp
run:
  - uv run pytest tracks/mlops/modules/07-model-serving/exercises/intermediate/01-rollback-reload -q
---

## Mục tiêu

Làm cho "rollback" thành một thao tác vài giây: đổi alias trong registry, gọi một endpoint, service đổi model mà không rebuild, không restart, không rơi request.

## Đề bài

`starter/service.py` có `create_app(tracking_uri, model_name, admin_token, alias="champion")`: phân giải alias ra số version lúc khởi động, nạp model bằng `mlflow.pyfunc.load_model(f"models:/{model_name}/{version}")` và phục vụ `POST /predict` (`{"rows": [[...]]}` trả `{"model_version": <int>, "predictions": [...]}`). Nó chưa có cách đổi model khi alias đổi. Thêm `POST /admin/reload`:

- Header `X-Admin-Token` thiếu, rỗng hoặc sai: trả 401 và không làm gì.
- Phân giải lại alias. Nếu version không đổi: trả 200 `{"changed": false, "previous_version": v, "model_version": v}` và **không nạp lại model** (test theo dõi lời gọi `mlflow.pyfunc.load_model`; hãy gọi qua `mlflow.pyfunc.load_model`, không import trực tiếp tên hàm).
- Version đổi: nạp model mới **trước**, rồi mới đổi sang nó; trả 200 `{"changed": true, "previous_version": cũ, "model_version": mới}`.
- Giữa hai lần reload, `/predict` phục vụ đúng version đã nạp, kể cả khi alias đã đổi trong registry (không tra alias mỗi request).
- Alias bị xoá hoặc nạp lỗi: trả 409, thông điệp nêu version đang giữ, và `/predict` vẫn phục vụ model cũ.
- Request `/predict` chạy song song với reload (nạp mất 0.4 giây) không được lỗi, và `model_version` luôn khớp với dự đoán đi kèm (không có response lẫn version mới với dự đoán cũ).
- `create_app` ném `LookupError` khi alias không tồn tại lúc khởi động (đã có trong starter, giữ nguyên).

Tình huống trong test: version 2 (alias `champion`) cho 999 giây, version 1 cho 620 giây; rollback là đổi `champion` về version 1.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/07-model-serving/exercises/intermediate/01-rollback-reload -q` pass.
- Mô tả được chuỗi lệnh rollback lúc 3 giờ sáng và bạn sẽ thấy gì trong response để biết nó đã xong.
- Nói được vì sao endpoint này không được mở ra Internet, và hai cách bảo vệ khác ngoài token.

## Gợi ý

### Gợi ý 1

Lưu `(version, model)` thành **một tuple** trong state và đổi cả tuple trong một phép gán; `/predict` đọc tuple một lần ở đầu hàm. Như vậy không bao giờ có version của bản này đi với model của bản kia.

### Gợi ý 2

Một `threading.Lock` quanh reload để hai lần reload đồng thời không nạp hai lần. Lỗi thì ném `HTTPException(409, ...)` trước khi chạm vào state.
