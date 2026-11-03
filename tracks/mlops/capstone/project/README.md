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
| `tests/` | mọi milestone | Không sửa: test chấm bài. Test của bạn để ở chỗ khác (ví dụ `tests_own/`) |

`.gitignore` ở đây chặn `data/`, `models/`, `reports/`, `metrics.json`: dữ liệu và model đi qua DVC và MLflow, không
qua git.

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
| Bộ `nyc-tlc` | `test_m01_real_data_baseline` | `uv run python data/download_dataset.py nyc-tlc` |
| Docker | M02 | Cài Docker, user thuộc nhóm `docker` |
| Stack MLOps | `test_m02_compose_api`, `test_m04_alias_rollback` | `docker compose -f setup/mlops/compose.yaml up -d` |
| bubblewrap (`bwrap`) | test chạy CLI, DVC | `sudo apt install bubblewrap` |

Skip không tính là đạt. Trên máy dùng chung, thêm `nice -n 15` trước `uv run`.

Bản tham chiếu nằm ở [`../solutions/`](../solutions/SOLUTION.md) và chạy được bằng
`SOLUTION=1 uv run pytest tracks/mlops/capstone/project/tests -q -rs`. Chỉ mở sau khi đã tự làm.

## Vận hành

Mục này là của bạn. Mỗi milestone thêm một phần theo "Kết quả nộp": lệnh train và MAE (M01), container (M02), dữ liệu và
ngưỡng validation (M03), registry, runbook rollback và model card (M04).
