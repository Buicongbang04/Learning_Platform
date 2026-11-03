# M02: Image training, image serving và stack Compose

## Mục tiêu

Package `eta` từ M01 mới chạy được trên máy bạn, với môi trường `uv` của cả repo (có cả torch, Spark, LangChain...).
Milestone này đóng gói hai việc thành hai image riêng, nhỏ, ghim phiên bản, chạy bằng user thường:

- **Image training** (`Dockerfile.train`): chạy `python -m eta.cli train` trên dữ liệu mount vào.
- **Image serving** (`Dockerfile.serve`): API FastAPI trả ETA cho một chuyến, nạp model từ tệp hoặc từ registry.

Rồi ghép API vào stack MLOps chung (`setup/mlops`: MLflow + MinIO + Postgres) bằng `compose.yaml`. Đây là bài tích hợp
sau [module 02](../../modules/02-containers-for-ml/README.md): multi-stage, cache layer cho dependency nặng, image nhỏ,
healthcheck, Compose nhiều dịch vụ.

Hai image tách nhau vì chúng có vòng đời khác nhau: image serving chạy 24/7, cần nhỏ, khởi động nhanh, ít bề mặt tấn
công; image training chạy theo lịch, cần `pyarrow` và `pandera` để đọc và kiểm dữ liệu. Image nào cũng **không** có
torch: model ETA là gradient boosting, kéo torch vào chỉ thêm 1–2 GB và vài lỗ hổng để quét.

## Việc cần làm

Mọi tệp nằm ở gốc `capstone/project/`; build context là chính thư mục đó. Test build image bằng `mlopskit.built_image`
(tên `mlops-ex-<uuid>:test`, xoá khi xong) và chạy container bằng `testkit.DockerLab` (giới hạn RAM, mount chỉ đọc,
cổng ngẫu nhiên trên `127.0.0.1`).

### 1. `eta.serve`: API

`eta/serve.py` có biến `app` là ứng dụng FastAPI:

| Endpoint | Hợp đồng |
| --- | --- |
| `GET /healthz` | 200 khi model đã nạp, body JSON có `model_version` (chuỗi). |
| `POST /predict` | Body `{"PULocationID": int, "DOLocationID": int, "pickup_datetime": "2019-01-15T08:30:00", "trip_distance": float}`, trả 200 với đúng `{"eta_s": float, "model_version": str}`, `eta_s > 0`. |
| `POST /predict` sai | Zone ngoài `1..265` (ví dụ `0`) hoặc thiếu trường: **422** (để Pydantic kiểm). |

- Nạp model **một lần** lúc khởi động (`lifespan`), không nạp mỗi request.
- Nguồn model: có biến `ETA_MODEL_PATH` (không rỗng) thì `joblib.load` tệp đó (Pipeline lưu bằng `--model-out` ở M01),
  `model_version` lấy từ `ETA_MODEL_VERSION` hoặc tên tệp. Không có thì nạp `models:/<ETA_MODEL_NAME, mặc định eta>@champion`
  từ MLflow (`MLFLOW_TRACKING_URI`); phần này được chấm ở M04.
- Feature dựng bằng **đúng hàm** của M01 (`pickup_datetime` đổi thành cột pickup rồi gọi hàm dựng feature chung).
- Log mỗi dự đoán một dòng JSON ra stderr: request id (nhận từ header `X-Request-ID` hoặc tự sinh, trả lại trong
  header), version model, feature, `eta_s`, độ trễ. M07 và M09 dựa vào log này.

### 2. `Dockerfile.serve`

- Base `python:3.12-slim` ghim bản vá (ví dụ `python:3.12.11-slim`). Multi-stage: stage đầu cài dependency vào một venv,
  stage cuối chỉ chép venv và `src/`.
- Cài **chỉ** thứ API cần: `fastapi`, `uvicorn`, `scikit-learn`, `pandas`, `numpy`, `joblib`, `mlflow-skinny` (nạp model
  từ registry, nhẹ hơn nhiều so với `mlflow` đủ), `pyyaml`. Ghim **toàn bộ** cây dependency trong một tệp
  `requirements-serve.txt`, cùng phiên bản với `uv.lock` của repo: model được pickle bằng scikit-learn 1.9.1 trên máy
  bạn, image chạy bản khác thì `joblib.load` có thể lỗi hoặc âm thầm đoán sai. Cách sinh tệp ghim:

```bash
uv export --frozen --no-hashes --no-emit-project > /tmp/repo-constraints.txt   # ở gốc repo
cd tracks/mlops/capstone/project
uv pip compile requirements-serve.in -c /tmp/repo-constraints.txt --python-version 3.12 \
  --python-platform x86_64-manylinux_2_28 -o requirements-serve.txt
```

- Chép `requirements-*.txt` và cài **trước** khi chép `src/`, để sửa code không làm mất cache layer cài dependency.
- `.dockerignore` chặn mọi thứ trừ `src/`, `requirements-*.txt`, `params.yaml` (đừng gửi `data/`, `models/`, notebook
  vào build context).
- Bẫy import: image serving không có `pyarrow` hay `pandera`. Nếu `serve.py` import `eta.features`, và `features.py`
  import `eta.data`, và `data.py` có `import pyarrow.parquet` ở đầu tệp, container chết ngay lúc khởi động với
  `ModuleNotFoundError`. Import thư viện chỉ training cần **bên trong** hàm dùng nó, hoặc tách module.
- Lắng nghe `0.0.0.0:8000`. Có `HEALTHCHECK` gọi `/healthz` (image không có `curl`, dùng `python -c "import urllib.request; ..."`).
- Chạy bằng user không phải root (`USER 10001` hoặc user tạo bằng `useradd`).

Test: chạy image với `ETA_MODEL_PATH=/models/model.joblib`, thư mục `/models` mount chỉ đọc (model train trong test
bằng `eta.train.train` rồi `joblib.dump`), giới hạn 512 MB RAM; chờ `/healthz`, gọi `/predict` hợp lệ và một request zone
`0`, kiểm `id -u` trong container khác `0`.

### 3. `Dockerfile.train`

- Cùng cách làm: multi-stage, `requirements-train.txt` ghim đủ (`pandas`, `pyarrow`, `scikit-learn`, `pandera`, `pyyaml`,
  `mlflow-skinny`), user không phải root, không torch.
- `python -m eta.cli ...` chạy được trong container (`PYTHONPATH` hoặc cài package vào venv). Gợi ý:
  `ENTRYPOINT ["python", "-m", "eta.cli"]`, `CMD ["train", "--config", "/app/params.yaml"]`, `ENV ETA_DATA_DIR=/data`.
- Commit được ghi vào image bằng `ARG GIT_COMMIT` → `ENV GIT_COMMIT` (M04 dùng làm lineage). Đặt `ARG` **sau** bước cài
  dependency: đổi commit mà đặt `ARG` ở đầu thì mất cache cả venv.

Test: chạy container với `--entrypoint sleep` (giữ container sống), mount chỉ đọc `/data` chứa một tệp
`yellow_tripdata_2019-01.parquet` giả và `config.yaml` (`data_dir: /data`), giới hạn 1 GB RAM, rồi `exec`:

- `python -m eta.cli train --config /data/config.yaml` exit 0, dòng cuối stdout là JSON có `mae`;
- `torch` không import được;
- `du -sxm /` (kích thước hệ thống tệp của image) dưới **1 536 MB**;
- `id -u` khác `0`.

Image phải có `sleep`, `du`, `id` (bản `python:3.12-slim` có sẵn; đừng dùng base distroless cho bài này).

### 4. `compose.yaml`: API trong stack MLOps

Bật stack chung trước (xem [README track](../README.md#bật-stack-mlops)):

```bash
docker compose -f setup/mlops/compose.yaml up -d --wait
```

`capstone/project/compose.yaml` có service tên **`api`**:

- Build từ `Dockerfile.serve`. Đừng đặt `image:` cố định (để `down --rmi local` dọn được image).
- Cổng `127.0.0.1:${ETA_API_PORT:-28080}:8000`. Test đặt `ETA_API_PORT=0` để Docker chọn cổng trống.
- Mount `${ETA_MODEL_DIR:-./models}` vào `/models` chỉ đọc, truyền `ETA_MODEL_PATH` (mặc định rỗng: nạp từ registry)
  và `ETA_MODEL_NAME` vào container.
- Join network của stack (mặc định `mlops_default`, khai `external: true`, tên đổi được qua biến `MLOPS_NETWORK`) và
  đặt `MLFLOW_TRACKING_URI` trong container trỏ tới MLflow của stack qua network đó (`http://mlflow:5000`).
- Có `healthcheck` (hoặc kế thừa `HEALTHCHECK` của image) để `docker compose up --wait` biết lúc nào API sẵn sàng.
- Nên thêm: `read_only: true` + `tmpfs: /tmp`, `cap_drop: [ALL]`, `no-new-privileges`, `mem_limit`.

Test (skip nếu stack chưa bật): `docker compose up --wait` project tạm với `ETA_MODEL_DIR=<thư mục model test>`,
`ETA_MODEL_PATH=/models/model.joblib`, gọi `/healthz`, `/predict` qua cổng host, rồi `exec` vào `api` gọi
`$MLFLOW_TRACKING_URI/health` phải thành công.

**Lỗi hay gặp: 403 `Invalid Host header`.** MLflow 3 chặn request có Host header lạ (chống DNS rebinding); mặc định chỉ
nhận `localhost` và IP. `http://mlflow:5000/health` vẫn 200 nhưng mọi API registry trả 403. Hai cách sửa: thêm
`--allowed-hosts mlflow,mlflow:5000,...` vào lệnh server của stack (đúng nhất, nhưng đó là hạ tầng chung), hoặc phía
client đổi tên host thành IP trước khi gọi (bản tham chiếu làm vậy khi có `ETA_MLFLOW_PIN_IP=1`). Ghi lựa chọn của bạn
vào README.

Chạy test:

```bash
uv run pytest tracks/mlops/capstone/project/tests -q -rs -k m02
```

Lần build đầu tải khoảng 300 MB wheel (vài phút tuỳ mạng); các lần sau dùng cache. Trên máy dùng chung, thêm
`nice -n 15` trước `uv run`.

## Kết quả nộp

- `capstone/project/src/eta/serve.py`.
- `capstone/project/Dockerfile.serve`, `Dockerfile.train`, `.dockerignore`, `requirements-serve.txt`,
  `requirements-train.txt` (kèm tệp `.in` nếu bạn sinh bằng `uv pip compile`).
- `capstone/project/compose.yaml`.
- Mục "Container" trong `capstone/project/README.md`: kích thước hai image (`docker image ls`), lệnh build/chạy, cách
  bạn xử lý Host header của MLflow.

## Tiêu chí đạt

- [ ] `uv run pytest tracks/mlops/capstone/project/tests -q -rs -k m02` pass, không skip (stack đã bật).
- [ ] Hai image multi-stage, base ghim bản vá, dependency ghim đủ cây, khớp `uv.lock`; không torch.
- [ ] Image training dưới 1,5 GB; cả hai chạy bằng user không phải root.
- [ ] API nạp model một lần, kiểm input (422), dựng feature bằng hàm chung của M01, log JSON mỗi dự đoán.
- [ ] Compose: API join network stack, cổng chỉ bind `127.0.0.1`, có healthcheck, `up --wait` thành công.
- [ ] (Tự đánh giá) Sửa một dòng trong `src/` rồi build lại: chỉ layer `COPY src/` chạy lại (xem log `CACHED`).
- [ ] (Tự đánh giá) `trivy image` cho hai image, ghi số lỗ hổng HIGH/CRITICAL vào README.
