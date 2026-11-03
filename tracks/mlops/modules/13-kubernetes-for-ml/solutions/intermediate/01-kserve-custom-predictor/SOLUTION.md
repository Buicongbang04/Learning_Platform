# Lời giải: InferenceService custom predictor

Xem `isvc.yaml`. Starter không đặt `MODEL_PATH`, nên service nạp giá trị mặc định `/models/eta-v1.joblib`. KServe thấy container mở cổng 8080 (probe TCP do KServe tự thêm), Deployment Available, InferenceService `READY True`: mọi tín hiệu xanh, nhưng phục vụ v1.

Sửa:

- Đặt `MODEL_PATH=/models/eta-v2.joblib` (và `MODEL_NAME=eta`) trong `env` của `kserve-container`.
- `readinessProbe` `httpGet /v1/models/eta`: pod chỉ vào Endpoints khi model đã nạp. Probe TCP chỉ nói cổng mở.
- Kiểm sau deploy bằng HTTP: `/v1/models/eta` trả `model_version`, và một `predict` mẫu so với giá trị kỳ vọng. Đây là bước nên có trong pipeline CD (smoke test), không chỉ trong bài.

## Custom container hay runtime có sẵn

| | Custom container | Runtime có sẵn (`predictor.model` + `storageUri`) |
| --- | --- | --- |
| Code serving | Của bạn (FastAPI, http.server...) | KServe sklearn/xgboost/mlserver... |
| Model đến pod | Đóng vào image, hoặc tự tải | storage-initializer tải `storageUri` (s3://, gs://, pvc://) vào `/mnt/models` |
| Tiền xử lý riêng | Tự do | Cần transformer hoặc custom runtime |
| Version model | Bạn tự báo (`model_version`) | Theo đường dẫn storageUri, phải tự ghi lại |

Dùng runtime có sẵn khi model là định dạng chuẩn và không có tiền xử lý; custom container khi service có logic riêng (feature, kiểm đầu vào) hoặc phải giữ đúng code đã test ở module trước.
