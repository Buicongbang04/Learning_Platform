# MLOps track Phase 2: module 05–10 + capstone m05–m10 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm module 05–10 (training pipeline, feature store, serving, CI/CD, monitoring, drift và sự cố) và capstone ETA m05–m10 (Prefect, Feast, shadow/canary, `act`, Prometheus/Grafana, phát lại 2019 → 2020 và quyết định có số liệu).

**Architecture:** Giữ nguyên kiến trúc Giai đoạn 1. Helper mới vào `mlopskit.py` (dựng trên `testkit.DockerLab`). Dịch vụ mới vào `setup/mlops/compose.yaml` dưới **profile** (`monitoring`, `feast`) để stack lõi không nặng thêm. Feast chạy **trong container** (vì `feast[redis]` hạ pandas 3.1 → 2.3.3). Capstone mở rộng package `eta` sẵn có; `project/` là starter, `solutions/project/` là lời giải tham chiếu.

**Tech Stack:** Python 3.12, uv, pytest; Prefect 3.9 (đã có trong env), MLflow 3.17.1, scikit-learn; **mới trong env:** `evidently==0.7.23`; **trong container:** `feast[redis]==0.67.0`, Redis, Prometheus `v3.5.0`, Alertmanager, Grafana `12.1.0`, k6 `grafana/k6:1.8.1` (image đã có trên máy); **binary:** `act` (bản phát hành ≥2 tuần tuổi, **không** dùng v0.2.95 ra ngày 2026-11-03).

**Spec:** `docs/superpowers/specs/2026-11-03-mlops-track-design.md` (mục 4.1 hàng 05–10, mục 5, mục 7 m05–m10). Plan Giai đoạn 1: `docs/superpowers/plans/2026-11-03-mlops-phase1.md` — **mọi Global Constraints của plan đó vẫn áp dụng**; dưới đây chỉ ghi phần thêm.

## Global Constraints

- Toàn bộ Global Constraints của plan Giai đoạn 1 (worktree, tệp cấm sửa, tiếng Việt, ≤5 phút CPU/bài, 5–8 phần `## `, `## 0. Cài đặt`, interview ≥12 câu, 3B/2–3I/2A, Advanced chỉ `SOLUTION.md`, không `docker` trần, dependency ≥2 tuần tuổi, `nice -n 15`, không comment inline, không Co-Authored-By, track khác giữ nguyên hành vi).
- **Bài học Giai đoạn 1, bắt buộc:** giá trị `text` trong quiz YAML luôn đặt trong dấu nháy; mọi luật mà test ép phải được nói trong README bài; bài sự cố: README chỉ tả triệu chứng, lý thuyết/interview/quiz **không** lộ nguyên nhân; không gọi docker trá hình (cần gì thì thêm helper công khai vào `mlopskit`).
- Từ module 07 trở đi mỗi module có ≥1 **bài sự cố cố ý** có ca hồi quy chứng minh starter tái hiện triệu chứng.
- **Feast không vào môi trường mặc định.** Mọi lệnh Feast chạy trong image `mlops-feast` (Task 1) qua `mlopskit.feast_run`. Code Python của người học chạy ở host chỉ dùng pandas để tính feature; phần đăng ký/materialize/lấy feature chạy trong container.
- **`act` không cần mạng và GitHub:** workflow bài tập chỉ dùng bước `run:` (không `uses:` action từ xa), chạy với runner image nhỏ build tại chỗ (`mlopskit.ACT_RUNNER`), `--bind` thư mục làm việc. Test skip khi thiếu `act`.
- **Prefect không cần server:** test dùng `prefect.testing.utilities.prefect_test_harness()` hoặc `PREFECT_HOME` trong `tmp_path`; không để lại tiến trình server.
- Cổng mới (mặc định, override qua `setup/.env`, bind `127.0.0.1`): Prometheus `MLOPS_PROMETHEUS_PORT=29090`, Alertmanager `MLOPS_ALERTMANAGER_PORT=29093`, Grafana `MLOPS_GRAFANA_PORT=23000`, Redis cho Feast `MLOPS_REDIS_PORT=26390`. Đã kiểm `ss -ltn` ngày 2026-11-03: không trùng.
- Dữ liệu thật cho số đếm/số đo: đọc qua `mlopskit.real_month(dataset, month)` có kiểm sha256 (Task 1), không đọc thẳng đường dẫn.

## Review Focus

1. **Nhãn về muộn bị rò** → khi phát lại, chất lượng thật của tháng `M` chỉ tính được khi `as_of >= M + delay`; trước đó hàm trả `None`, không trả số tính từ nhãn chưa công bố. Test: Task 8 `test_m05_labels_not_before_publication`; module 10 bài nhãn về muộn.
2. **Feature từ tương lai lọt vào tập train (point-in-time)** → feature tốc độ zone cho chuyến tháng `M` chỉ lấy từ dữ liệu trước `M`. Test: Task 8 `test_m06_point_in_time_no_future`; module 06 bài point-in-time.
3. **Rule alert chia cho 0 khi không có traffic** → tỉ lệ lỗi khi `rate(requests)=0` không bắn alert lỗi giả; mất hẳn metric thì có alert `absent`. Test: `promtool test rules` có ca không traffic ở module 09 và Task 9 `test_m09_rules_no_traffic`.
4. **`act` kéo image vài GB / cần mạng** → test dùng runner image tự build, workflow không có `uses:` từ xa; thiếu `act` thì skip có hướng dẫn cài. Test: Task 1 `test_act_run_offline`.
5. **Canary/shadow làm hỏng đường chính** → challenger lỗi hoặc chậm thì request vẫn trả kết quả của champion (shadow không chặn, canary lỗi thì fallback và đếm `eta_fallback_total`). Test: Task 8 `test_m07_shadow_failure_does_not_break`.

---

### Task 1: Hạ tầng Giai đoạn 2 (helper, stack profile, dependency, dọn nợ)

**Files:**
- Modify: `mlopskit.py`, `tests/test_mlopskit.py`, `setup/mlops/compose.yaml`, `setup/mlops/README.md`, `setup/.env.example` (thêm dòng cuối), `tests/test_mlops_setup.py`, `pyproject.toml`, `uv.lock`, `CONTENT_SPEC.md` (chỉ mục `## Track MLOps`), `data/download_dataset.py` (chỉ entry `nyc-tlc-2020`, entry của mình)
- Create: `setup/mlops/feast/Dockerfile`, `setup/mlops/monitoring/{prometheus.yml,alertmanager.yml}`, `setup/mlops/act-runner/Dockerfile`
- Modify (dọn nợ Giai đoạn 1): test module 03 dùng helper chung thay cho hàm `sh()` chép ở nhiều bài; module 02 bỏ bản sao `serve.py`/`make_model.py` trùng nếu gom được mà đề bài vẫn tự đứng được (nếu không gom được thì để nguyên, ghi lý do vào report)

**Interfaces:**
- Produces: `STACK_SERVICES` thêm `"prometheus": ("MLOPS_PROMETHEUS_PORT", 29090)`, `"alertmanager": ("MLOPS_ALERTMANAGER_PORT", 29093)`, `"grafana": ("MLOPS_GRAFANA_PORT", 23000)`, `"redis": ("MLOPS_REDIS_PORT", 26390)`. `require_stack("prometheus")` skip với lệnh có `--profile monitoring`; `require_stack("redis")` với `--profile feast`.
- Produces: compose profile `monitoring` (prometheus `prom/prometheus:v3.5.0`, alertmanager tag cụ thể, grafana `grafana/grafana:12.1.0` với provisioning datasource Prometheus); profile `feast` (redis `redis:7.4.5`). Giữ `mem_limit`, `cpuset`, cổng `127.0.0.1`.
- Produces: `FEAST_IMAGE = "mlops-feast:0.67.0"`; `feast_image() -> str` (build một lần từ `setup/mlops/feast/Dockerfile` nếu chưa có, nhãn `mlops-ex=1` **không** gắn để không bị dọn); `feast_run(repo: Path, *args: str, network: str | None = None, timeout: int = 300) -> subprocess.CompletedProcess` chạy `feast <args>` trong container với `repo` mount `/repo` (rw), user không root, `--rm`, nhãn `mlops-ex=1`; `feast_python(repo: Path, script: str, ...) -> CompletedProcess` chạy một script Python trong cùng image (để gọi `get_historical_features`/`get_online_features`), stdout là JSON.
- Produces: `promtool(*args: str, cwd: Path) -> CompletedProcess` (chạy `promtool` trong `prom/prometheus:v3.5.0`, mount `cwd` read-only tại `/work`).
- Produces: `k6_run(script: Path, env: dict[str, str], network: str = "host") -> CompletedProcess` (image `grafana/k6:1.8.1`, `--summary-export` JSON trả trong `.stdout` hoặc tệp).
- Produces: `ACT_RUNNER = "mlops-act-runner:1"` (Debian slim + python3.12 + uv + git, build từ `setup/mlops/act-runner/Dockerfile`); `act_run(workdir: Path, *args: str, event: str = "push", timeout: int = 600) -> CompletedProcess`: skip `"Chưa cài act. Xem module 08-cicd-for-ml, mục 0"` khi thiếu binary; chạy `act <event> -P ubuntu-latest=<ACT_RUNNER> --pull=false --bind --container-options "--label mlops-ex=1" <args>` với `cwd=workdir`; dọn container nhãn `mlops-ex=1` trong `finally`.
- Produces: `REAL_SHA256: dict[str, str]` cho `nyc-tlc/yellow_tripdata_2019-01..12.parquet` và `nyc-tlc-2020/yellow_tripdata_2020-01..12.parquet` (sha256 tính từ tệp đã tải); `real_month(dataset: str, month: str) -> Path`: gọi `testkit` để skip khi chưa tải, `pytest.fail` khi sha256 lệch (thông báo: tệp nguồn đã bị TLC sửa hoặc tải hỏng, xoá và tải lại). Entry `nyc-tlc-2020` thêm `sha256` nếu `download_dataset.py` có trường đó; không sửa entry `nyc-tlc`.
- Produces: dependency `evidently==0.7.23` trong `dependencies`. Ghi vào mục "Track MLOps" của `CONTENT_SPEC.md`: Feast chạy trong container (lý do: pandas), profile `monitoring`/`feast`, `act` offline, `real_month`.

- [ ] **Step 1: Test thất bại** trong `tests/test_mlopskit.py` và `tests/test_mlops_setup.py`:

```python
def test_stack_port_new_services(monkeypatch): ...      # prometheus 29090, alertmanager 29093, grafana 23000, redis 26390
def test_require_stack_profile_hint(monkeypatch): ...   # cổng prometheus đóng → skip message chứa "--profile monitoring"
def test_profiles_declared(): ...                        # compose: prometheus/alertmanager/grafana có profiles ["monitoring"], redis có ["feast"]; postgres/minio/mlflow không có profile
def test_new_ports_avoid_taken_and_localhost(): ...      # như test Giai đoạn 1, áp cho service mới
def test_real_month_checksum_mismatch(tmp_path, monkeypatch): ...  # tệp giả với sha khác → pytest.fail.Exception, message chứa "sha256"
def test_promtool_check_config(tmp_path): ...            # prometheus.yml tối thiểu → returncode 0; tệp hỏng → != 0
def test_feast_run_version(tmp_path): ...                # feast_run(tmp_path, "version") chứa "0.67.0"
def test_act_run_offline(tmp_path): ...                  # repo git tạm, workflow 1 job `run: python3 -c "print(42)"` → returncode 0, "42" trong output; không tạo leftovers()
def test_k6_run_smoke(tmp_path): ...                     # script k6 gọi một http.server tạm 5 vòng → returncode 0
```

- [ ] **Step 2:** `uv run pytest tests/test_mlopskit.py tests/test_mlops_setup.py -q` → FAIL.
- [ ] **Step 3: Viết helper, Dockerfile, profile, dòng `.env.example`, README stack (bật profile: `docker compose -f setup/mlops/compose.yaml --profile monitoring --profile feast up -d --wait`), thêm `evidently`, `uv lock`, `uv sync`.** Cài `act` vào `~/.local/bin` theo đúng quy trình `## 0. Cài đặt` (checksum) để test chạy được trên máy này. Tính và ghi `REAL_SHA256`.
- [ ] **Step 4:** test → PASS; `uv run pytest tests -q` tăng đúng số test mới; `SOLUTION=1 uv run pytest tracks/mlops -q` không đổi (sau dọn nợ module 02/03).
- [ ] **Step 5: Commit** — `git commit -m "MLOps: hạ tầng Giai đoạn 2 (profile monitoring/feast, act, promtool, k6, kiểm sha256 dữ liệu, evidently)"`

### Task 2–7: Module 05–10

Quy trình mỗi module **giống hệt Task 5–9 của plan Giai đoạn 1** (test trước → starter/lời giải/đề → kiểm chứng → lý thuyết + interview → commit `MLOps: module <id>`). Cập nhật validator: thêm `test_phase2_present` (module 05–10 và milestone m05–m10 tồn tại) vào `tests/test_mlops_track.py` ở Task 9.

| Task | Module | Trọng tâm lý thuyết | Bài bắt buộc (ngoài bài builder tự chọn) | Chấm bằng |
| --- | --- | --- | --- | --- |
| 2 | `05-training-pipelines` | Pipeline tái lập (seed, ghim data version, ghim môi trường, artifact có hash); **Prefect 3**: flow/task, retry, cache theo input (`cache_key_fn`/`cache_policy`), schedule, backfill, parameter; continuous training: trigger theo lịch / data mới / cảnh báo và vì sao **không** retrain mù; **một** phần ôn Airflow (link DE `05-batch-pipelines`); Kubeflow Pipelines, ZenML, Metaflow so sánh | Flow Prefect `train → evaluate → register` có retry cho bước đọc dữ liệu (test bơm lỗi tạm thời 2 lần → flow vẫn xong, đếm đúng số lần thử); cache: chạy lại cùng tham số không train lại (đếm lần gọi); backfill N tháng sinh đúng N artifact theo tên tháng; trigger "data mới": flow chỉ chạy khi hash data đổi; **bài sự cố**: backfill ghi đè kết quả tháng khác (đề chỉ tả "chạy backfill xong số liệu tháng cũ bị đổi") | `prefect_test_harness`, `mlflow_local` |
| 3 | `06-feature-stores` | Training-serving skew (các nguồn: code tiền xử lý hai nơi, dữ liệu khác thời điểm, default khác); point-in-time correctness; **Feast** (entity, feature view, offline store file, online store Redis, `apply`, `materialize-incremental`, feature server); parity batch vs online; khi nào **không** cần feature store; Tecton/Hopsworks so sánh; `## 0. Cài đặt` (Feast chạy trong container: lý do pandas, cách gọi `feast_run`) | Point-in-time join tự viết bằng `pd.merge_asof` (test: không có feature nào có timestamp > event time); feature repo Feast cho "tốc độ trung bình theo zone/giờ" → `apply` + `materialize` + đọc online qua `feast_python`, test online == offline cho cùng entity/thời điểm (`require_stack("redis")`); parity: một hàm tính feature dùng chung cho train và serve, test bảng ca biên (giờ 23→0, zone thiếu → default ghi trong README); **bài sự cố**: model tốt offline nhưng tệ khi serve vì tiền xử lý online lệch (đơn vị km vs dặm) — đề chỉ tả triệu chứng | `ex.module`, `mlopskit.feast_run`/`feast_python`, `require_stack("redis")` |
| 4 | `07-model-serving` | **Một** phần ôn FastAPI (link DS 14); production checklist: load theo alias, `/healthz` vs `/readyz`, warmup, timeout, validate input, version trong response, graceful shutdown; batch inference theo lịch (khác realtime ở đâu); **shadow, canary, A/B** ở tầng ứng dụng (định tuyến theo hash ổn định); rollback nhanh (đổi alias + reload, không rebuild); load test **k6** (p95, thông lượng, cách đọc kết quả, warmup); BentoML/Triton/Ray Serve/TorchServe so sánh | `/readyz` 503 cho tới khi model nạp xong + warmup; canary theo `request_id` hash: tỉ lệ ~ trọng số (±3% trên 2000 request), cùng id → cùng nhánh; shadow: không đổi response, log dự đoán shadow, shadow lỗi không làm lỗi request; rollback: `POST /admin/reload` sau khi đổi alias → `model_version` đổi mà không restart; k6 với ngưỡng p95 trên service container (`built_image` + `k6_run`); **bài sự cố**: sau deploy, độ trễ p99 tăng vọt ở request đầu (thiếu warmup / load model trong request) — đề chỉ tả triệu chứng | `TestClient`, `mlflow_local`, `built_image`, `k6_run` |
| 5 | `08-cicd-for-ml` | CI cho code (lint, test, build image) vs lớp data/model (data test, train mẫu, kiểm model, đăng ký, cổng promotion) và **chỗ hai lớp nối nhau**; CD khi alias đổi; trigger (push, path filter, schedule, `workflow_dispatch`); secrets và OIDC (khái niệm); cache dependency; artifact giữa job; `act` để chạy local và giới hạn của nó; GitLab CI/Jenkins/CML so sánh; chạy trên GitHub thật là tuỳ chọn; `## 0. Cài đặt` (act: bảng phiên bản, checksum, `~/.local/bin`, runner image `mlops-act-runner`) | Workflow CI (ruff + pytest + build) chạy bằng `act_run` pass trên repo tốt và **fail** khi có test hỏng; workflow CT có path filter: đổi `src/` chỉ chạy CI, đổi `params.yaml`/`data.dvc` mới chạy train mẫu + cổng promotion (test bằng `act -l`/`--dryrun` và chạy thật một job); job promotion exit khác 0 khi challenger tệ hơn và job deploy phụ thuộc không chạy; secrets không in ra log (test grep log không thấy giá trị); **bài sự cố**: pipeline xanh nhưng model deploy không phải model vừa train (artifact giữa job lấy nhầm) — đề chỉ tả triệu chứng | `mlopskit.act_run`, `run_sandboxed` cho `git` |
| 6 | `09-monitoring-observability` | Monitoring vs observability; metric service **RED** và metric model (phân phối dự đoán dạng histogram, tỉ lệ fallback, version đang chạy dạng info metric); cardinality (không đặt `request_id` làm label); log dự đoán có cấu trúc để join nhãn sau; alert rule tốt (for, severity, runbook link, alert theo triệu chứng), Alertmanager routing/inhibit; dashboard as code (Grafana provisioning); **một** phần ôn OTel trace (link AE 20); `## 0. Cài đặt` (profile `monitoring`, phiên bản) | Instrument app FastAPI bằng `prometheus_client`: test đọc `/metrics` thấy counter theo `status`, histogram độ trễ, `eta_model_info{version=…}`, **không** có label cardinality cao; rule alert + `promtool test rules`: lỗi >5% trong 5 phút bắn, không traffic thì **không** bắn alert lỗi, mất metric thì bắn `absent`; dashboard JSON provisioned: test Grafana API (`require_stack("grafana")`) thấy dashboard và panel dùng đúng metric; Alertmanager route: critical → receiver `oncall`, warning → `ticket` (`amtool`/test cấu hình); **bài sự cố**: alert không bao giờ bắn dù service lỗi thật (rule sai selector/label) — đề chỉ tả triệu chứng | `mlopskit.promtool`, `require_stack("prometheus","grafana")`, `TestClient` |
| 7 | `10-drift-incidents` | Data drift / prediction drift / concept drift; **một** phần ôn PSI/KS (link DS 14) và giới hạn của chúng (cỡ mẫu lớn → p-value vô nghĩa); **Evidently** (report, preset, test suite); drift đa biến (classifier phân biệt hai tập); nhãn về muộn và ước lượng chất lượng khi chưa có nhãn (proxy: phân phối dự đoán, tỉ lệ fallback, so baseline mùa vụ); **khung quyết định retrain / rollback / giữ nguyên** (detect → verify → impact → decide), drift ≠ chất lượng giảm; runbook, on-call, postmortem không đổ lỗi; NannyML/WhyLabs/Arize so sánh | Hàm PSI/KS tự viết khớp Evidently trên cùng dữ liệu (sai số nhỏ); notebook dữ liệu thật: drift giữa NYC TLC 2019-07 và 2019-12 (mùa vụ) vs 2020-02 và 2020-04 (COVID), quiz `data`; drift đa biến bằng classifier (AUC); **bài quyết định** (YAML `decision`/`reasons`/`evidence`): ít nhất 3 tình huống có số liệu, trong đó **một ca đáp án đúng là `keep`** (drift lớn nhưng MAE không xấu đi) và một ca `rollback`; **bài sự cố**: drift giả do pipeline đổi đơn vị (giây → phút) — đề chỉ tả "dashboard báo drift mạnh từ hôm qua"; Advanced: runbook và postmortem | `ex.module`, `ex.notebook`, `mlopskit.real_month`, evidently |

### Task 8: Capstone m05–m07

**Files:**
- Create: `tracks/mlops/capstone/milestones/m05-orchestration.md`, `m06-feature-store.md`, `m07-serving.md`
- Create: `project/tests/test_m05.py`, `test_m06.py`, `test_m07.py`; starter stub mới trong `project/src/eta/` (`clock.py`, `labels.py`, `flows.py`, `zone_features.py`) và `project/feature_repo/`, `project/loadtest/`
- Modify: `project/tests/etakit.py`, `project/tests/conftest.py` (fixture mới), `solutions/project/` (lời giải), `solutions/SOLUTION.md`, `solutions/project/src/eta/serve.py`
- Modify (nợ Giai đoạn 1): `project/tests/test_m04.py` thêm một ca promotion **khác** ba bài promotion của module 04 (đề xuất: champion có metric NaN/thiếu → không cho promote vì không so được, không phải coi như vắng champion); kiểm lại ca này chưa có trong module 04

**Interfaces** (package `eta`, lời giải tham chiếu cùng tên):
- `eta.clock.months_between(start: str, end: str) -> list[str]` (bao gồm hai đầu, `"YYYY-MM"`); `eta.clock.add_months(month: str, n: int) -> str`.
- `eta.labels.LABEL_DELAY_MONTHS = 1`; `published(month: str, as_of: str, delay: int = LABEL_DELAY_MONTHS) -> bool` (`as_of >= add_months(month, delay)`); `labels_for(month: str, as_of: str, config: Config) -> pd.DataFrame | None` (None khi chưa công bố; cột `request_id`, `duration_s`).
- `eta.flows` (Prefect 3): `train_flow(config_path: str, months: list[str]) -> str` (trả model version, cache theo `data_version` + params); `batch_score_flow(month: str, config_path: str, out_dir: str) -> str` (ghi `predictions_<month>.parquet` với đúng cột `PREDICTION_LOG_COLUMNS`); `replay_flow(start: str, end: str, config_path: str, out_dir: str) -> list[dict]` mỗi tháng một dict khoá `month`, `model_version`, `n_scored`, `mae` (None khi nhãn chưa công bố tại thời điểm mô phỏng), `as_of`.
- `eta.logs.PREDICTION_LOG_COLUMNS = ["request_id", "ts", "model_version", "variant", "PULocationID", "DOLocationID", "pickup_datetime", "trip_distance", "eta_s"]` — dùng chung cho log API (JSON lines) và batch (parquet).
- `eta.zone_features.zone_hour_speed(df: pd.DataFrame, month: str) -> pd.DataFrame` cột `PULocationID`, `pickup_hour`, `avg_speed_mph`, `event_timestamp` (= đầu tháng **sau** `month`, tức feature chỉ dùng được cho chuyến của tháng sau); `DEFAULT_SPEED_MPH` (trung vị toàn thành phố, ghi trong milestone doc); `attach_speed(trips: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame` (point-in-time bằng `merge_asof`, thiếu → `DEFAULT_SPEED_MPH`). `FEATURES` thêm `avg_speed_mph` (m06 trở đi; m01–m04 test vẫn pass).
- `project/feature_repo/`: `feature_store.yaml` (offline file, online Redis `redis:6379` trong mạng `mlops_default`), `features.py` (entity `pu_zone` join key `PULocationID` + `pickup_hour`, feature view `zone_hour_speed` field `avg_speed_mph`, TTL 62 ngày).
- `eta.serve` thêm: `GET /readyz`; env `ETA_CANARY_WEIGHT` (0–1), `ETA_SHADOW` (`0`/`1`); `route(request_id: str, weight: float) -> str` (`"champion"`/`"canary"`, hash ổn định sha256); response thêm khoá `variant`; header `X-Request-ID` (sinh nếu thiếu); `POST /admin/reload` (nạp lại alias `champion`/`challenger`); fallback về champion khi canary lỗi, đếm `eta_fallback_total`; log dự đoán ra `ETA_PREDICTION_LOG` (JSON lines) theo `PREDICTION_LOG_COLUMNS`.
- `project/loadtest/eta.js` (k6): ngưỡng `http_req_duration p(95)<200`, `http_req_failed rate<0.01`.

- [ ] **Step 1: Viết test**, chạy trên starter → FAIL/skip, không ERROR:

```python
def test_m05_months_between(): months_between("2019-11", "2020-02") == ["2019-11", "2019-12", "2020-01", "2020-02"]
def test_m05_labels_not_before_publication(project): published("2020-03", "2020-03") is False; published("2020-03", "2020-04") is True; labels_for(...) is None trước công bố
def test_m05_train_flow_cached(project, tmp_path): prefect_test_harness; gọi train_flow 2 lần cùng tham số → chỉ 1 run MLflow mới (mlflow_local)
def test_m05_batch_score_columns(project, tmp_path): parquet đầu ra có đúng PREDICTION_LOG_COLUMNS, n dòng = n chuyến sạch
def test_m05_replay_mae_late(project, tmp_path): replay_flow 3 tháng tí hon → tháng cuối mae is None, các tháng trước có số
def test_m06_point_in_time_no_future(project, synthetic_trips): attach_speed cho chuyến tháng M chỉ dùng feature có event_timestamp <= pickup; feature tháng M không gắn vào chuyến tháng M
def test_m06_default_for_unknown_zone(project): zone không có feature → DEFAULT_SPEED_MPH
def test_m06_online_offline_parity(project, tmp_path): require_stack("redis"); feast_run apply + materialize; feast_python lấy online và historical cho 20 entity → bằng nhau (sai số 1e-6)
def test_m07_readyz_before_load(project): readyz 503 khi model chưa nạp, 200 sau warmup
def test_m07_canary_split(project): 2000 request_id ngẫu nhiên, weight 0.1 → tỉ lệ canary trong [0.07, 0.13]; cùng id → cùng variant
def test_m07_shadow_failure_does_not_break(project): challenger raise → response 200 từ champion, eta_fallback_total hoặc log shadow lỗi tăng, không 5xx
def test_m07_reload_rollback(project, tmp_path): mlflow_local; champion v1 → v2 → đặt lại v1 + /admin/reload → model_version == v1
def test_m07_loadtest_thresholds(project): built_image(Dockerfile.serve) + k6_run(loadtest/eta.js) → exit 0
def test_m04_promotion_champion_missing_metric(project): champion thiếu "mae_airport" → không promote, reasons nhắc metric thiếu
```

- [ ] **Step 2: Viết milestone docs** (5 phần đúng `CONTENT_SPEC.md`), starter stub, lời giải tham chiếu (cập nhật `Dockerfile.serve`, `compose.yaml` nếu cần biến mới, `requirements-serve.*`).
- [ ] **Step 3:** `SOLUTION=1 nice -n 15 uv run pytest tracks/mlops/capstone -q -rs` (stack + profile `feast` bật) → PASS, không skip; starter: m05–m07 fail/skip, m01–m04 hành vi như trước. Ghi MAE có/không có `avg_speed_mph` trên mẫu thật 2019-02 (train 2019-01) vào `SOLUTION.md`.
- [ ] **Step 4: Commit** — `git commit -m "MLOps: capstone ETA m05–m07 (Prefect, Feast, shadow/canary)"`

### Task 9: Capstone m08–m10 và validator

Phụ thuộc Task 8 (dùng `flows`, `labels`, `serve`, `PREDICTION_LOG_COLUMNS`).

**Files:**
- Create: `tracks/mlops/capstone/milestones/m08-cicd.md`, `m09-monitoring.md`, `m10-drift-incident.md`
- Create: `project/tests/test_m08.py`, `test_m09.py`, `test_m10.py`; starter `project/.github/workflows/`, `project/monitoring/`, `project/src/eta/drift.py`, `project/src/eta/quality.py`, `project/reports/` (khung), `project/docs/` (khung runbook/postmortem)
- Modify: `solutions/project/` (lời giải), `solutions/SOLUTION.md`, `tests/test_mlops_track.py` (thêm `test_phase2_present`)

**Interfaces:**
- `project/.github/workflows/ci.yml` (job `lint`, `test`, `build`), `ct.yml` (path filter `params.yaml`, `dvc.lock`, `src/eta/train.py`; job `validate` → `train` → `gate`; `gate` gọi `python -m eta.cli promote`, exit `EXIT_REJECTED=3` khi bị từ chối), `cd.yml` (`workflow_dispatch` input `model_version`; deploy bằng `docker compose` chỉ khi job `verify` thấy alias `champion` == input). Chỉ bước `run:`.
- `eta.serve` thêm `/metrics`: `eta_requests_total{status,variant}`, `eta_request_duration_seconds` (histogram), `eta_prediction_seconds` (histogram giá trị dự đoán), `eta_fallback_total`, `eta_model_info{version,variant}`.
- `project/monitoring/prometheus.yml`, `rules/eta.rules.yml` (alert `EtaHighErrorRate` >5% trong 5m, `EtaHighLatencyP95` >0.3s trong 10m, `EtaMetricsAbsent`, `EtaPredictionShift` khi trung vị dự đoán lệch >30% so với 7 ngày trước — có `for`, `severity`, `runbook_url`), `rules/eta.rules.test.yml`, `grafana/dashboards/eta.json` (panel RED + phân phối dự đoán + version).
- `eta.drift.psi(ref: pd.Series, cur: pd.Series, bins: int = 10) -> float`; `drift_table(ref: pd.DataFrame, cur: pd.DataFrame, columns: list[str]) -> pd.DataFrame` cột `feature`, `psi`, `ks_stat`.
- `eta.quality.join_labels(predictions: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame` (theo `request_id`); `monthly_quality(joined: pd.DataFrame) -> dict[str, float]` khoá `mae`, `p90_abs_err`, `mae_airport`, `n`.
- `eta.cli replay --start 2019-07 --end 2020-06 --out reports/replay` (dùng `replay_flow`, mẫu nhỏ để ≤5 phút) ghi `reports/replay/summary.parquet` (mỗi tháng: drift PSI chính, MAE khi có nhãn).
- `project/reports/decisions/2020-03.yaml`: `decision: retrain|rollback|keep`, `reasons: list[str]` (≥2), `evidence: {psi_trip_distance, mae_before, mae_after, as_of}`; thêm ít nhất một quyết định khác cho một tháng mùa vụ (vd. `2019-12.yaml`). `project/docs/runbook.md`, `project/docs/postmortem-covid.md` (chấm rubric trong `SOLUTION.md`, test chỉ kiểm cấu trúc heading).

- [ ] **Step 1: Viết test**, chạy trên starter → FAIL/skip, không ERROR:

```python
def test_m08_ci_fails_on_broken_test(project, tmp_path): copy project vào repo git tạm, thêm test hỏng → act_run(push, "-j", "test") returncode != 0; bỏ test hỏng → 0
def test_m08_ct_path_filter(project, tmp_path): act -l / --dryrun: đổi src/eta/serve.py → ct không có trong kế hoạch chạy; đổi params.yaml → có
def test_m08_gate_blocks_deploy(project, tmp_path): challenger tệ hơn (mlflow_local) → job gate exit 3, job sau không chạy
def test_m09_metrics_exposed(project): TestClient gọi /predict 5 lần, 1 lỗi validate → /metrics có eta_requests_total{status="200"} 4 và {status="422"} 1; không label request_id
def test_m09_rules_promtool(project): promtool check rules + promtool test rules → 0
def test_m09_rules_no_traffic(project): tệp test rule có ca không traffic: EtaHighErrorRate không bắn, EtaMetricsAbsent bắn (kiểm tệp test chứa ca này và promtool pass)
def test_m09_dashboard_provisioned(project): require_stack("grafana"); dashboard eta.json load được qua API, mọi expr của panel tham chiếu metric có trong /metrics
def test_m10_psi_matches_reference(project): psi trên hai mẫu tổng hợp khớp giá trị tính tay (1e-6); psi(x, x) == 0
def test_m10_join_labels_and_quality(project): join theo request_id, request thiếu nhãn bị loại, n đúng
def test_m10_replay_summary_real(project): real_month cho 2019-07..2020-06; summary có 12 tháng; PSI trip_distance tháng 2020-04 > tháng 2019-12
def test_m10_decision_files_valid(project): YAML hợp lệ, decision ∈ {retrain, rollback, keep}, ≥2 reasons, evidence khớp summary.parquet (sai số 1%)
def test_m10_docs_structure(project): runbook có các heading Triệu chứng/Kiểm tra/Hành động/Leo thang; postmortem có Tóm tắt/Dòng thời gian/Nguyên nhân/Tác động/Việc cần làm
```

- [ ] **Step 2: Viết milestone docs, starter, lời giải**; thêm `test_phase2_present` vào validator.
- [ ] **Step 3:** `SOLUTION=1 nice -n 15 uv run pytest tracks/mlops/capstone -q -rs` (stack + profile `monitoring` + `feast`, `act` đã cài, `nyc-tlc` + `nyc-tlc-2020` đã tải) → PASS, không skip. Ghi kết quả phát lại thật (PSI, MAE theo tháng, quyết định tham chiếu và lý do) vào `SOLUTION.md`. `uv run pytest tests/test_mlops_track.py -q` → PASS.
- [ ] **Step 4: Commit** — `git commit -m "MLOps: capstone ETA m08–m10 (act, Prometheus/Grafana, phát lại COVID và quyết định)"`

### Task 10: Kiểm toàn nhánh và cập nhật PR

- [ ] **Step 1:** như Task 11 Giai đoạn 1 (regression từng track riêng, so với `main`; `tests` tăng đúng số test mới).
- [ ] **Step 2:** `SOLUTION=1 nice -n 15 uv run pytest tracks/mlops -q -rs --durations=10` (stack + hai profile bật) → chỉ skip bài Advanced; bài chậm nhất ≤300 s.
- [ ] **Step 3:** `cd app && pnpm test && pnpm typecheck && pnpm build` → PASS.
- [ ] **Step 4:** dọn: `leftovers()` rỗng; `docker compose -f setup/mlops/compose.yaml --profile monitoring --profile feast down` cho các profile (giữ stack lõi nếu Giai đoạn 3 dùng tiếp).
- [ ] **Step 5:** rebase lên `origin/main`, push `mlops-track`, mở PR mới (PR #13 của Giai đoạn 1 đã merge ngày 2026-11-03). Rồi viết plan Giai đoạn 3.

## Thứ tự và song song

- Task 1 trước (helper mà mọi task sau dùng).
- Sau Task 1: Task 2–7 và Task 8 chạy **song song**, mỗi task một worktree con từ `mlops-track` (như Giai đoạn 1), merge lại theo thứ tự xong trước merge trước.
- Task 9 sau Task 8. Task 10 cuối.
