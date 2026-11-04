---
title: Service FastAPI nhận ảnh, trả mask PNG và model_version
level: intermediate
services: []
files:
  - path: starter/service.py
    note: 3 hàm TODO
  - path: tests/test_service.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/01-mask-service -q
---

## Mục tiêu

Dựng service phân đoạn ảnh có hợp đồng rõ: nhận tệp ảnh, kiểm kích thước và định dạng trước khi chạm vào model, trả mask đúng kích thước ảnh gốc cùng phiên bản model đã sinh ra nó.

## Đề bài

FastAPI cơ bản và `/readyz` đã học ở module 07; bài này tập trung vào phần riêng của model ảnh. Model là tệp ONNX (input `pixel_values` `(N, 3, 64, 64)` đã chuẩn hoá, output logits `(N, 3, 64, 64)`, lớp 0 nền, 1 thú cưng, 2 viền). Hằng `INPUT_SIZE=64`, `MEAN`, `STD` (ImageNet), `MIN_SIDE=32`, `MAX_SIDE=1024`, `MAX_BYTES=10 MiB` đã có. Điền `starter/service.py`:

- `preprocess(image)`: `convert("RGB")` (ảnh xám, RGBA đều phải nhận), `resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)`, chia 255, trừ `MEAN` chia `STD` theo kênh, đổi sang NCHW; trả `float32` shape `(1, 3, 64, 64)`.
- `postprocess(logits, size)`: `argmax` theo trục lớp của phần tử đầu, `uint8`, ảnh mode `L`, `resize(size, Image.NEAREST)` với `size = (width, height)` của ảnh gốc; trả bytes PNG.
- `create_app(model_path, model_version)`: trả ứng dụng FastAPI.
  - `ort.InferenceSession` tạo **đúng một lần** trong lifespan (provider CPU), không tạo lại mỗi request.
  - `GET /healthz` trả `{"status": "ok", "model_version": <model_version>}`.
  - `POST /segment` nhận multipart, trường `file`. Thứ tự kiểm tra: lớn hơn `MAX_BYTES` byte trả **413**; PIL không mở được header trả **400**; cạnh ngắn nhỏ hơn `MIN_SIDE` hoặc cạnh dài lớn hơn `MAX_SIDE` trả **422** (biên `32` và `1024` hợp lệ); decode pixel lỗi (`image.load()`) trả **400**. Thiếu trường `file` là 422 mặc định của FastAPI.
  - Thành công: body là PNG mask (`media_type="image/png"`), kích thước bằng ảnh gốc, header `X-Model-Version: <model_version>`. Chạy `session.run` ngoài event loop (`run_in_threadpool`).

Test so mask trả về với mask tính lại từ cùng tệp ONNX **từng pixel**, và một test dùng model tí hon đã huấn luyện trên ảnh tổng hợp đòi IoU lớp thú cưng trên 0.8 khi ảnh bị đổi kích thước 200×150.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/11-deep-learning-serving/exercises/intermediate/01-mask-service -q` pass.
- Giải thích được vì sao kiểm kích thước **sau** khi decode header nhưng **trước** khi resize và chạy model.
- Nói được vì sao `model_version` nằm trong header của mọi response chứ không chỉ ở `/healthz`.

## Gợi ý

### Gợi ý 1

`Image.open(io.BytesIO(data))` chỉ đọc header, đủ để biết `image.size` (`(width, height)`). Kiểm kích thước xong mới `image.load()` (decode pixel) trong `try` để ảnh hỏng nửa chừng cũng thành 400.

### Gợi ý 2

`await file.read(MAX_BYTES + 1)` rồi so độ dài: không đọc cả tệp khổng lồ vào RAM chỉ để từ chối nó. `np.asarray(img, dtype=np.float32).transpose(2, 0, 1)[None]` cho NCHW.
