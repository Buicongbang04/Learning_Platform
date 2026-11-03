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

Rollback: `MlflowClient().set_registered_model_alias("eta", "champion", "<version cũ>")` rồi
`docker compose restart api`; kiểm bằng `curl -s 127.0.0.1:28080/healthz`.

Compose: `ETA_MODEL_DIR=$PWD/models ETA_MODEL_PATH=/models/model.joblib docker compose up -d --build --wait` (chạy bằng
tệp) hoặc bỏ hai biến để nạp `models:/eta@champion`. API join network `mlops_default` của stack và đổi `mlflow` thành
IP trước khi gọi (`ETA_MLFLOW_PIN_IP=1`) vì MLflow 3 trả 403 cho Host header lạ.
