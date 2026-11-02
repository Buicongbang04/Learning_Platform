# M03: Container hoá, image tối ưu và đã quét lỗ hổng

## Mục tiêu

Sau M02, Olist Shop vẫn chạy bằng `Dockerfile` một stage của sample-app: image gần 900 MB, chạy bằng root, mang theo
compiler, và compose của sample-app build lại image ngay trên máy chạy. Không ai trả lời được "trên production đang chạy
đúng artifact nào, đã quét chưa". Milestone này biến Olist Shop thành **artifact** đúng nghĩa:

- Một `Dockerfile` multi-stage cho cả hai tiến trình (target `api` và `worker`), dependency build **một lần** ở stage
  chung, runtime chạy UID số khác 0, không compiler, có HEALTHCHECK dùng được thật, version và commit nằm trong image.
- Một compose **production** không build gì: chỉ chạy đúng image được chỉ định, root filesystem chỉ đọc, bỏ hết
  capability, Postgres và Redis không lộ ra máy host, mật khẩu không nằm trong tệp, log có xoay vòng.
- Một chính sách quét lỗ hổng bằng trivy chạy được trong CI (M04 dùng lại nguyên tệp), image không mang bí mật của máy dev.

Đây là bài tích hợp sau [module 06 Containers](../../modules/06-containers/README.md): mục 2 (layer, cache,
multi-stage), mục 3 (non-root, capability, rootfs chỉ đọc, giới hạn tài nguyên), mục 4 (PID 1, tín hiệu, HEALTHCHECK) và
mục 5 (tag, digest, quét lỗ hổng). Module làm từng mảnh trên image riêng lẻ; ở đây bạn làm cho hai tiến trình của cùng
một service, chạy chung một stack, và để lại thứ mà pipeline M04, Helm chart M06 dùng thẳng.

## Việc cần làm

Bạn viết các tệp trong `capstone/project/container/`. Ứng dụng vẫn là [sample-app](../../sample-app/README.md); bạn
không sửa code ứng dụng.

**Cách test dựng repo.** Test chép vào một thư mục tạm đúng bố cục của repo portfolio: ở gốc là `olist_shop/`, `tests/`,
`conftest.py`, `requirements.txt`, `compose.yaml` (compose dev của sample-app), `.env.example` của sample-app, cộng thư
mục `container/` (và `ci/`, `.github/` nếu có) của bạn. Gốc repo còn có một tệp `.env` giả lập máy dev, chứa một GitHub
token giả. **Không** có `.dockerignore` ở gốc: Dockerfile của bạn tự lo việc loại trừ (gợi ý: `container/Dockerfile.dockerignore`,
BuildKit đọc tệp ignore cạnh Dockerfile trước tệp ở gốc context).

Test build hai lần bằng `testkit.DockerLab.build` với context là **gốc repo**, `-f container/Dockerfile`,
`--target api` rồi `--target worker`, kèm `--build-arg APP_VERSION=m03-<ngẫu nhiên>` và
`--build-arg GIT_COMMIT=<40 ký tự hex ngẫu nhiên>`. Build chạy bằng BuildKit (driver `docker`), ghim CPU theo
`DEVOPS_CPUSET`, RAM 1 GB, `--pull=false`: mọi image nền trong các dòng `FROM` phải có sẵn trên máy, thiếu thì test skip
kèm lệnh `docker pull`. Lần build đầu cần mạng để tải gói pip; lỗi mạng thì skip, lần sau dùng cache của BuildKit.

Mọi quy tắc dưới đây đều được chấm. Không có quy tắc chấm nào nằm ngoài tệp này.

### 1. `container/Dockerfile`

Đọc tĩnh:

- Ít nhất 2 dòng `FROM` (stage cài dependency tách khỏi stage runtime), có stage tên `api` và stage tên `worker`
  (`FROM ... AS api`, `FROM ... AS worker`).
- Mọi image nền bên ngoài (không tính tên stage, `scratch`, tham chiếu `$ARG`) được **ghim**: tag có đủ
  `major.minor.patch` (ví dụ `python:3.12.16-slim-trixie`) hoặc digest `@sha256:<64 hex>`. `python:3.12-slim`, `latest`
  hay tag không có số đều trượt.

Chấm trên **từng** image `api` và `worker` đã build:

| Hạng mục | Quy tắc được chấm |
| --- | --- |
| Non-root | `Config.User` là UID **số** khác 0, có thể kèm GID (`10001` hoặc `10001:10001`): Kubernetes chỉ kiểm được `runAsNonRoot` khi USER là số (M06). Test chạy `python3 -c` trong image (entrypoint `python3`) và đòi `os.getuid() != 0`. |
| Không công cụ build | Không có `gcc`, `cc`, `g++`, `c++`, `make`, `ld` trong `PATH`. |
| PID 1 | `CMD`/`ENTRYPOINT` dạng exec: Docker không ghi lại thành `["/bin/sh", "-c", ...]`. |
| HEALTHCHECK | Image có `HEALTHCHECK`. Ở mục 2, cả `api` lẫn `worker` phải đạt `healthy` (gợi ý: worker phơi metrics ở cổng `9101`). |
| Nhãn OCI | `org.opencontainers.image.version` bằng build arg `APP_VERSION`, `org.opencontainers.image.revision` bằng build arg `GIT_COMMIT`. |
| Version trong image | Ở mục 2, `GET /healthz` trả `version` bằng `APP_VERSION` của lần build: version đi theo image, compose không đặt nó. |
| Không mang rác của repo | Không ở đâu trong image có tệp `.env` trùng nội dung `.env` của repo, hay `test_api.py`, `test_worker.py` trùng nội dung test của sample-app. |
| Kích thước | `Size` của `docker image inspect` tối đa **350 MB** (image nền `python:3.12.16-slim-trixie` khoảng 180 MB). |
| SBOM đọc được | `trivy image --format cyclonedx` (không cần DB lỗ hổng) liệt kê gói `pkg:pypi` với đúng phiên bản của `requirements.txt`: image `api` có `fastapi 0.143.1`, `uvicorn 0.54.0`, `psycopg 3.3.6`, `sqlalchemy 2.1.6`; image `worker` có `redis 8.1.0`, `sqlalchemy 2.1.6`, `prometheus-client 0.26.0`, `psycopg 3.3.6`. Chép `site-packages` mà bỏ `*.dist-info` là làm scanner mù. |
| Không bí mật | `trivy image --scanners secret` không tìm thấy bí mật nào. |

Và một quy tắc trên **cặp** image: `api` và `worker` dùng chung **một** bộ dependency. Test tìm thư mục `site-packages`
chứa gói `redis` trong mỗi image và so đường dẫn cùng danh sách tệp kèm kích thước và mtime: phải trùng khớp. Cài
dependency riêng trong từng target (hai lần `pip install`) là trượt, vì hai lần cài cho hai bộ tệp khác nhau, hai lần
quét, hai lần đẩy layer lên registry.

### 2. `container/compose.yaml`

Đây là compose chạy **artifact**, dùng cho production local, và là đúng tệp M04 dùng để deploy staging. Đọc tĩnh (YAML
sau khi giải anchor và `<<:` merge, trước khi thay biến):

| Hạng mục | Quy tắc được chấm |
| --- | --- |
| Service | Có `api`, `worker`, `postgres`, `redis` (thêm service khác được, miễn không mở cổng). |
| Image của app | `api.image` đúng dạng `${OLIST_API_IMAGE:?<thông báo>}`, `worker.image` đúng dạng `${OLIST_WORKER_IMAGE:?<thông báo>}`; không có `build:`. Thiếu biến thì compose dừng ngay thay vì chạy nhầm image cũ. |
| Image hạ tầng | `postgres`, `redis` ghim tag có ít nhất `major.minor` (`postgres:16.15-alpine`, `redis:7.4.12-alpine`) hoặc digest; không `latest`. Mỗi service có `healthcheck.test`. |
| Hardening `api`, `worker` | `read_only: true`; `tmpfs` có `/tmp`; `cap_drop: [ALL]`; `restart` là `unless-stopped`, `always` hoặc `on-failure`; có `deploy.resources.limits.memory`. |
| Thứ tự khởi động | `api` và `worker` có `depends_on` tới `postgres` và `redis` với `condition: service_healthy`. |
| Cấu hình | `api`, `worker` không đặt `APP_VERSION`; `DATABASE_URL` lấy mật khẩu từ `${POSTGRES_PASSWORD...}`. `postgres` đặt `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?<thông báo>}`. Không có mật khẩu dạng chữ nào trong tệp (ví dụ `olist:olist@`). |
| Dữ liệu | `postgres` mount named volume vào `/var/lib/postgresql/data`. |
| Cổng | Chỉ `api` mở cổng: đúng một mục, container `8000`, chỉ trên `127.0.0.1` (dạng `127.0.0.1:<cổng hoặc ${BIẾN}>:8000` hoặc dạng dài với `host_ip: 127.0.0.1`). `worker`, `postgres`, `redis` không mở cổng ra máy host. |
| Dừng sạch | `worker` có `stop_grace_period` từ `10s` trở lên: worker chỉ thấy SIGTERM sau lần `BLPOP` hiện tại (tối đa 5 giây). |
| Log | Mọi service có `logging.driver` là `json-file` hoặc `local` kèm `logging.options.max-size`. |

Rồi test dựng stack bằng `testkit.DockerLab.compose` với `OLIST_API_IMAGE`, `OLIST_WORKER_IMAGE` là hai image vừa build
và `POSTGRES_PASSWORD` là chuỗi hex ngẫu nhiên. `DockerLab.compose` chép thư mục `container/` sang thư mục tạm, xét cấu
hình theo allowlist (khoá như `privileged`, `cap_add`, `network_mode`, `secrets`, bind mount ra ngoài thư mục đều bị từ
chối kèm lý do; xem mục "Track DevOps" của `CONTENT_SPEC.md`), rồi ghi đè: ghim CPU, RAM 256 MB và giới hạn số tiến trình
cho mỗi service, `no-new-privileges`, cổng chuyển về `127.0.0.1:<cổng trống>`, bỏ `restart` và `container_name`,
`--pull never` (image `postgres`, `redis` bạn chọn phải có sẵn, thiếu thì skip kèm lệnh `docker pull`). Chạy
`up -d --wait`, rồi:

- `api` và `worker` ở trạng thái `running` và `healthy` (chờ thêm tối đa 60 giây).
- `GET /healthz` trả 200 với `version` bằng `APP_VERSION` của lần build; `GET /readyz` trả 200.
- `POST /jobs/recompute` trả 202; trong 30 giây, log của `worker` có một dòng chứa `job_id` đó và `job done`.
- `docker compose stop worker` xong thì `ExitCode` của worker là `0` (không phải 137 vì bị SIGKILL).

### 3. `container/trivy.yaml` và `container/.trivyignore.yaml`

Chính sách quét giống module 06 Intermediate 02, nhưng cho image của chính bạn, và cùng tệp đó chạy trong pipeline M04.
Đọc tĩnh:

- `trivy.yaml`: `severity` đúng `HIGH` và `CRITICAL`; `exit-code` là số khác 0; `vulnerability.ignore-unfixed: true`;
  `ignorefile: .trivyignore.yaml`; `scan.scanners` có `vuln` và `secret`.
- `.trivyignore.yaml` phải có, với khoá `vulnerabilities` là một danh sách (rỗng được). Mỗi mục có `id` dạng `CVE-...`
  hoặc `GHSA-...`, `purls` không rỗng, `statement` ít nhất 40 ký tự, `expired_at` dạng `YYYY-MM-DD`.

Rồi với từng image, test chạy `trivy image` hai lần với DB ở `~/.cache/devops-track/trivy` (`--skip-db-update
--offline-scan`, env dựng từ đầu, không đọc `TRIVY_*` hay cấu hình của máy), luôn với `--scanners vuln`: một lần đối chứng
không cấu hình, một lần với `trivy.yaml` và `.trivyignore.yaml` của bạn (chạy trong thư mục chứa hai tệp, `expired_at` bị
bỏ khỏi bản chép để bài không hỏng theo ngày). Gate của bạn phải:

- chỉ báo lỗ hổng `HIGH`/`CRITICAL` có trạng thái `fixed`;
- không che lỗ hổng `HIGH`/`CRITICAL` đã có bản vá nào mà lần đối chứng thấy, trừ mục khớp `id` và `purls` trong
  `.trivyignore.yaml`;
- trả mã khác 0 khi và chỉ khi còn lỗ hổng bị báo.

Test **không** đòi image sạch lỗ hổng và không đếm CVE: DB của trivy cập nhật nhiều lần mỗi ngày, image hôm nay sạch
mai có thể đỏ. Test chấm việc gate của bạn quyết định đúng theo chính sách. Gate đỏ trên image của bạn là thông tin, không
phải lỗi của test; xử lý nó là việc của bạn (mục "Kết quả nộp").

### 4. Chạy thử bằng tay

Chạy từ gốc repo, `DEVOPS_CPUSET` đặt theo [Ghim CPU](../../README.md#ghim-cpu-trên-máy-dùng-chung) (để trống nếu không
ghim). Dựng bản repo giống test rồi build hai target:

```bash
REV="$(git rev-parse HEAD)" && APP=tracks/devops/sample-app && P="$PWD/tracks/devops/capstone/project" &&
DEST="$(mktemp -d)/olist-shop" && mkdir -p "$DEST" &&
cp -r "$APP"/{olist_shop,requirements.txt} "$DEST/" && cp -r "$P/container" "$DEST/" && cd "$DEST" &&
for t in api worker; do
  nice -n 15 docker build ${DEVOPS_CPUSET:+--cpuset-cpus "$DEVOPS_CPUSET"} --pull=false -f container/Dockerfile \
    --target "$t" --build-arg APP_VERSION=local-1 --build-arg GIT_COMMIT="$REV" -t "olist-shop/$t:local-1" . || break
done && docker image ls olist-shop
```

Chạy stack production (dừng stack dev của M01 trước nếu cổng `28000` đang bận) rồi kiểm:

```bash
OLIST_API_IMAGE=olist-shop/api:local-1 OLIST_WORKER_IMAGE=olist-shop/worker:local-1 \
POSTGRES_PASSWORD="$(openssl rand -hex 16)" \
  docker compose -p olist-shop-prod -f container/compose.yaml up -d --wait &&
curl -s 127.0.0.1:28000/healthz && curl -s 127.0.0.1:28000/readyz &&
docker compose -p olist-shop-prod -f container/compose.yaml ps
```

Quét bằng chính sách của bạn (chạy trong `container/` để `ignorefile` tìm thấy tệp ngoại lệ):

```bash
cd container && for t in api worker; do
  nice -n 15 trivy image --config trivy.yaml --cache-dir ~/.cache/devops-track/trivy "olist-shop/$t:local-1"
  echo "gate $t: mã thoát $?"
done; cd ..
```

Dọn khi xong:

```bash
docker compose -p olist-shop-prod -f container/compose.yaml down -v && docker image rm olist-shop/api:local-1 olist-shop/worker:local-1
```

### 5. Chạy test

```bash
uv run pytest tracks/devops/capstone/project/tests -q -rs -k m03
```

Trên máy dùng chung, thêm `nice -n 15 ${DEVOPS_CPUSET:+taskset -c "$DEVOPS_CPUSET"}` trước `uv run`. Test cần Docker
(compose ≥ 2.24.4, buildx với builder driver `docker`), các image nền và image `postgres`, `redis` bạn chọn đã pull, trivy
≥ 0.76 (cài theo mục 0 của module 06) và DB của trivy; thiếu thứ nào thì riêng các test cần nó skip kèm lệnh cần chạy. Test
`test_m03_checks_catch_defective` build Dockerfile lỗi trong `tests/fixtures/defective/container/` và chứng minh các phép
kiểm ở trên bắt được lỗi của nó; test này pass cả khi bạn chưa làm gì.

## Kết quả nộp

- `capstone/project/container/Dockerfile` (cộng `Dockerfile.dockerignore` nếu bạn dùng)
- `capstone/project/container/compose.yaml`
- `capstone/project/container/trivy.yaml`, `capstone/project/container/.trivyignore.yaml`
- Mục "Container" trong README của bạn: sơ đồ các stage và target; bảng kích thước, số gói (SBOM) và kết quả gate của
  image cũ (Dockerfile của sample-app) so với `api`, `worker`; image nền đã chọn và vì sao (slim, alpine hay distroless,
  với musl và wheel của `psycopg`); mỗi khoá hardening trong compose chặn loại tấn công hay sự cố nào; quy trình khi gate đỏ
  (nâng image nền, nâng gói, hay ngoại lệ có hạn kèm lý do), kèm một lần bạn đã thực sự làm.

## Tiêu chí đạt

- [ ] `uv run pytest tracks/devops/capstone/project/tests -q -rs -k m03` pass, không skip.
- [ ] Dockerfile multi-stage có target `api`, `worker`, image nền ghim; dependency build một lần và dùng chung.
- [ ] Hai image: UID số khác 0, không compiler, exec form, HEALTHCHECK đạt `healthy`, nhãn OCI version và revision,
      không `.env` hay test, ≤ 350 MB, SBOM thấy đủ gói Python, không bí mật.
- [ ] Compose production chỉ chạy image truyền vào, không build, rootfs chỉ đọc, `cap_drop: [ALL]`, giới hạn RAM, chỉ API
      mở cổng trên `127.0.0.1`, mật khẩu từ biến bắt buộc, healthcheck và `service_healthy`, log xoay vòng.
- [ ] Stack trả đúng version, `/readyz` 200, worker xử lý job và dừng với mã 0.
- [ ] Gate trivy chặn đúng `HIGH`/`CRITICAL` đã có bản vá, không che gì ngoài ngoại lệ đã khai, mã thoát khớp kết quả.
- [ ] (Tự đánh giá) Đã chạy vòng thật ở mục 4 và so được image cũ với image mới bằng số liệu.
- [ ] (Tự đánh giá) README có mục "Container" như phần Kết quả nộp.
