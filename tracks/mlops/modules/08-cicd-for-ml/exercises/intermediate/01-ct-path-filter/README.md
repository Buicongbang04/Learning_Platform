---
title: Workflow CT với path filter - đổi src chỉ chạy CI, đổi params hay data mới train
level: intermediate
services: []
files:
  - path: starter/ci.yml
    note: Thiếu khoá on, giữ nguyên job
  - path: starter/ct.yml
    note: Thiếu khoá on, giữ nguyên job
  - path: tests/test_ct_paths.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/08-cicd-for-ml/exercises/intermediate/01-ct-path-filter -q
---

## Mục tiêu

Tách hai lớp pipeline bằng trigger: sửa code chỉ chạy CI (rẻ, nhanh), sửa đầu vào của model (tham số, dữ liệu) mới chạy
huấn luyện mẫu (đắt hơn). Bạn viết bộ lọc `paths`, kiểm nó bằng một bảng các thay đổi, rồi chạy thật job `train` trên dữ liệu
taxi.

## Đề bài

Repo `etalite` có `src/`, `tests/`, `pyproject.toml`, `params.yaml`, `data.dvc`, `train.py`, `gate.py`. Hai workflow trong
`starter/` đã có job, chỉ thiếu khoá `on:` (hiện chỉ có `push:` trần). Điền:

1. **`ci.yml`**: `push` và `pull_request`, đều với `paths` đúng năm mục `src/**`, `tests/**`, `pyproject.toml`, `train.py`, `gate.py`.
2. **`ct.yml`**: `push` chỉ trên nhánh `main`, `pull_request`, đều với `paths` đúng bốn mục `params.yaml`, `data.dvc`,
   `train.py`, `gate.py`; thêm `workflow_dispatch` (không input).

Quy ước khớp đường dẫn mà test dùng, theo đúng GitHub: `*` không vượt qua dấu `/`, `**` vượt qua; mẫu không có `/` đứng đầu
vẫn neo ở gốc repo, nên `params.yaml` không khớp `docs/params.yaml`. Không dùng mẫu phủ định `!`. Khi workflow có `paths`, nó chạy
nếu **ít nhất một** tệp đổi khớp một mẫu.

Test có ba phần: bảng 12 thay đổi mỗi sự kiện (vd. chỉ sửa `src/` thì chỉ `ci` chạy; sửa `params.yaml` thì chỉ `ct`; sửa
`train.py` thì cả hai); `act -l` và `act --dryrun` kiểm cấu trúc; chạy thật `act -W .github/workflows/ct.yml -j train`
trên mẫu 4 000 chuyến ngẫu nhiên của tháng 3/2019 (qua `mlopskit.real_month`; skip nếu chưa tải dữ liệu).

## Tiêu chí đạt

- Với mọi thay đổi trong bảng, đúng workflow chạy (cả `push` và `pull_request`).
- `ct` không chạy khi push lên nhánh khác `main`, và `workflow_dispatch` luôn chạy được `ct`.
- `act -l` liệt kê `lint`, `test` (workflow `ci`) và `train`, `gate` (workflow `ct`); `--dryrun` thoát 0.
- Job `train` chạy thật: thoát 0, tạo `models/metrics.json` với `rows` > 2000, in dòng `trained model_id=...`.

## Gợi ý

### Gợi ý 1

`paths` và `branches` nằm trong từng sự kiện. Một lỗi quen thuộc: `src/*` chỉ khớp tệp ngay dưới `src/`, không khớp
`src/etalite/model.py`. Bạn cần mẫu nào?

### Gợi ý 2

`act` không tự đánh giá `paths` khi chạy local (việc đó do máy chủ GitHub làm), nên đừng thử bằng cách `act push` rồi xem nó có
chạy không: bảng trong test mô phỏng đúng luật của GitHub, bạn dùng nó để kiểm bộ lọc trước khi push lên thật.
