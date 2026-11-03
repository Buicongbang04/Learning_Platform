---
title: Workflow CI cho repo ML - ruff, pytest, build, chạy bằng act
level: basic
services: []
files:
  - path: starter/ci.yml
    note: Workflow, 3 bước TODO
  - path: tests/test_ci_workflow.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/08-cicd-for-ml/exercises/basic/01-ci-workflow-green-red -q
---

## Mục tiêu

Viết workflow CI đầu tiên cho một repo ML nhỏ và chứng minh nó đúng theo cả hai chiều: xanh trên repo tốt, **đỏ** khi có
test hỏng hoặc lỗi lint. Workflow chạy thật bằng `act` trong runner image `mlops-act-runner:1`, không cần GitHub.

## Đề bài

Test dựng một repo git tạm (gói `etalite`: `src/`, `tests/`, `pyproject.toml`), chép `starter/ci.yml` vào
`.github/workflows/ci.yml`, rồi chạy `act push`. Runner không có mạng nên test chép sẵn công cụ vào thư mục
`.ci-tools/` của repo (đây chỉ là chỗ thay cho bước cài đặt trên runner thật): `ruff` ở `.ci-tools/bin/ruff`, `pytest` import được
khi đặt `PYTHONPATH=.ci-tools`. Điền `starter/ci.yml`:

1. Kích hoạt trên `push` và `pull_request`.
2. Ba job, đều `runs-on: ubuntu-latest` và **chỉ có bước `run:`** (không `uses:`, vì runner không tải được action từ xa):
   - `lint`: `.ci-tools/bin/ruff check src tests`;
   - `test`: `python -m pytest tests -q -p no:cacheprovider`;
   - `build`: tạo thư mục `dist` rồi `python -m zipapp src -o dist/etalite.pyz -m "etalite.cli:main"`.
3. `build` phải `needs` cả `lint` và `test`: không đóng gói thứ chưa qua kiểm.

## Tiêu chí đạt

- Cấu trúc đúng như trên (job, `needs`, `runs-on`, không `uses:`, có `push` và `pull_request`).
- Repo tốt: `act` thoát mã 0, có `dist/etalite.pyz` và chạy `python dist/etalite.pyz` in `etalite 1.0 40`.
- Sửa một test thành sai: `act` thoát mã khác 0, log có `Job failed`, không có `dist/etalite.pyz`.
- Thêm một `import` không dùng vào `src/etalite/model.py`: `act` thoát mã khác 0 và không có `dist/etalite.pyz`.

## Gợi ý

### Gợi ý 1

Bước `run:` nhiều dòng dùng `|`. Mỗi job chạy trong container mới nhưng cùng thư mục repo (`--bind`), nên `dist/` tạo trong
job `build` hiện ra ở thư mục repo trên máy bạn. Biến môi trường cho một bước đặt ở khoá `env:` của bước đó.

### Gợi ý 2

Muốn biết vì sao job đỏ, đọc log theo tiền tố `[ci/lint]`, `[ci/test]`. Chạy tay trong thư mục repo tạm:
`act push -P ubuntu-latest=mlops-act-runner:1 --pull=false --bind` (cần cả `--container-options "--user $(id -u):$(id -g)"` nếu muốn
tệp sinh ra thuộc về bạn).
