---
title: Dockerfile cho service dự đoán ETA bằng sklearn
level: basic
services: []
files:
  - path: starter/Dockerfile
    note: Viết toàn bộ, đang chỉ có FROM
  - path: tests/test_image.py
    note: Không sửa
  - path: tests/fixtures/service/app/serve.py
    note: Code service, chỉ đọc
  - path: tests/fixtures/service/requirements.txt
    note: Dependency đã ghim, chỉ đọc
run:
  - docker pull python:3.12.11-slim
  - uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/basic/01-dockerfile-predict-service -q
---

## Mục tiêu

Đóng gói một model sklearn nhỏ thành image chạy được, nhỏ, không chạy bằng root và tự báo sức khoẻ.

## Đề bài

Service dự đoán ETA (phút) cho chuyến taxi dựa trên `distance_km`, `hour`, `passengers`. Build context mà test dựng sẵn cho bạn gồm:

```text
requirements.txt        # numpy, scipy, scikit-learn, joblib: đã ghim
app/serve.py            # HTTP server, nghe cổng 8000, đọc model ở $MODEL_PATH (mặc định /models/model.joblib)
model.joblib            # model đã train (đóng vào image)
Dockerfile              # bản của bạn, chép từ starter/Dockerfile
```

Service có `GET /healthz` và `POST /predict` (body `{"rows": [[distance_km, hour, passengers], ...]}`). Viết `starter/Dockerfile` để:

- image build được từ context trên và chạy `python -m app.serve` từ thư mục chứa `app/`;
- model nằm ở `/models/model.joblib` trong image;
- base image ghim tag phiên bản đầy đủ (vd. `python:3.12.11-slim`), biến thể `slim` hoặc `alpine`, không dùng `latest`;
- `pip install` dùng `--no-cache-dir` (hoặc đặt `PIP_NO_CACHE_DIR`) để cache wheel không nằm lại trong layer;
- có `USER` không phải root làm lệnh cuối cùng, và container chạy với uid khác 0;
- có `HEALTHCHECK` (Docker báo healthy dựa trên `/healthz`; image slim không có `curl`);
- image nhỏ hơn **600 MB** (kích thước Docker báo).

## Tiêu chí đạt

- `uv run pytest tracks/mlops/modules/02-containers-for-ml/exercises/basic/01-dockerfile-predict-service -q` pass.
- `GET /healthz` trả 200 và `POST /predict` trả đúng giá trị model đã train.
- Giải thích được vì sao cài dependency trong một stage riêng rồi chép `/opt/venv` sang stage cuối lại giúp image nhỏ hơn.

## Gợi ý

### Gợi ý 1

Cài dependency vào một virtualenv ở stage đầu, stage cuối chỉ `COPY --from` virtualenv đó. Không bắt buộc, nhưng đó là cách làm quen thuộc.

### Gợi ý 2

`useradd --system` tạo user không cần home. `HEALTHCHECK` dạng exec dùng chính `python -c` với `urllib.request` vì image slim không có `curl`.
