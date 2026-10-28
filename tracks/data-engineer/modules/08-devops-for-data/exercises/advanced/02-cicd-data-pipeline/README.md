---
title: Pipeline CI/CD đầy đủ cho repo dữ liệu (test, build image, deploy nhiều môi trường)
level: advanced
services: []
files:
  - path: starter/pipeline.yml
    note: Viết lại gần như toàn bộ
  - path: tests/test_cicd_data_pipeline.py
    note: Không sửa
run:
  - uv run pytest tracks/data-engineer/modules/08-devops-for-data/exercises/advanced/02-cicd-data-pipeline -q
---

## Mục tiêu

Thiết kế một workflow GitHub Actions nhiều job cho repo pipeline dữ liệu: kiểm thử nhiều tầng,
build image bất biến theo commit, triển khai lần lượt staging rồi production với cơ chế duyệt, và
an toàn về quyền.

## Đề bài

Repo `olist-pipelines` có code Python, `requirements.txt`, `tests/unit`, `tests/integration` (cần
PostgreSQL) và `Dockerfile`. Image đẩy lên GHCR (`ghcr.io/<owner>/olist-pipelines`). Việc deploy
thực hiện bằng một lệnh bất kỳ (vd. `kubectl set image`, `helm upgrade`, hoặc cập nhật repo GitOps);
bạn có thể dùng lệnh giả lập nhưng phải truyền đúng tag image.

Viết `starter/pipeline.yml` (sẽ đặt ở `.github/workflows/pipeline.yml`) thoả mãn:

1. Chạy khi push lên `main` và khi có pull request. Có `concurrency` để không chạy/deploy chồng.
2. `permissions` cấp workflow chỉ `contents: read`; job nào cần thêm quyền (đẩy image cần
   `packages: write`) thì khai báo ở cấp job.
3. Job **unit**: lint (`ruff`) và unit test (`pytest`), không cần service.
4. Job **integration**: `needs` job unit, chạy pytest với **service container** `postgres` (image
   pin phiên bản, có health check trong `options`), truyền DSN qua `env`.
5. Job **build**: chỉ chạy trên `main` (điều kiện `if` dựa vào `github.ref`), `needs` integration,
   build và push image có tag chứa `github.sha` (không chỉ `latest`).
6. Job **deploy staging** (`environment: staging`) `needs` build; job **deploy production**
   (`environment: production`) `needs` deploy staging. Cả hai dùng đúng image tag theo SHA.
7. Mọi job có `timeout-minutes`. Không có secret viết thẳng (mật khẩu thật, token).

Tên job tuỳ bạn; test nhận diện vai trò của job theo nội dung.

## Tiêu chí đạt

- Trigger `push` (main) và `pull_request`; có `concurrency`.
- `permissions` workflow = `{contents: read}`; job build có `packages: write`.
- Có job chạy `ruff` và `pytest` không có `services`.
- Có job có `services.postgres` với image pin version và `--health-cmd`, chạy `pytest`, phụ thuộc
  (trực tiếp hoặc gián tiếp) vào job unit.
- Có job build chứa `github.sha` trong tag, có `if` nhắc `refs/heads/main`, phụ thuộc job integration.
- Có job `environment` staging phụ thuộc build, job `environment` production phụ thuộc staging.
- Mọi job có `timeout-minutes`.
- Không có chuỗi giống token (`ghp_...`, `AKIA...`) trong tệp.

## Gợi ý

### Gợi ý 1

Chuỗi phụ thuộc: `unit → integration → build → deploy-staging → deploy-production`. Job PR dừng ở
integration vì build có `if: github.ref == 'refs/heads/main'` (các job phụ thuộc build cũng bị bỏ
qua theo).

### Gợi ý 2

Build và push lên GHCR:

```yaml
- uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
- uses: docker/build-push-action@v6
  with:
    push: true
    tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

Environment `production` cấu hình "required reviewers" trên GitHub để có bước duyệt tay.
