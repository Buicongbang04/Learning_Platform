---
title: Serve model review xấu bằng FastAPI
level: basic
services: []
files:
  - path: starter/service.py
    note: Ràng buộc schema + create_app
  - path: tests/test_service.py
    note: Không sửa
run:
  - uv run pytest tracks/data-science/modules/14-mlops-for-ds/exercises/basic/03-fastapi-serving -q
---

## Mục tiêu

Viết một API chấm điểm online đúng kiểu production ở mức tối thiểu: schema đầu vào có ràng buộc
(dữ liệu sai bị chặn **trước** khi tới model), chấm cả batch trong một lần gọi model, trả kèm phiên
bản model, và test được hoàn toàn bằng `TestClient` mà không cần chạy server.

## Đề bài

Model là pipeline scikit-learn dự đoán xác suất đơn Olist bị review xấu (1–2 sao), chấm ngay khi
đơn vừa giao xong. Trong `starter/service.py`:

1. Thêm ràng buộc vào `OrderFeatures`: `promised_days`, `delivery_days`, `price`, `freight`,
   `approve_hours`, `payment_installments` không âm; `n_items`, `n_sellers` ít nhất 1;
   `freight_ratio` trong [0, 1]; `customer_state` đúng 2 ký tự; `payment_type` là một trong
   `credit_card`, `boleto`, `voucher`, `debit_card`, `not_defined`, `missing`.
   `approve_hours` và `payment_installments` được phép `null`.
2. `PredictRequest.orders` có từ 1 tới 1000 đơn.
3. `create_app(model, model_version, threshold=0.5) -> FastAPI` với hai route:
   - `GET /health` trả `{"status": "ok", "model_version": ...}`.
   - `POST /predict` nhận `PredictRequest`, trả `{"model_version", "predictions": [{"order_id",
     "score", "high_risk"}]}` theo đúng thứ tự đầu vào; `score` là `predict_proba(X)[:, 1]`,
     `high_risk = score >= threshold`.
   - Gọi `model.predict_proba` **một lần** cho cả request, với DataFrame có đúng các cột
     `FEATURES` theo thứ tự (không có `order_id`); `null` thành NaN.

`create_app` nhận model làm tham số thay vì tự đọc từ đĩa: test truyền vào một model giả để kiểm
cách gọi, và production truyền model đọc từ registry lúc khởi động.

## Tiêu chí đạt

- `/health` đúng; `/predict` cho score khớp `pipeline.predict_proba` tới 1e-9, giữ thứ tự đơn.
- Ngưỡng `high_risk` đổi được khi tạo app.
- Model được gọi đúng một lần mỗi request, với DataFrame đúng cột và thứ tự.
- `null` ở trường tuỳ chọn thành NaN, pipeline vẫn chấm được.
- Giá âm, `n_items = 0`, `freight_ratio = 1.5`, `payment_type` lạ, bang dài hơn 2 ký tự, thiếu
  trường, batch rỗng hoặc trên 1000 đơn: trả 422 và model **không** được gọi.

## Gợi ý

### Gợi ý 1

`price: float = Field(ge=0)`, `payment_type: Literal["credit_card", ...]`,
`orders: list[OrderFeatures] = Field(min_length=1, max_length=1000)`. FastAPI tự trả 422 kèm
mô tả lỗi khi body không khớp schema; bạn không cần tự viết kiểm tra.

### Gợi ý 2

`pd.DataFrame([o.model_dump() for o in request.orders])` rồi chọn `X[FEATURES]`. Với cột chỉ toàn
`None`, pandas tạo cột kiểu `object` chứa `None` chứ không phải NaN: ép các cột số về `float`.
Khai báo route bên trong `create_app` (closure) để mỗi app dùng đúng model của nó.
