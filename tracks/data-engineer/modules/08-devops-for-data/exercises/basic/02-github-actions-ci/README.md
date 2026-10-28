---
title: Workflow GitHub Actions chạy test cho repo pipeline
level: basic
services: []
files:
  - path: starter/ci.yml
    note: 6 TODO
  - path: tests/test_github_actions_ci.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/basic/02-github-actions-ci -q
---

## Mục tiêu

Viết được một workflow CI cơ bản trên GitHub Actions cho repo Python chứa pipeline dữ liệu: đúng
trigger, quyền tối thiểu, có timeout, cài dependency và chạy pytest.

## Đề bài

Repo `olist-pipelines` có `requirements.txt` và thư mục `tests/`. Hoàn thiện `starter/ci.yml`
(trên repo thật sẽ đặt ở `.github/workflows/ci.yml`) sao cho:

- Workflow tên `ci`, chạy khi **push lên nhánh `main`** và khi có **pull request**.
- `GITHUB_TOKEN` chỉ có quyền `contents: read` (khai báo `permissions` ở cấp workflow).
- Có job `test` chạy trên `ubuntu-latest` (hoặc `ubuntu-24.04`), có `timeout-minutes` không quá 30.
- Các bước: checkout bằng `actions/checkout@v4`; cài Python bằng `actions/setup-python@v5` với
  `python-version: "3.12"` (viết dạng chuỗi) và bật `cache: pip`; cài dependency bằng
  `pip install -r requirements.txt`; cuối cùng chạy `pytest`.

Test đọc YAML bằng PyYAML và kiểm tra cấu trúc. Lưu ý: PyYAML (YAML 1.1) đọc khoá `on` thành giá
trị boolean `True`; test đã xử lý chuyện này, bạn cứ viết `on:` bình thường.

## Tiêu chí đạt

- YAML hợp lệ, `name: ci`.
- `on` có `push` với `branches` chứa `main`, và có `pull_request`.
- `permissions` cấp workflow bằng đúng `{contents: read}`.
- Job `test`: `runs-on` bắt đầu bằng `ubuntu`, `timeout-minutes` là số trong khoảng 1–30.
- Có step `uses: actions/checkout@v4` đứng trước mọi step `run`.
- Có step `uses: actions/setup-python@v5` với `python-version` là chuỗi `"3.12"` và `cache: pip`.
- Có step `run` chứa `pip install -r requirements.txt`, sau đó có step `run` chứa `pytest`.

## Gợi ý

### Gợi ý 1

Viết `python-version: 3.12` không có ngoặc, YAML sẽ hiểu là số `3.12`; tệ hơn, `3.10` sẽ thành
`3.1`. Luôn đặt phiên bản trong ngoặc kép.

### Gợi ý 2

Khung:

```yaml
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
```
