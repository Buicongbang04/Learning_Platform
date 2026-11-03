---
title: Service ETA có /readyz, warmup, timeout và kiểm tra đầu vào
level: basic
services: []
files:
  - path: starter/service.py
    note: Hoàn thiện create_app, đang sẵn sàng giả
  - path: tests/test_readyz.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/07-model-serving/exercises/basic/01-readyz-warmup -q
---

## Mục tiêu

Biến một service model "chạy được" thành service orchestrator dám giao traffic: báo sẵn sàng đúng lúc, từ chối đầu vào rác, không treo vì một request chậm.

## Đề bài

FastAPI cơ bản đã học ở [DS 14](../../../../../../data-science/modules/14-mlops-for-ds/README.md); bài này chỉ áp dụng phần vận hành. `starter/service.py` có `create_app(load_model, warmup_rows, predict_timeout)` đang nạp model đồng bộ rồi báo ready ngay. `load_model()` trả một đối tượng có `.version` và `.predict(rows) -> list[float]`, có thể chạy rất lâu hoặc lỗi. Sửa để:

- **Khởi động không bị chặn**: `load_model()` chạy trong một thread nền (daemon), `create_app` và lifespan trả về ngay.
- `GET /healthz` luôn 200 `{"status": "ok"}`, kể cả khi đang nạp hoặc nạp lỗi.
- `GET /readyz` trả 503 cho tới khi model nạp xong **và** warmup xong; warmup là gọi `model.predict(warmup_rows)` ít nhất 3 lần. Khi sẵn sàng trả 200 `{"ready": true, "model_version": <version>}`.
- Nạp lỗi: `/readyz` giữ 503, nội dung chứa thông điệp lỗi (vd. `RuntimeError: không thấy model`); `/healthz` vẫn 200.
- `POST /predict` body `{"rows": [[distance_km, hour, passengers], ...]}`: trả 503 khi chưa sẵn sàng; sẵn sàng thì trả `{"model_version": <version>, "predictions": [...]}`.
- Kiểm tra đầu vào, sai trả 422: số dòng từ 1 đến 100; mỗi dòng đúng 3 số hữu hạn (từ chối `NaN`, `Infinity`, `1e999`); `hour` trong 0..23.
- Timeout: nếu `model.predict` chạy quá `predict_timeout` giây thì trả 504 **ngay khi hết hạn** (dưới 0.7 giây với `predict_timeout=0.2`), không đợi model chạy xong. Chạy `model.predict` ngoài event loop (thread pool) để một request chậm không chặn các request khác.

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/07-model-serving/exercises/basic/01-readyz-warmup -q` pass.
- Giải thích được vì sao `/healthz` không nên kiểm tra model hay registry, còn `/readyz` thì phải.
- Nói được điều gì xảy ra với traffic nếu `/readyz` luôn trả 200.

## Gợi ý

### Gợi ý 1

Giữ trạng thái trong một dict (`ready`, `model`, `error`) mà thread nền ghi và các endpoint đọc. Lifespan chỉ khởi động thread rồi `yield`.

### Gợi ý 2

`asyncio.wait_for(run_in_threadpool(model.predict, rows), predict_timeout)` bắt `asyncio.TimeoutError` để trả 504. Số không hữu hạn: kiểm bằng `math.isfinite` sau khi pydantic đã parse.
