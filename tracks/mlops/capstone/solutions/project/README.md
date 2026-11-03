# Dịch vụ ETA: bản tham chiếu

Cây thư mục giống `capstone/project/`. Quyết định và số đo ở [`../SOLUTION.md`](../SOLUTION.md).

## Vận hành

Từ thư mục này (`uv` dùng môi trường của repo):

```bash
make train                     # MAE 2019-01 khoảng 148 s, model ở models/model.joblib
make serve                     # API ở http://127.0.0.1:28080 với model vừa train
make repro                     # dvc repro: prepare → validate → train (cần `uv run dvc init --subdir` một lần)
make images                    # eta-train:dev, eta-api:dev
make register                  # cần stack MLOps; in model_version
PYTHONPATH=src uv run --project ../../../../.. python -m eta.cli promote --config params.yaml --version <N>
```

Biến môi trường khi làm với stack: `MLFLOW_TRACKING_URI=http://127.0.0.1:25000`,
`MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false`.

| Lệnh | Exit |
| --- | --- |
| `eta.cli train` | 0 xong; khác 0 khi lỗi config hay dữ liệu |
| `eta.cli validate` | 0 hợp lệ, 1 vi phạm schema |
| `eta.cli promote` | 0 đã promote, 3 bị cổng chặn |

Rollback (M07, không restart): `MlflowClient().set_registered_model_alias("eta", "champion", "<version cũ>")` rồi
`curl -s -X POST 127.0.0.1:28080/admin/reload` (thêm `-H "X-Admin-Token: $ETA_ADMIN_TOKEN"` nếu đặt token); kiểm bằng
`curl -s 127.0.0.1:28080/readyz`.

Compose: `ETA_MODEL_DIR=$PWD/models ETA_MODEL_PATH=/models/model.joblib docker compose up -d --build --wait` (chạy bằng
tệp) hoặc bỏ hai biến để nạp `models:/eta@champion`. API join network `mlops_default` của stack và gọi
`http://mlflow:5000` (stack khai `--allowed-hosts` cho tên `mlflow`).

Flow Prefect (M05), không cần server Prefect:

```bash
PYTHONPATH=src uv run --project ../../../../.. python -c \
  "from eta.flows import replay_flow; print(replay_flow('2019-02', '2019-06', 'params.yaml', 'reports/replay'))"
```

Feast (M06) chạy trong container `mlops-feast:0.67.0`, Redis bật bằng `--profile feast` của stack; ghi
`feature_repo/data/zone_hour_speed.parquet` bằng `eta.zone_features.zone_hour_speed`, rồi `feast apply` và
`feast materialize` qua `mlopskit.feast_run(..., network="mlops_default")`.

Canary và shadow (M07): `ETA_CANARY_WEIGHT=0.1` (10% request cho alias `challenger`), `ETA_SHADOW=1` (challenger chấm sau
response, chỉ ghi log), `ETA_PREDICTION_LOG=/tmp/predictions.jsonl`. Tải thử: `loadtest/eta.js` với `TARGET`.
