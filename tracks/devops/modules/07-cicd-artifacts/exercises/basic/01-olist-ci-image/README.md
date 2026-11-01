---
title: Workflow CI cho Olist Shop - test, tag bất biến, image lên registry
level: basic
services: [registry]
files:
  - path: starter/.github/workflows/ci.yml
    note: 6 TODO; giữ nguyên hai bước cài đặt có sẵn
  - path: tests/test_ci_image.py
    note: Không sửa
  - path: tests/fixtures/repo/Dockerfile
    note: Dockerfile của repo, harness build image từ tệp này
  - path: tests/fixtures/repo/requirements-dev.txt
    note: Dependency cho test (pytest, fakeredis, httpx, pyyaml), ghim phiên bản
  - path: tests/fixtures/ci.starter.yml
    note: Bản gốc của starter, test chứng minh phép kiểm bắt được lỗi của nó
run:
  - docker pull node:24.22.2-trixie-slim && docker build --pull=false -t devops-track/act-runner:1.0 setup/act-runner
  - docker pull python:3.12.16-slim-trixie
  - docker compose -f setup/docker-compose.yml --profile devops up -d registry
  - uv run pytest tracks/devops/modules/07-cicd-artifacts/exercises/basic/01-olist-ci-image -q
---

## Mục tiêu

Viết workflow GitHub Actions đầu tiên cho Olist Shop theo đúng thứ tự một pipeline nghiêm túc: test xanh mới tới build, image
mang tag bất biến suy ra từ commit, token chỉ có quyền tối thiểu, bước đụng registry thật chỉ chạy trên GitHub. Chạy nó trên máy
bằng `act`, rồi thấy chính image đó nằm trong registry local theo digest.

## Đề bài

Repo của bài là Olist Shop (`tracks/devops/sample-app`: `olist_shop/`, `tests/`, `requirements.txt`, `compose.yaml`) cộng hai tệp
trong `tests/fixtures/repo/` (`Dockerfile` ghim `python:3.12.16-slim-trixie`, nhận `ARG APP_VERSION`; `requirements-dev.txt`).
Bạn chỉ viết `starter/.github/workflows/ci.yml`. Starter đã có job `test` với hai bước **Cài uv** và **Cài Python và
dependency**; giữ nguyên tên và nội dung hai bước này (mục "Vì sao" bên dưới).

Workflow cần có:

1. Trigger: `push` chỉ trên `branches: [main]`, và `pull_request`. Không trigger nào khác ngoài `workflow_dispatch` (tuỳ chọn).
2. `permissions:` cấp workflow đúng bằng `contents: read`.
3. `concurrency:` cấp workflow có `group` chứa `github.ref` và `cancel-in-progress` bật.
4. Job `test`: `timeout-minutes` từ 1 tới 30, không có quyền `write`, thêm bước `run:` chạy
   `"$RUNNER_TEMP/venv/bin/python" -m pytest -q tests`.
5. Job `image`: `needs: test`; `permissions` đúng bằng `contents: read` và `packages: write`; `timeout-minutes` từ 1 tới 30;
   `outputs.tag` lấy từ `steps.<id>.outputs.tag` của một bước trong job.
6. Bước tính tag (bước `run:` có `id` ở trên): tag là `sha-` cộng 12 ký tự đầu của `GITHUB_SHA`, ghi `tag=...` vào
   `$GITHUB_OUTPUT`, in hai dòng `devops-ex-output tag=<tag>` và `devops-ex-output revision=<GITHUB_SHA>`. Bước này không được
   chứa `date`, `run_number`, `run_id`, `run_attempt` hay `latest`.
7. Bước `docker/login-action` vào `registry: ghcr.io` bằng `password: ${{ secrets.GITHUB_TOKEN }}`, và bước
   `docker/build-push-action` với `context: .`, `tags` dùng `steps.<id>.outputs.tag` (không có `latest`),
   `build-args: APP_VERSION=${{ steps.<id>.outputs.tag }}`, `push` đúng bằng `${{ github.event_name == 'push' }}` hoặc
   `${{ github.event_name != 'pull_request' }}` để pull request chỉ build mà không push. Cả hai bước có `if:` mà testkit công nhận
   là chắc chắn sai dưới act: `${{ !env.ACT }}`, có thể nối thêm điều kiện bằng `&&` (mục 3 của lý thuyết).

**Vì sao chạy được trên máy, và phần nào không chạy.** Test chạy workflow bằng `act` (mục 3 của lý thuyết) qua
`testkit.act_run`: mỗi job là một container `devops-track/act-runner:1.0` (image runner của track, build một lần theo mục 0 của
module), ghim CPU, RAM 1 GB, **không có socket Docker**. Image đã có uv 0.10.8, CPython 3.12.13 và cache wheel của Olist Shop, nên
hai bước có sẵn không tải gì: **Cài uv** thấy đúng phiên bản thì thoát, **Cài Python và dependency** lấy Python và wheel từ image
(`UV_OFFLINE=1`). Trên runner `ubuntu-latest` của GitHub, cùng hai bước đó tải uv (kiểm SHA-256), Python và wheel từ Internet.
Bước `docker/login-action` và `docker/build-push-action` cần socket Docker và registry thật nên gắn `if: ${{ !env.ACT }}`: dưới
act chúng bị bỏ qua (testkit thay action bằng action rỗng, không tải gì), test chỉ **kiểm tĩnh** chúng: cấu trúc YAML theo 7 điểm
trên, cộng `actionlint` nếu bạn đã cài. Phần build và push thật do **harness** làm thay workflow, dùng đúng output của workflow:

1. `act_run` với sự kiện `push` trên nhánh `main`. Job `test` và `image` phải xanh; tag đọc từ dòng `devops-ex-output tag=` của
   job `image` (`act_outputs`), phải khớp `sha-<12 ký tự đầu của revision>`.
2. Chạy lại với một test đỏ do harness thêm (`tests/test_devops_ex_canary.py`): job `test` phải fail, job `image` không được
   chạy và không in tag.
3. `DockerLab.build` build `Dockerfile` của repo với `APP_VERSION=<tag>`, `DockerLab.push` đẩy lên registry local thành
   `localhost:15000/devops-ex-<id>/olist-api:<tag>`; test hỏi API của registry digest của tag đó, kiểm manifest tồn tại theo digest,
   chạy container **theo digest** và đòi `GET /healthz` trả `{"status": "ok", "version": "<tag>"}`. Image và manifest bị xoá khi
   test xong.

Registry local là service `registry` (profile `devops`) trong `setup/docker-compose.yml`; chưa bật thì test đó skip kèm lệnh bật.
Thiếu image runner thì test skip kèm lệnh build; thiếu image Python thì skip kèm lệnh `docker pull`. Lần build image đầu tiên
của harness cần mạng để tải gói pip (lỗi mạng thì skip); các lần sau dùng cache của BuildKit. `actionlint`
chưa cài thì riêng test actionlint skip (xem `## 0. Cài đặt` của module); test cấu trúc không phụ thuộc actionlint.

**Chạy pipeline thật trên GitHub (tuỳ chọn, không chấm).** Tạo repo riêng (private cũng được) rồi chép đúng bộ tệp mà harness
dựng:

```bash
EX=tracks/devops/modules/07-cicd-artifacts/exercises/basic/01-olist-ci-image &&
DEST="$(mktemp -d)/olist-shop-ci" && mkdir -p "$DEST/.github/workflows" &&
cp -r tracks/devops/sample-app/{olist_shop,tests,conftest.py,requirements.txt,compose.yaml,.dockerignore} "$DEST/" &&
cp "$EX"/tests/fixtures/repo/{Dockerfile,requirements-dev.txt} "$DEST/" &&
cp "$EX/starter/.github/workflows/ci.yml" "$DEST/.github/workflows/ci.yml" &&
find "$DEST" -name __pycache__ -prune -exec rm -rf {} + &&
cd "$DEST" && git init -q -b main && git add -A && git commit -qm "Olist Shop CI" &&
echo "Đã dựng repo ở $DEST; thêm remote GitHub của bạn rồi git push -u origin main"
```

Trên GitHub, `env.ACT` rỗng nên hai bước Docker chạy thật: pull request chỉ build, push lên `main` thì đẩy
`ghcr.io/<owner>/olist-api:sha-...` (owner phải viết thường; tài khoản có chữ hoa thì đổi tag thành chữ thường). Package mới tạo
trên GHCR mặc định private. Workflow chỉ dùng `GITHUB_TOKEN` nên không cần tạo secret nào. Xoá repo và package khi xong.

## Tiêu chí đạt

- Test cấu trúc pass với đủ 7 điểm ở trên; một test đưa `tests/fixtures/ci.starter.yml` vào cùng phép kiểm và đòi bắt được các
  thiếu sót của nó (trigger, quyền, concurrency, thiếu job `image`, timeout, thiếu pytest), một test khác đưa vào job `image` cẩu
  thả (không `needs`, `write-all`, tag theo `date`, login Docker Hub bằng PAT, tag `latest`, `push: true`) và đòi bắt đủ.
- `actionlint` (chạy với `-shellcheck= -pyflakes=` để kết quả không phụ thuộc máy) không báo lỗi.
- Dưới act: code đúng thì job `test` và `image` xanh, tag `sha-<12 hex>` khớp revision; có test đỏ thì `image` không chạy.
- Image do harness build theo tag của workflow nằm trong registry, tra được theo digest, chạy theo digest trả đúng version.

## Gợi ý

### Gợi ý 1

Bash có cắt chuỗi: `${GITHUB_SHA::12}`. Ghi output của bước bằng `echo "tag=${tag}" >> "$GITHUB_OUTPUT"`, rồi khai báo ở cấp job
`outputs: tag: ${{ steps.<id>.outputs.tag }}` để job khác đọc qua `needs.image.outputs.tag`. Nhớ đặt `id:` cho bước tính tag.

### Gợi ý 2

`push: ${{ github.event_name == 'push' }}` cho pull request build để bắt lỗi Dockerfile mà không đẩy image của code chưa review.
Điều kiện của bước login có thể là `${{ !env.ACT && github.event_name == 'push' }}`. Muốn thử nhanh từng job:
`act push -j test -P ubuntu-latest=devops-track/act-runner:1.0 --pull=false --container-daemon-socket -` trong thư mục repo
đã dựng ở trên (`--container-daemon-socket -` để job không nhận socket Docker của máy bạn).
