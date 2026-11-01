# Công cụ cho track DevOps

Mục lục các công cụ ngoài `uv` và Docker mà track DevOps cần. Mỗi công cụ được dạy cài ở đúng module dùng nó lần đầu, trong phần `## 0. Cài đặt` (bảng phiên bản đã kiểm, lệnh tải, kiểm checksum, cài vào `~/.local/bin`, lệnh xác nhận, cách gỡ). Bài tập thiếu công cụ hoặc công cụ cũ hơn mức tối thiểu sẽ `skip` kèm lời nhắc trỏ về tệp này, không `fail`.

| Công cụ | Module dạy cài | Phiên bản tối thiểu | Hướng dẫn cài |
|---|---|---|---|
| docker | Có sẵn từ đầu, xem [SETUP.md](SETUP.md) | 24.0 | [SETUP.md](SETUP.md) |
| shellcheck | 01 Linux & terminal | 0.9.0 | [Cài đặt](../tracks/devops/modules/01-linux-terminal/README.md#0-cài-đặt) |
| jq | 01 Linux & terminal | 1.6 | [Cài đặt](../tracks/devops/modules/01-linux-terminal/README.md#0-cài-đặt) |
| curl | Có sẵn trên hầu hết distro | 7.68 | Không cần cài |
| bubblewrap (`bwrap`) | 02 Scripting & lập trình (sandbox cho test chạy script của bạn) | 0.5.0 | [Cài đặt](../tracks/devops/modules/02-scripting/README.md#0-cài-đặt) |
| flock, sha256sum | Có sẵn trên Linux (util-linux, coreutils); dùng từ 02 Scripting & lập trình | Không đặt | Không cần cài; macOS không có `flock`, xem [Cài đặt](../tracks/devops/modules/02-scripting/README.md#0-cài-đặt) |
| git | Có sẵn trên mọi distro; dùng từ 03 Git & VCS hosting | 2.30 | [Cài đặt](../tracks/devops/modules/03-git-vcs-hosting/README.md#0-cài-đặt) |
| openssl | 04 Networking & protocols | 1.1.1 | [Cài đặt](../tracks/devops/modules/04-networking-protocols/README.md#0-cài-đặt) |
| dig | 04 Networking & protocols (tuỳ chọn, không bài nào bắt buộc) | 9.16 | [Cài đặt](../tracks/devops/modules/04-networking-protocols/README.md#0-cài-đặt) |
| ssh (OpenSSH client) | Có sẵn trên hầu hết distro; dùng từ 04 Networking & protocols | 8.0 | [Cài đặt](../tracks/devops/modules/04-networking-protocols/README.md#0-cài-đặt) |
| nginx (image Docker `nginx:1.30.6-alpine`, kèm `python:3.12.16-alpine3.24` cho backend giả) | 05 Web server & proxy (chạy trong container, không cài lên máy) | Đúng tag đã ghim | [Cài đặt](../tracks/devops/modules/05-web-server-proxy/README.md#0-cài-đặt) |
| docker buildx (BuildKit, builder driver `docker`), image `python:3.12.16-slim-trixie`, `gcr.io/distroless/python3-debian13:nonroot` | 06 Containers (build image trong test bằng BuildKit của Docker) | buildx có sẵn trong Docker Engine; image đúng tag/digest đã ghim | [Cài đặt](../tracks/devops/modules/06-containers/README.md#0-cài-đặt) |
| trivy (kèm DB lỗ hổng ở `~/.cache/devops-track/trivy`) | 06 Containers | 0.76 | [Cài đặt](../tracks/devops/modules/06-containers/README.md#0-cài-đặt) |
| act | 07 CI/CD & artifacts (chạy workflow GitHub Actions trên máy; image runner `devops-track/act-runner:1.0-9d5fff50` (đuôi là hash của Dockerfile và requirements-ci.txt, đổi khi hai tệp đổi) build một lần từ `setup/act-runner/` trên `node:24.22.2-trixie-slim`, có sẵn uv, CPython 3.12.13 và wheel nên chấm offline; cache action ở `~/.cache/devops-track/act`) | 0.2.94 | [Cài đặt](../tracks/devops/modules/07-cicd-artifacts/README.md#0-cài-đặt) |
| actionlint | 07 CI/CD & artifacts (kiểm tĩnh workflow; thiếu thì riêng test actionlint skip) | 1.7 | [Cài đặt](../tracks/devops/modules/07-cicd-artifacts/README.md#0-cài-đặt) |
| tofu (OpenTofu) | 08 IaC & provisioning (bản đã kiểm 1.13.2; test chạy `tofu` trong sandbox với LocalStack riêng `localstack-devops`, provider `hashicorp/aws` 6.12.0 tải một lần vào `~/.cache/devops-track/tofu-plugins` rồi dùng offline) | 1.10 | [Cài đặt](../tracks/devops/modules/08-iac-provisioning/README.md#0-cài-đặt) |

Các dòng của module chưa viết sẽ được liên kết đầy đủ khi module đó có mặt trong repo.

## Dịch vụ phụ trợ: Mailpit

Module 04 cần một máy chủ SMTP giả để kiểm thư gửi ra. Mailpit nằm trong profile `devops` của `setup/docker-compose.yml` và không thuộc profile `all`, nên bật `all` của track Data Engineer không kéo nó lên.

```bash
docker compose -f setup/docker-compose.yml --profile devops up -d mailpit
docker compose -f setup/docker-compose.yml --profile devops stop mailpit
docker compose -f setup/docker-compose.yml --profile devops rm -f mailpit
```

SMTP ở `localhost:11025`, giao diện web và API (`GET /api/v1/messages`) ở `localhost:18025`, cả hai chỉ mở trên `127.0.0.1`. Đổi cổng bằng `MAILPIT_SMTP_PORT` và `MAILPIT_HTTP_PORT` trong `setup/.env` khi cổng đã bị dự án khác dùng.

## Dịch vụ phụ trợ: registry local

Module 07 và capstone m04 push, pull image qua một registry Docker chạy trên máy (`registry:2.8.3`), cũng trong profile `devops` và không thuộc `all`.

```bash
docker compose -f setup/docker-compose.yml --profile devops up -d registry
docker compose -f setup/docker-compose.yml --profile devops stop registry
docker compose -f setup/docker-compose.yml --profile devops rm -fsv registry
```

Registry ở `localhost:15000`, chỉ mở trên `127.0.0.1`; Docker cho push lên `localhost` qua HTTP mà không cần cấu hình `insecure-registries`. Đổi cổng bằng `DEVOPS_REGISTRY_PORT` trong `setup/.env`. Registry bật `REGISTRY_STORAGE_DELETE_ENABLED` để test xoá được image đã push: test đặt image dưới tên `devops-ex-<id>/...` và xoá manifest khi xong. Tên repository rỗng vẫn hiện trong `/v2/_catalog` tới khi xoá volume bằng lệnh `rm -fsv` ở trên.

## Dịch vụ phụ trợ: LocalStack riêng cho IaC

Module 08 và capstone m05 tạo bucket S3, bảng DynamoDB, IAM role, khoá KMS... bằng OpenTofu trên một LocalStack riêng của track DevOps: service `localstack-devops` (cùng image `localstack/localstack:4.4.0` với track DE, bản community không cần `LOCALSTACK_AUTH_TOKEN`), profile `devops`, không thuộc `all`. Nó tách hẳn service `localstack` của track Data Engineer: cổng khác, volume khác (`devops-track-localstack-data`), nên bài DevOps không bao giờ đụng dữ liệu của DE.

```bash
docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
docker compose -f setup/docker-compose.yml --profile devops stop localstack-devops
docker compose -f setup/docker-compose.yml --profile devops rm -fsv localstack-devops
docker volume rm devops-track-localstack-data
```

Endpoint ở `http://127.0.0.1:14566`, chỉ mở trên `127.0.0.1`; đổi cổng bằng `LOCALSTACK_DEVOPS_PORT` trong `setup/.env` (không được trùng `LOCALSTACK_PORT` của DE, test sẽ từ chối). Service bật S3, IAM, STS, DynamoDB, KMS, SSM và Secrets Manager. Lần chạy test đầu tiên tải provider `hashicorp/aws` 6.12.0 (khoảng 150 MB, giải nén khoảng 780 MB) vào `~/.cache/devops-track/tofu-plugins`; từ đó test chạy offline. Provider mới hơn 6.12 chưa chạy được với LocalStack 4.4.0 (bảng DynamoDB, tag bucket S3), nên bài tập ghim đúng bản này.

## Ghim CPU

Biến `DEVOPS_CPUSET` quyết định container của track DevOps (compose, test bài tập, hướng dẫn khởi chạy) chạy trên những core nào.

- Đặt `DEVOPS_CPUSET` thành một dải core của máy bạn để ghim container vào dải đó. Xem số core bằng `nproc`, chừa vài core đầu cho việc khác, ví dụ máy 8 core đặt `2-7`, máy 36 core dùng chung đặt `12-35`. Dải phải nằm trong số core của máy, nếu không Docker và `taskset` từ chối chạy.
- Không muốn ghim (máy ít core): `unset DEVOPS_CPUSET` hoặc để trống. Đừng đặt một giá trị chữ nào khác dải core: compose truyền nguyên giá trị cho Docker, và Docker từ chối tạo container.
- Không đặt gì: `testkit.docker_cpu_args()` chỉ ghim `12-35` khi máy có từ 36 core trở lên, máy ít core hơn thì bỏ qua. Trong compose, giá trị rỗng nghĩa là không ghim.

Nên ghim để một bài tập nặng không chiếm hết core bạn đang dùng cho việc khác.

`nice` và `taskset` chỉ áp dụng cho tiến trình bạn chạy trực tiếp, tức là client `docker`. Container do Docker daemon (`dockerd` và `containerd`) sinh ra, nằm ngoài cây tiến trình của lệnh bạn gõ, nên không kế thừa độ ưu tiên và affinity. Muốn giới hạn container phải dùng `--cpuset-cpus` của Docker (hoặc `cpuset` trong compose), cộng với `--cpus` nếu cần giới hạn theo thời gian CPU. Trong thực tế dùng cả hai: `nice -n 15 taskset -c "$DEVOPS_CPUSET"` cho các bước build và test chạy ngoài container (không ghim thì chỉ `nice -n 15`), `--cpuset-cpus` cho chính container.

Container đã chạy mà quên ghim thì ghim sau, không cần tạo lại:

```bash
docker update --cpuset-cpus "$DEVOPS_CPUSET" <container>
```
