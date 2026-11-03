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

## Orchestration (M05)

Ba flow Prefect trong `eta.flows`, chạy không cần server Prefect (Prefect tự bật API tạm trong tiến trình):

```bash
make replay-data
PYTHONPATH=src uv run --project ../../../../.. python -c \
  "from eta.flows import replay_flow; print(replay_flow('2019-02', '2019-06', 'params.replay.yaml', 'reports/replay'))"
```

- `train_flow(config_path, months)`: train và đăng ký, trả version, không promote.
- `batch_score_flow(month, config_path, out_dir)`: chấm cả tháng bằng `champion`, ghi `predictions_<month>.parquet`.
- `replay_flow(start, end, config_path, out_dir)`: đồng hồ qua từng tháng; chưa có champion thì train trên `start - 1`;
  MAE chỉ tính cho tháng có nhãn đã công bố tại `as_of = end`, ghi `replay.json`.

**Khoá cache** của task train (`_train_key`): `data_version` (sha256 nội dung các tệp tháng và bảng tốc độ), `months`,
`sample_rows`, `seed`, `model_params`, `mlflow_uri` (sqlite tương đối đã quy về đường dẫn tuyệt đối theo thư mục config),
`model_name`, `speed_table`, và `code_version()` (sha256 các tệp `data.py`, `features.py`, `train.py`, `labels.py`,
`zone_features.py`, `registry.py`, `flows.py`). Cache trúng thì `train_flow` vẫn hỏi registry: version không còn hoặc tag
`data_version` lệch thì log `stale_cache` và train lại với `refresh_cache=True`. Vì vậy xoá `data/replay-mlflow.db` rồi
`make replay` lại vẫn ra registry đúng.

**Xoá cache** khi muốn train lại có chủ đích: xoá thư mục kết quả Prefect (`PREFECT_LOCAL_STORAGE_PATH`, mặc định
`~/.prefect/storage`), hoặc đổi khoá (đổi tham số trong config, sửa code train).

**Deployment có lịch** (ví dụ, không chạy trong test): một tiến trình phục vụ flow theo cron, đầu mỗi tháng lúc 03:00.

```python
from eta.flows import train_flow

train_flow.serve(name="eta-monthly", cron="0 3 1 * *", parameters={"config_path": "params.yaml", "months": ["2019-01"]})
```

Lịch chỉ **train và đăng ký**; không promote. Train mù theo lịch tốn tài nguyên và, tệ hơn, nếu promote tự động thì
một tháng dữ liệu lạ (COVID 2020-03) đẩy thẳng model xấu ra production. Promote vẫn qua cổng `eta.cli promote` (M04,
CT ở M08), còn quyết định retrain dựa trên drift và MAE đã có nhãn (M10). Cache làm lần chạy lịch trùng dữ liệu gần như
miễn phí.

## Feature tốc độ, canary và shadow (M06–M07)

Feast (M06) chạy trong container `mlops-feast:0.67.0`, Redis bật bằng `--profile feast` của stack; ghi
`feature_repo/data/zone_hour_speed.parquet` bằng `eta.zone_features.zone_hour_speed`, rồi `feast apply` và
`feast materialize` qua `mlopskit.feast_run(..., network="mlops_default")`.

Canary và shadow (M07): `ETA_CANARY_WEIGHT=0.1` (10% request cho alias `challenger`), `ETA_SHADOW=1` (challenger chấm sau
response, chỉ ghi log), `ETA_PREDICTION_LOG=/tmp/predictions.jsonl`. Tải thử: `loadtest/eta.js` với `TARGET`.

## CI/CD (M08)

```text
push src/** ──► ci.yml: lint + test ─► build (dist/eta.pyz)
push params.yaml, dvc.lock, src/eta/train.py ──► ct.yml: validate ─► train ─► gate (eta.cli promote) ─► announce
                                                                                    │ exit 0: alias champion
workflow_dispatch(model_version) ──► cd.yml: verify (eta.cli champion --expect) ─► deploy (compose + /admin/reload)
```

| Workflow | Trigger | Jobs | Thời gian act (máy tham chiếu) |
| --- | --- | --- | --- |
| `ci.yml` | `push`, `pull_request` vào `src/**`, `tests_own/**`, `pyproject.toml`, `requirements-*.txt`, `Dockerfile.*`, chính nó | lint, test → build | 12 s (test hỏng rồi xanh) |
| `ct.yml` | `push` lên `main` vào `params.yaml`, `dvc.lock`, `src/eta/train.py`; `workflow_dispatch` | validate → train → gate → announce | 28 s (champion không thể thắng), 35 s (registry trống) |
| `cd.yml` | `workflow_dispatch` với `model_version` | verify → deploy | 19 s (sai rồi đúng version) |

Chỗ nối: **CI → CT** là cổng promotion. CI chỉ bảo đảm code đúng; CT train trên code đã qua CI rồi để `eta.cli promote`
(M04) quyết định, exit 3 khi từ chối làm job `gate` đỏ và `announce` không chạy. **CT → CD** là alias `champion`: CD không
đọc output của CT mà hỏi registry, nên chỉ version đang mang `champion` mới deploy được. `ETA_ADMIN_TOKEN` lấy từ secret
ở mức job `deploy` để cả `docker compose` lẫn `curl /admin/reload` dùng cùng token.

Chạy CI bằng act: `make act-ci` (lần đầu runner cài `requirements-ci.txt` vào `.ci-deps`, cần mạng; `--user` theo uid của
bạn để tệp ghi qua `--bind` không thuộc root).

## Monitoring (M09)

`/metrics` có `eta_requests_total{status,variant}`, `eta_request_duration_seconds`, `eta_prediction_seconds`,
`eta_model_info{version,variant}`. `make monitoring` bật Prometheus (`127.0.0.1:29190`) và Grafana (`127.0.0.1:23100`,
dashboard ETA được provision) bên cạnh API; Prometheus ở cả network `mlops` của stack để gửi alert tới
`alertmanager:9093`. Kiểm rule bằng `promtool test rules monitoring/rules/eta.rules.test.yml`.

Dashboard (7 panel): request theo status, tỉ lệ 5xx, model đang chạy, p50/p95 thời gian xử lý theo variant, fallback
canary và lỗi shadow, trung vị ETA theo variant, phân phối ETA. Ảnh chụp khi chạy k6 của M07
(`loadtest/eta.js`) là phần bạn tự chụp trên máy mình; bản tham chiếu không kèm ảnh.

| Alert | Điều kiện | `for` | Vì sao ngưỡng này |
| --- | --- | --- | --- |
| `EtaHighErrorRate` | 5xx / tổng request trong 5 phút > 5% | 5m | Lỗi 5xx là lỗi của mình; 5% đủ cao để không bắn vì vài request lẻ, 5 phút lọc nháy do restart |
| `EtaHighLatencyP95` | p95 `eta_request_duration_seconds` > 0.3 s | 10m | Dự đoán thường vài chục ms; 0.3 s là lúc người gọi bắt đầu thấy chậm, 10 phút bỏ qua đợt GC hay reload |
| `EtaMetricsAbsent` | `absent(eta_model_info{job="eta-api"})` | 5m | Gauge có ngay khi nạp model, khác counter chỉ có series sau request đầu; mất nó là API chết hoặc không scrape được |
| `EtaPredictionShift` | \|trung vị ETA 1h / cùng giờ 7 ngày trước - 1\| > 30% (bỏ `shadow`) | 1h | Tín hiệu proxy cho drift khi nhãn chưa về; so cùng giờ tuần trước để không bắn theo nhịp ngày |

Tỉ lệ lỗi 0/0 không bắn alert: không có traffic thì `sum(rate(5xx)) / sum(rate(all))` là NaN, và `NaN > 0.05` là false.
Không thêm `or vector(0)` vào mẫu số: đó mới là chỗ sinh alert giả hay che lỗi. Mất traffic hẳn do `EtaMetricsAbsent` lo.

## Drift và sự cố (M10)

`make replay` symlink 2019 và 2020 vào `data/replay`, rồi `eta.cli replay` với `params.replay.yaml` (champion train trên
2019-06, mẫu 50 000 chuyến/tháng, `as_of = 2020-06`) ghi `reports/replay/summary.parquet`. `make experiments` chạy các thí
nghiệm hỗ trợ quyết định. Quyết định ở `reports/decisions/`, runbook ở `docs/runbook.md`, postmortem ở
`docs/postmortem-covid.md`.

| Tháng | PSI `trip_distance` | PSI giờ đón | PSI `eta_s` | MAE (s) | bias (s) |
| --- | --- | --- | --- | --- | --- |
| 2019-07 | 0.0006 | 0.0018 | 0.0016 | 194.2 | +41.5 |
| 2019-08 | 0.0015 | 0.0012 | 0.0042 | 192.6 | +72.6 |
| 2019-09 | 0.0006 | 0.0019 | 0.0003 | 201.5 | -9.8 |
| 2019-10 | 0.0010 | 0.0045 | 0.0002 | 195.7 | -8.9 |
| 2019-11 | 0.0019 | 0.0012 | 0.0010 | 196.4 | -4.9 |
| 2019-12 | 0.0023 | 0.0022 | 0.0019 | 212.3 | -21.8 |
| 2020-01 | 0.0041 | 0.0055 | 0.0009 | 199.1 | +102.7 |
| 2020-02 | 0.0062 | 0.0044 | 0.0026 | 181.1 | +65.1 |
| 2020-03 | 0.0047 | 0.0147 | 0.0023 | 207.0 | +103.9 |
| 2020-04 | 0.0161 | 0.1772 | 0.0157 | 371.8 | +340.6 |
| 2020-05 | 0.0448 | 0.1071 | 0.0483 | 362.2 | +321.2 |
| 2020-06 | 0.0184 | 0.1113 | 0.0321 | chưa có nhãn | |

| Tháng | Quyết định | `as_of` | Lý do một dòng |
| --- | --- | --- | --- |
| 2019-12 | `keep` | 2020-01 | MAE 212.3 s nằm trong dải 192.6–212.3 s của nửa sau 2019, PSI nhỏ; train lại trên 2019-11 chỉ được 2% |
| 2020-03 | `retrain` | 2020-04 | Cả tháng còn trong dải nhưng lát từ 2020-03-12 cho champion 283.6 s, challenger train đầu tháng 3 đạt 240.8 s (-15%); rollback vô nghĩa vì mọi version đều trước COVID |

Chi tiết số, thí nghiệm và rubric ở `../SOLUTION.md`.

## Cloud (M11, tuỳ chọn)

AWS, vùng `us-east-1`, Terraform trong `cloud/`: bucket S3 chứa `models/model.joblib` (chặn public, mã hoá AES256), một
Lambda 128 MB trả `/healthz` (version model và vị trí artifact, không nạp model), log group giữ 3 ngày, budget 1 USD/tháng
có hai cảnh báo email. Mọi tài nguyên mang `tags = local.tags` với `project = "eta-mlops"`; IAM role nằm dưới path
`/eta-mlops/`. Chi phí ước tính 0 USD trong free tier với lưu lượng thử tay.

```bash
cd cloud
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
curl "$(terraform output -raw health_url)"
terraform destroy
bash teardown.sh --dry-run
```

Budget và quy trình dọn ở `cloud/budget.md`.

## Kubernetes (M12)

Cluster kind `mlops` (`bash setup/mlops/kind/up.sh`). Serving là InferenceService `eta` (KServe RawDeployment, predictor
custom container chạy image `Dockerfile.serve` không sửa); model vào pod bằng image `k8s/Dockerfile.model` (busybox +
`model.joblib`, khoảng 3 MB) qua hai init container `model-champion`, `model-challenger` chép vào `emptyDir`. Biến release
(`ETA_MODEL_VERSION`, `ETA_CHALLENGER_VERSION`, `ETA_CANARY_WEIGHT`) nằm trong `env` của container nên đổi biến nào cũng
sinh pod mới; ConfigMap `eta-config` chỉ giữ đường dẫn cố định, Secret `eta-admin` giữ token.

```bash
export ETA_SERVE_IMAGE=eta-serve:dev ETA_CHAMPION_IMAGE=eta-model:v1 ETA_CHAMPION_VERSION=v1 \
       ETA_CHALLENGER_IMAGE=eta-model:v2 ETA_CHALLENGER_VERSION=v2 ETA_CANARY_WEIGHT=0.25 ETA_ADMIN_TOKEN=$(openssl rand -hex 16)
envsubst < k8s/eta.yaml | kubectl --context kind-mlops -n eta apply -f -
kubectl --context kind-mlops -n eta rollout status deployment/eta-predictor
```

Rollout đo được (laptop, image đã nạp): apply tới `/readyz` báo version mới khoảng 5–7 giây; bốn release của test (ổn định,
25%, 50%, rollback) cộng 160 request mất khoảng 26 giây. Rollback là apply lại bộ biến cũ.

Training: `argo/train-workflow.yaml` (DAG `validate → train → gate`, parameter `month`, `champion-metrics`, dữ liệu từ
ConfigMap `eta-train-data`, artifact `sample`, `model`, `metrics` qua MinIO của Argo). Một Workflow trên 1 500 chuyến xong
trong khoảng 30 giây; `gate` từ chối thoát mã 3 và Workflow Failed ở đúng bước đó.

## Đánh giá M13

`make assessment` dựng `data/assessment/` (tháng lạ 2019-10 và ba tháng thật quanh nó), chạy `prepare`, `validate` (exit 1
là kết quả mong đợi) và `replay` 2019-09..2019-11 với `params.assessment.yaml`. Chẩn đoán ở
`reports/assessment/diagnosis.yaml`, báo cáo ở `docs/assessment.md`. Đây là đáp án của bài đánh giá: chỉ đọc sau khi
đã nộp bài của mình.
