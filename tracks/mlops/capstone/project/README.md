# Dịch vụ ETA: code của bạn

Thư mục này là chỗ bạn làm capstone. Lúc đầu có notebook baseline của team DS, khung package `src/eta/` (tên module và
chữ ký hàm, thân hàm còn `NotImplementedError`) và test chấm. Mỗi milestone thêm tệp vào đúng vị trí dưới đây. Đề từng
milestone ở [`../milestones/`](../milestones/), tổng quan ở [README capstone](../README.md).

| Tệp / thư mục | Milestone | Bạn làm |
| --- | --- | --- |
| `notebooks/baseline.ipynb` | điểm xuất phát | Đọc, chạy, **không sửa**: đây là mốc so sánh (MAE baseline khoảng 243 s) |
| `src/eta/data.py`, `features.py`, `train.py`, `config.py`, `cli.py` | [M01](../milestones/m01-package.md) | Package, config, logging, CLI `train` |
| `params.yaml`, `pyproject.toml`, `Makefile` | [M01](../milestones/m01-package.md) | Config và công cụ |
| `src/eta/serve.py`, `Dockerfile.serve`, `Dockerfile.train`, `compose.yaml` | [M02](../milestones/m02-containers.md) | API, hai image, stack Compose |
| `src/eta/validate.py`, `dvc.yaml` | [M03](../milestones/m03-data-pipeline.md) | Pipeline DVC, schema Pandera |
| `src/eta/registry.py`, `promotion.py` | [M04](../milestones/m04-registry-promotion.md) | Registry, cổng promotion, rollback |
| `src/eta/clock.py`, `labels.py`, `flows.py`, `PREDICTION_LOG_COLUMNS` trong `logs.py` | [M05](../milestones/m05-prefect-replay.md) | Đồng hồ mô phỏng, nhãn về muộn, flow Prefect train/batch/replay |
| `src/eta/zone_features.py`, `feature_repo/` | [M06](../milestones/m06-feast-features.md) | Feature tốc độ zone/giờ, point-in-time, Feast online/offline |
| `src/eta/serve.py` (bản M07), `loadtest/eta.js` | [M07](../milestones/m07-serving-canary.md) | Readiness, canary, shadow, reload/rollback, k6 |
| `.github/workflows/`, `requirements-ci.txt`, `tests_own/` | [M08](../milestones/m08-cicd-act.md) | CI, CT có cổng promotion, CD theo alias `champion`, chạy bằng `act` |
| `monitoring/`, `src/eta/serve.py` (bản M09) | [M09](../milestones/m09-monitoring.md) | Metric Prometheus, alert rule có test promtool, dashboard Grafana |
| `src/eta/drift.py`, `quality.py`, `reports/decisions/`, `docs/` | [M10](../milestones/m10-drift-replay.md) | PSI/KS, chất lượng theo nhãn về muộn, phát lại 2019–2020, quyết định, runbook, postmortem |
| `tests/` | mọi milestone | Không sửa: test chấm bài. Test của bạn để ở chỗ khác (ví dụ `tests_own/`) |

`.gitignore` ở đây chặn `data/`, `models/`, `reports/` (trừ `reports/decisions/` của M10), `metrics.json`, `.ci-deps`,
`dist/`: dữ liệu và model đi qua DVC và MLflow, không qua git.

## Chạy test

Từ gốc repo:

```bash
uv run pytest tracks/mlops/capstone/project/tests -q -rs
uv run pytest tracks/mlops/capstone/project/tests -q -rs -k m01
```

Chưa làm milestone nào thì test **fail** với thông báo "chưa import được ...", "NotImplementedError" hay "Chưa có tệp
...", không phải lỗi của test. Test skip khi thiếu thứ ngoài code của bạn, và lý do skip nói cần làm gì:

| Thiếu | Test skip | Cách bật |
| --- | --- | --- |
| Bộ `nyc-tlc` | `test_m01_real_data_baseline`, M08 (CT), M10 (phát lại) | `uv run python data/download_dataset.py nyc-tlc` |
| Docker | M02, `test_m06_online_offline_parity`, `test_m07_loadtest_thresholds`, M08, `test_m09_rules_*` | Cài Docker, user thuộc nhóm `docker` |
| Stack MLOps | `test_m02_compose_api`, `test_m04_alias_rollback` | `docker compose -f setup/mlops/compose.yaml up -d --wait` |
| Redis cho Feast | `test_m06_online_offline_parity` | `docker compose -f setup/mlops/compose.yaml --profile feast up -d --wait` |
| bubblewrap (`bwrap`) | test chạy CLI, DVC, M08 | `sudo apt install bubblewrap` |
| `act` | M08 (trừ `test_m08_workflow_structure`) | Cài theo module 08, mục 0 |
| Grafana của stack | `test_m09_dashboard_provisioned` | `docker compose -f setup/mlops/compose.yaml --profile monitoring up -d --wait` |
| Bộ `nyc-tlc-2020` | `test_m10_replay_summary_real`, `test_m10_decision_files_valid` | `uv run python data/download_dataset.py nyc-tlc-2020` |

Skip không tính là đạt. Trên máy dùng chung, thêm `nice -n 15` trước `uv run`.

Bản tham chiếu nằm ở [`../solutions/`](../solutions/SOLUTION.md) và chạy được bằng
`SOLUTION=1 uv run pytest tracks/mlops/capstone/project/tests -q -rs`. Chỉ mở sau khi đã tự làm.

## Vận hành

Mục này là của bạn. Mỗi milestone thêm một phần theo "Kết quả nộp": lệnh train và MAE (M01), container (M02), dữ liệu và
ngưỡng validation (M03), registry, runbook rollback và model card (M04), orchestration và replay (M05), feature (M06),
serving và kết quả k6 (M07), CI/CD (M08), monitoring (M09), drift và sự cố (M10).
