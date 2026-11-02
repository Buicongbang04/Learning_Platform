# M04: Pipeline CI/CD tới registry local và staging

## Mục tiêu

M03 cho bạn một artifact tốt, nhưng vẫn do người build trên máy mình rồi gõ lệnh compose. Milestone này đặt artifact
đó vào một pipeline: mỗi commit lên `main` chạy test, build hai image `api` và `worker` một lần với tag bất biến, quét
bằng đúng chính sách trivy của M03 **trước** khi lên registry, đẩy lên registry rồi deploy staging **theo digest**, và
chỉ coi là xong khi smoke test xác nhận staging đang chạy đúng bản vừa build.

Đây là bài tích hợp sau [module 07 CI/CD & artifact](../../modules/07-cicd-artifacts/README.md): mục 1 (thiết kế
pipeline), mục 2 (quyền, concurrency, ghim action), mục 3 (act), mục 4 (tag bất biến, digest, promotion) và mục 5 (deploy,
rollback). Module 07 dừng ở "image lên registry"; ở đây pipeline đi tiếp tới một môi trường chạy thật, với những quyết định
mà module chỉ nói qua: không huỷ một lần deploy đang dở, quét chặn trước khi push, môi trường nhận digest chứ không nhận tag.

## Việc cần làm

Bạn viết `capstone/project/.github/workflows/ci.yml` và `capstone/project/ci/smoke-test.sh`, dùng lại nguyên
`capstone/project/container/` của M03.

**Cách test dựng repo.** Như M03: gốc repo là `olist_shop/`, `tests/`, `conftest.py`, `requirements.txt`,
`compose.yaml`, `.env.example` của sample-app, cộng `requirements-dev.txt` (`tests/fixtures/repo/requirements-dev.txt`:
pytest, fakeredis, httpx, pyyaml, ghim phiên bản) và các thư mục `container/`, `ci/`, `.github/` của bạn. Chỉ để đúng
một workflow `ci.yml` trong `.github/workflows/`: act chạy mọi workflow trong thư mục đó.

**Vì sao chạy được trên máy, phần nào không chạy.** Test chạy workflow bằng `act` qua `testkit.act_run`, giống module 07:
mỗi job là một container `devops-track/act-runner:1.0-<hash8>` (build theo mục 0 của module 07), ghim CPU, RAM 1 GB,
**không có socket Docker**, không ra được registry hay Docker của máy. Image runner đã có uv 0.10.8, CPython 3.12.13 và
wheel của Olist Shop nên job `test` không tải gì. Mọi bước đụng Docker (build, quét, push, compose, smoke test trên
staging) gắn `if: ${{ !env.ACT ... }}`: dưới act chúng bị bỏ qua và chỉ được **kiểm tĩnh** theo mục 1; **harness** làm thay
chúng ở mục 3, bằng đúng output của workflow và đúng tệp của bạn.

Mọi quy tắc dưới đây đều được chấm. Không có quy tắc chấm nào nằm ngoài tệp này.

### 1. `.github/workflows/ci.yml`: cấu trúc

Cấp workflow:

- Trigger: `push` với `branches: [main]` và `pull_request`; ngoài ra chỉ được thêm `workflow_dispatch`.
- `permissions` đúng bằng `contents: read`.
- `concurrency.group` chứa `github.ref`, `cancel-in-progress` đúng bằng `${{ github.event_name == 'pull_request' }}`:
  commit mới trên một PR huỷ lần chạy cũ của PR đó, nhưng không bao giờ huỷ pipeline của `main` đang deploy.
- `env.REGISTRY` khác rỗng (địa chỉ registry, ví dụ `localhost:15000`).
- Mọi `uses:` ghim theo commit SHA đủ 40 ký tự hex (`actions/checkout@3d3c42e5...`, không `@v6`).
- Có ba job `test`, `build`, `deploy-staging`, mỗi job `timeout-minutes` từ 1 tới 30.

Job `test`: không có quyền `write`; giữ nguyên hai bước **Cài uv** và **Cài Python và dependency** của starter module 07
Basic 01 (test so tên và nội dung `run:` sau khi bỏ khoảng trắng đầu cuối với tệp starter đó), và `env` của job có đủ bốn
biến của starter (`UV_VERSION`, `UV_SHA256_X86_64`, `UV_SHA256_AARCH64`, `PYTHON_VERSION`) với đúng giá trị; lý do ở mục
"Vì sao" của bài đó. Có bước `run:` chạy pytest (ví dụ `"$RUNNER_TEMP/venv/bin/python" -m pytest -q tests`).

Job `build`:

| Hạng mục | Quy tắc được chấm |
| --- | --- |
| Thứ tự, quyền | `needs: test`; `permissions` đúng bằng `contents: read` (hoặc `contents: read` cộng `packages: write` nếu bạn đẩy GHCR). |
| Tag | `outputs.tag` lấy từ `steps.<id>.outputs.tag` của một bước `run:` trong job. Bước đó tính tag từ `GITHUB_SHA` (`sha-` cộng 12 ký tự đầu), ghi vào `$GITHUB_OUTPUT`, in `devops-ex-output tag=<tag>` và `devops-ex-output revision=<GITHUB_SHA>`, và không chứa `date`, `run_number`, `run_id`, `run_attempt`, `latest`. |
| Build | Hai bước `docker/build-push-action`, một với `target: api`, một với `target: worker`; mỗi bước có `if:` mà act bỏ qua (`${{ !env.ACT }}`, có thể nối `&&`), `context: .`, `file: container/Dockerfile`, `load: true`, `push: false` (hoặc không khai), `tags` gồm `${{ env.REGISTRY }}`, `/<target>:` và `${{ steps.<id>.outputs.tag }}` (không `latest`), `build-args` có `APP_VERSION=${{ steps.<id>.outputs.tag }}` và `GIT_COMMIT=${{ github.sha }}`. |
| Quét | Với mỗi target, một bước `aquasecurity/trivy-action` có `if:` mà act bỏ qua, `image-ref` trỏ image `/<target>:` với tag ở trên, `trivy-config: container/trivy.yaml`; đứng **sau** bước build của target đó. Bước quét không đặt `severity`, `exit-code`, `ignore-unfixed`, `trivyignores`, `vuln-type`, `skip-dirs`, `skip-files`: chính sách chỉ đến từ `container/trivy.yaml` (trivy-action chạy ở gốc repo, nên `ignorefile: container/.trivyignore.yaml` của M03 tìm đúng tệp). |
| Push | Một bước `run:` chạy `docker push` cho cả hai image, hoặc một bước cho mỗi image. Mỗi bước có `if:` dạng `${{ !env.ACT && github.event_name == 'push' }}` (pull request build và quét nhưng không đẩy), đứng **sau** mọi bước quét, và ghi tham chiếu dạng `<registry>/<tên>@sha256:<digest>` vào `$GITHUB_OUTPUT` (script phải nhắc tới digest, ví dụ đọc `RepoDigests`). |
| Output | `outputs.api_image` và `outputs.worker_image` lấy từ `steps.<id>.outputs.*`, với `<id>` là `id` của một bước `docker push`. |

Job `deploy-staging`:

| Hạng mục | Quy tắc được chấm |
| --- | --- |
| Điều kiện | `needs: build`; `if:` có `github.event_name == 'push'`; `environment: staging` (chuỗi hoặc `name: staging`). |
| Không chồng deploy | `concurrency.group` chứa `staging`, `cancel-in-progress` không bật: deploy dở bị huỷ là staging nửa cũ nửa mới. |
| Quyền | `permissions` đúng bằng `contents: read`. |
| Deploy | Bước `run:` có `docker compose`, `-f container/compose.yaml`, `up` và `--wait`; `if:` mà act bỏ qua; `env` của bước có `OLIST_API_IMAGE: ${{ needs.build.outputs.api_image }}`, `OLIST_WORKER_IMAGE: ${{ needs.build.outputs.worker_image }}` và `POSTGRES_PASSWORD` lấy từ `secrets.*`. |
| Xác nhận | Bước `run:` gọi `ci/smoke-test.sh`, `if:` mà act bỏ qua, đứng sau bước deploy, nhận version mong đợi từ `needs.build.outputs.tag` (trong `run:` hoặc `env:` của bước). |

Thêm: `actionlint -shellcheck= -pyflakes=` không báo lỗi (test này skip khi chưa cài actionlint; cài theo mục 0 của module 07).

### 2. Chạy dưới act

Test gọi `act_run` với sự kiện `push` trên nhánh `main`:

- Repo đúng: ba job `test`, `build`, `deploy-staging` đều xanh (bước gắn `!env.ACT` bị bỏ qua); job `build` in `tag` và
  `revision`, `tag` đúng bằng `sha-<12 ký tự đầu của revision>`.
- Repo có thêm một test đỏ do harness cài (`tests/test_devops_ex_canary.py`): job `test` đỏ, `build` và `deploy-staging`
  không chạy, không có tag.

### 3. Harness làm phần Docker thay workflow

Dùng tag và revision từ lần chạy xanh, harness:

1. Build `container/Dockerfile` của bạn hai lần (`--target api`, `--target worker`) bằng `DockerLab.build` với
   `APP_VERSION=<tag>`, `GIT_COMMIT=<revision>`.
2. Đẩy hai image lên registry local bằng `DockerLab.push` thành `localhost:15000/devops-ex-<id>/<target>:<tag>`, hỏi API
   registry digest của từng tag và kiểm manifest tồn tại theo digest. Image theo digest phải mang nhãn
   `org.opencontainers.image.revision` bằng revision.
3. Deploy staging bằng `DockerLab.compose` trên `container/compose.yaml` của bạn với `OLIST_API_IMAGE`,
   `OLIST_WORKER_IMAGE` là hai tham chiếu **theo digest** (`localhost:15000/...@sha256:...`) và `POSTGRES_PASSWORD` ngẫu
   nhiên (ràng buộc và ghi đè của `DockerLab.compose` như M03, mục 2).
4. Chạy `ci/smoke-test.sh http://127.0.0.1:<cổng api> <tag>` với `SMOKE_TIMEOUT=60`: phải exit 0. Chạy lại với version
   `sha-000000000000` và `SMOKE_TIMEOUT=3`: phải exit 1. `GET /healthz` trả `version` bằng tag.

Image, manifest trên registry và mọi container bị xoá khi test xong. Registry local là service `registry` (profile
`devops`) trong `setup/docker-compose.yml`; chưa bật thì test này skip kèm lệnh bật.

### 4. `ci/smoke-test.sh`

```text
smoke-test.sh <base-url> <expected-version>
```

- Đúng hai tham số khác rỗng; sai số tham số hoặc một tham số là chuỗi rỗng thì exit 2, stderr bắt đầu bằng `Usage:`.
- Lặp tới khi đạt hoặc quá hạn `SMOKE_TIMEOUT` giây (biến môi trường, mặc định 60): đạt khi `GET <base-url>/healthz` trả
  200 với `version` đúng bằng `<expected-version>` **và** `GET <base-url>/readyz` trả 200.
- Đạt: exit 0, in một dòng bắt đầu bằng `OK`.
- Quá hạn: exit 1, in (stdout hoặc stderr) một dòng bắt đầu bằng `FAIL`; dòng `FAIL` cuối cùng nêu lý do: version sai
  thì có version đang chạy, chưa sẵn sàng thì có chữ `readyz`.
- Với `SMOKE_TIMEOUT=3`, script kết thúc trong dưới 23 giây kể cả khi không kết nối được (đặt timeout cho từng lần gọi).
- Qua `shellcheck -S style` không cảnh báo.

Test chạy script trong sandbox bubblewrap như M01 (env dựng từ đầu, chỉ có `PATH`, `HOME`, `SMOKE_TIMEOUT`), cần `curl` ≥
7.68 và `jq` ≥ 1.6. Ngoài staging ở mục 3, test dùng một API giả trên `127.0.0.1`: đúng version và `/readyz` chỉ trả 200
sau 2 giây (với `SMOKE_TIMEOUT=20`, phải exit 0); version sai; `/readyz` luôn 503; cổng không có gì nghe. Ba ca sau dùng
`SMOKE_TIMEOUT=3` và phải exit 1.

### 5. Chạy thử bằng act và chạy trên GitHub (tuỳ chọn)

Dựng repo giống test rồi chạy từng job, từ gốc repo (`ACT_RUNNER` đặt như lệnh build ở mục 0 của module 07):

```bash
APP=tracks/devops/sample-app && P="$PWD/tracks/devops/capstone/project" &&
DEST="$(mktemp -d)/olist-shop" && mkdir -p "$DEST" &&
cp -r "$APP"/{olist_shop,tests,conftest.py,requirements.txt,compose.yaml,.env.example} "$DEST/" &&
cp "$P/tests/fixtures/repo/requirements-dev.txt" "$DEST/" && cp -r "$P"/{container,ci,.github} "$DEST/" &&
find "$DEST" -name __pycache__ -prune -exec rm -rf {} + &&
cd "$DEST" && git init -q -b main && git add -A && git commit -qm "Olist Shop pipeline" &&
nice -n 15 act push -P ubuntu-latest="$ACT_RUNNER" --pull=false --container-daemon-socket - \
  ${DEVOPS_CPUSET:+--container-options "--cpuset-cpus=$DEVOPS_CPUSET"}
```

`REGISTRY: localhost:15000` chỉ đúng với runner chạy trên chính máy có registry (runner self-hosted cạnh staging). Trên
runner `ubuntu-latest` của GitHub, đổi `REGISTRY` sang `ghcr.io/<owner viết thường>`, thêm `docker/login-action` dùng
`secrets.GITHUB_TOKEN` (job `build` khi đó cần `packages: write`) và chạy job `deploy-staging` trên runner có Docker tới
được staging. Test không chấm phần này.

### 6. Chạy test

```bash
uv run pytest tracks/devops/capstone/project/tests -q -rs -k m04
```

Trên máy dùng chung, thêm `nice -n 15 ${DEVOPS_CPUSET:+taskset -c "$DEVOPS_CPUSET"}` trước `uv run`. Cần `act` ≥ 0.2.94,
image runner, Docker như M03 và registry local đang chạy; thiếu thứ nào thì riêng các test cần nó skip kèm lệnh cần chạy.
Test `test_m04_checks_catch_defective_workflow` đưa một workflow cẩu thả (`tests/fixtures/defective/ci.yml`) vào cùng phép
kiểm ở mục 1 và đòi bắt đủ lỗi; test này pass cả khi bạn chưa làm gì.

## Kết quả nộp

- `capstone/project/.github/workflows/ci.yml`
- `capstone/project/ci/smoke-test.sh`
- Mục "Pipeline" trong README của bạn: sơ đồ các job và điều kiện chạy; vì sao quét trước khi push; vì sao staging nhận
  digest chứ không nhận tag; quy trình rollback staging về bản trước (lấy digest ở đâu, chạy lệnh gì, mất bao lâu, đã đo
  một lần thật); và bước promote lên production sẽ trông thế nào (gắn thêm tag hay ghi digest vào cấu hình môi trường,
  không build lại).

## Tiêu chí đạt

- [ ] `uv run pytest tracks/devops/capstone/project/tests -q -rs -k m04` pass, không skip.
- [ ] Workflow: quyền tối thiểu, action ghim SHA, concurrency chỉ huỷ PR, tag `sha-<12 hex>` bất biến, build hai target
      một lần, quét bằng `container/trivy.yaml` trước khi push, push chỉ khi `push`, output là tham chiếu theo digest.
- [ ] Job `deploy-staging` có `environment: staging`, không chồng deploy, deploy compose theo digest, mật khẩu từ secret,
      smoke test sau deploy.
- [ ] Dưới act: code đúng thì ba job xanh; có test đỏ thì không build, không deploy.
- [ ] Staging do harness dựng từ image theo digest trả đúng version; `smoke-test.sh` xác nhận đúng bản và từ chối bản sai.
- [ ] (Tự đánh giá) Đã chạy workflow bằng act theo mục 5 và đọc được log từng job.
- [ ] (Tự đánh giá) README có mục "Pipeline" như phần Kết quả nộp, có số đo rollback thật.
