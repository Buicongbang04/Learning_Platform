---
title: Git, Makefile và pre-commit cho repo ML
level: basic
services: []
files:
  - path: starter/.gitignore
    note: Viết từ đầu
  - path: starter/Makefile
    note: 5 TODO
  - path: starter/.pre-commit-config.yaml
    note: 1 TODO lớn
  - path: tests/test_repo_hygiene.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/01-engineering-foundations/exercises/basic/03-ml-repo-hygiene -q
---

## Mục tiêu

Dựng ba tệp giữ cho repo ML sạch: `.gitignore` chặn data, model và bí mật; `Makefile` làm lệnh chung của cả đội; `pre-commit` chặn tệp lớn trước khi vào lịch sử.

## Đề bài

Test dựng một repo git tạm, chép ba tệp của bạn vào, tạo tệp giả ở nhiều đường dẫn rồi chạy `git` và `make` trong sandbox `bubblewrap`.

**`.gitignore`**: phải chặn dữ liệu (`data/raw/...`, `data/interim/...`), artifact model (`models/`, `*.joblib`, `*.pkl`), tracking cục bộ (`mlruns/`, `mlflow.db`), môi trường ảo, cache, notebook checkpoint, `.env` và `.env.*`. Phải **không** chặn: mã nguồn, test, `uv.lock`, `Makefile`, `data/README.md`, `data/.gitkeep` và `.env.example`. Sau `git add -A`, chỉ mã nguồn và tệp cấu hình được stage.

**`Makefile`**: mặc định in danh sách lệnh (mỗi target có chú thích `##` thành một dòng `tên  mô tả`), và có các target:

| Target | Việc làm |
| --- | --- |
| `setup` | `uv sync --frozen` |
| `test` | chạy `pytest` qua `uv run` |
| `lint` | `ruff check` và `ruff format --check` trên `src tests` |
| `train` | tạo `models/` rồi chạy `$(PYTHON) -m eta_mini --data $(DATA) --out models/model.joblib --seed $(SEED)`; `PYTHON`, `DATA`, `SEED` ghi đè được từ dòng lệnh |
| `clean` | xoá `models/`, cache và `__pycache__`, giữ nguyên `data/` |

**`.pre-commit-config.yaml`**: hook `check-added-large-files` (giới hạn không quá 1024 KB), `check-yaml`, `ruff`, `ruff-format`; ghim `rev` của từng repo bằng tag bắt đầu bằng `v` (không dùng `main`, `master`, `HEAD`).

## Tiêu chí đạt

- Mọi đường dẫn data, model, tracking, môi trường, cache và `.env*` bị `git check-ignore` chặn.
- Mã nguồn, lockfile, `data/README.md`, `data/.gitkeep`, `.env.example` không bị chặn.
- `make` không tham số liệt kê đủ 5 target; `make -n setup|test|lint` hiện đúng lệnh.
- `make train PYTHON=echo SEED=7 ...` truyền biến đúng và tạo `models/`.
- `make clean` xoá model và cache nhưng không đụng `data/`.
- `git add -A` trên repo thử chỉ stage đúng các tệp nguồn, `uv.lock`, `Makefile`, `data/README.md`, `data/.gitkeep`, `.env.example`, `.gitignore` và `.pre-commit-config.yaml`.
- Cấu hình pre-commit ghim `rev` và giới hạn kích thước tệp.

## Gợi ý

### Gợi ý 1

Chặn cả thư mục `data/*` rồi bỏ chặn từng tệp bằng `!` (`!data/README.md`). Chặn `data/` (có dấu `/` cuối) thì không bỏ chặn được tệp bên trong.

### Gợi ý 2

Dòng ghi chú `##` trên target đọc được bằng `grep -E '^[a-z_-]+:.*## ' $(MAKEFILE_LIST)`; trong recipe viết `$$1` thay cho `$1` của awk.

### Gợi ý 3

Tên repo hook: `pre-commit/pre-commit-hooks` (tag `v6.0.0`) và `astral-sh/ruff-pre-commit` (tag `v0.17.1`).
