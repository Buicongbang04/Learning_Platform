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
| act | 07 CI/CD & artifacts (chạy workflow GitHub Actions trên máy; image runner `devops-track/act-runner:1.0-a5037b3b` (đuôi là hash của Dockerfile và requirements-ci.txt, đổi khi hai tệp đổi) build một lần từ `setup/act-runner/` trên `node:24.22.2-trixie-slim`, có sẵn uv, CPython 3.12.13 và wheel nên chấm offline; cache action ở `~/.cache/devops-track/act`) | 0.2.94 | [Cài đặt](../tracks/devops/modules/07-cicd-artifacts/README.md#0-cài-đặt) |
| actionlint | 07 CI/CD & artifacts (kiểm tĩnh workflow; thiếu thì riêng test actionlint skip) | 1.7 | [Cài đặt](../tracks/devops/modules/07-cicd-artifacts/README.md#0-cài-đặt) |
| tofu (OpenTofu) | 08 IaC & provisioning (bản đã kiểm 1.13.2; test chạy `tofu` trong sandbox với LocalStack riêng `localstack-devops`, provider `hashicorp/aws` 6.12.0 tải một lần vào `~/.cache/devops-track/tofu-plugins` rồi dùng offline; trivy của module 06 quét chính sách ở Intermediate 04) | 1.10 (1.11 cho biến `ephemeral`: Basic 02, capstone m05) | [Cài đặt](../tracks/devops/modules/08-iac-provisioning/README.md#0-cài-đặt) |
| ansible-core (`ansible`, `ansible-playbook`, `ansible-inventory`, `ansible-vault`...) | 09 Configuration management (bản đã kiểm 2.21.5, cài vào venv riêng `~/.cache/devops-track/ansible` bằng `uv pip install --require-hashes -r setup/ansible/requirements.txt`, symlink vào `~/.local/bin`; không thêm vào `pyproject.toml` gốc; test chạy Ansible trong sandbox tới target là container SSH build từ `setup/ansible-target/` trên `python:3.12.16-slim-trixie`) | 2.21 | [Cài đặt](../tracks/devops/modules/09-config-management/README.md#0-cài-đặt) |
| kind | 10 Kubernetes core (cluster dùng chung `devops-lab`, xem [Cluster kind devops-lab](#cluster-kind-devops-lab)) | 0.30.0 (node image ghim `kindest/node:v1.34.0` theo digest) | [Cài đặt](../tracks/devops/modules/10-kubernetes-core/README.md#0-cài-đặt) |
| kubectl | 10 Kubernetes core (bản đã kiểm 1.34.13, khớp minor của node image) | 1.33 (lệch tối đa một minor với API server 1.34) | [Cài đặt](../tracks/devops/modules/10-kubernetes-core/README.md#0-cài-đặt) |
| helm | 11 Kubernetes production (bản đã kiểm 3.22.1; Kustomize có sẵn trong kubectl) | 3.18 | [Cài đặt](../tracks/devops/modules/11-kubernetes-production/README.md#0-cài-đặt) |
| metrics-server (trong cluster, không cài lên máy) | 11 Kubernetes production (HPA, `kubectl top`; bản 0.9.1 ghim trong `setup/kind/metrics-server/`, xem [metrics-server dùng chung](#metrics-server-dùng-chung)) | Đúng bản đã ghim | [Cài đặt](../tracks/devops/modules/11-kubernetes-production/README.md#0-cài-đặt) |
| sops | 12 GitOps & secrets (bản đã kiểm 3.13.3, binary chính thức từ GitHub release, kiểm SHA-256 theo `sops-v3.13.3.checksums.txt`; test chạy `sops` trong sandbox với `sops_env`, không đọc `~/.config/sops` hay `SOPS_*` của máy) | 3.9 | [Cài đặt](../tracks/devops/modules/12-gitops-secrets/README.md#0-cài-đặt) |
| age, age-keygen | 12 GitOps & secrets (bản đã kiểm 1.3.2; khoá của bài sinh bằng `age_keypair` trong sandbox, nằm ngoài repo và ngoài project của bạn) | 1.2 | [Cài đặt](../tracks/devops/modules/12-gitops-secrets/README.md#0-cài-đặt) |
| Vault (image `hashicorp/vault:2.2.1` ghim digest, chạy dev mode trong compose, xem [Vault dev](#dịch-vụ-phụ-trợ-vault-dev)) | 12 GitOps & secrets | Đúng tag đã ghim | [Cài đặt](../tracks/devops/modules/12-gitops-secrets/README.md#0-cài-đặt) |
| vault (CLI) | 12 GitOps & secrets (bản đã kiểm 2.2.1 từ releases.hashicorp.com, kiểm SHA-256 theo `vault_2.2.1_SHA256SUMS`; test chạy `vault` trong sandbox với `vault_env`, không đọc `VAULT_*` hay `~/.vault-token` của máy) | 1.15 | [Cài đặt](../tracks/devops/modules/12-gitops-secrets/README.md#0-cài-đặt) |
| argocd (CLI, tuỳ chọn) | 12 GitOps & secrets (bản đã kiểm 3.5.6, kiểm SHA-256 theo `cli_checksums.txt`; không bài nào cần: bản core của track không có API server, và `argocd --core` v3.5.6 không đọc được Application ngoài namespace `argocd`, nên trạng thái đọc bằng `kubectl`) | Không đặt | [Cài đặt](../tracks/devops/modules/12-gitops-secrets/README.md#0-cài-đặt) |
| ArgoCD và git server (trong cluster, không cài lên máy) | 12 GitOps & secrets (ArgoCD v3.5.6 bản core ghim trong `setup/kind/argocd/`, sidecar CMP `sops-kustomize`, git server chỉ đọc trong `devops-git`; xem [ArgoCD và git server dùng chung](#argocd-và-git-server-dùng-chung)) | Đúng bản đã ghim | [Cài đặt](../tracks/devops/modules/12-gitops-secrets/README.md#0-cài-đặt) |
| linkerd (CLI, tuỳ chọn) | 15 Service mesh & patterns (bản đã kiểm edge-26.10.1, kiểm SHA-256 theo digest của asset trên GitHub release vì release của Linkerd không kèm tệp checksum; test không gọi `linkerd`, CLI chỉ để xem tay bằng kubeconfig admin, ví dụ `linkerd --kubeconfig ~/.kube/devops-lab.yaml check`) | Không đặt | [Cài đặt](../tracks/devops/modules/15-service-mesh-patterns/README.md#0-cài-đặt) |
| Linkerd (trong cluster, không cài lên máy) | 15 Service mesh & patterns (edge-26.10.1, control plane cộng linkerd-cni render sẵn trong `setup/kind/linkerd/`, chứng chỉ do admin sinh bằng `certs.sh`; xem [Linkerd dùng chung](#linkerd-dùng-chung)) | Đúng bản đã ghim | [Cài đặt](../tracks/devops/modules/15-service-mesh-patterns/README.md#0-cài-đặt) |
| Stack observability (image Docker ghim digest: OTel Collector contrib 0.163.2, Jaeger 2.22.0, Loki 3.7.9, Prometheus v3.5.0, Alertmanager v0.34.1, Grafana 13.2.5; xem [Stack observability](#stack-observability)) | 13 Observability (chạy trong container bằng `testkit.ObsStack`, không cài lên máy) | Đúng tag và digest đã ghim | [Stack observability](#stack-observability) |
| promtool, amtool | 13 Observability (chạy trong image Prometheus, Alertmanager ghim qua `testkit.promtool`/`amtool`, không cần cài; muốn gõ tay thì dùng `docker run` ở [Stack observability](#stack-observability)) | Đúng bản trong image | [Stack observability](#stack-observability) |
| logcli (tuỳ chọn) | 13 Observability (bản đã kiểm 3.7.9, cùng bản Loki của stack, kiểm SHA-256 theo `SHA256SUMS` của release; không bài nào cần, chỉ để chạy LogQL từ terminal) | 3.0 | [Cài đặt](../tracks/devops/modules/13-observability/README.md#0-cài-đặt) |
| Image Lambda `public.ecr.aws/lambda/python:3.12.2026.10.22.03` ghim digest (có Runtime Interface Emulator, chạy handler qua `LambdaLab`, xem [Lambda local: LambdaLab](#lambda-local-lambdalab)) | 14 Cloud & serverless | Đúng tag đã ghim | [Cài đặt](../tracks/devops/modules/14-cloud-serverless/README.md#0-cài-đặt) |
| AWS CLI v2 (`aws`, tuỳ chọn) | 14 Cloud & serverless (bản đã kiểm 2.38.6, cài vào `~/.local/aws-cli` từ zip chính thức, kiểm chữ ký PGP của AWS CLI Team và SHA-256; test không cần, chỉ để chạy tay trên LocalStack hay làm lab AWS thật) | 2.x | [Cài đặt](../tracks/devops/modules/14-cloud-serverless/README.md#0-cài-đặt) |

Các dòng của module chưa viết sẽ được liên kết đầy đủ khi module đó có mặt trong repo.

## Binary dùng chung với track MLOps

act, kind và kubectl của track DevOps cài vào `~/.local/bin`, đúng chỗ track MLOps cài bản của nó. Trên một máy chỉ có một bản
của mỗi công cụ: cài sau thì ghi đè bản cài trước, gỡ là gỡ luôn bản track kia đang dùng.

| Binary | Track DevOps (đã kiểm / tối thiểu) | Track MLOps (đã kiểm / tối thiểu) | Ai ghi vào `~/.local/bin` |
|---|---|---|---|
| act | 0.2.94 / 0.2.94 | 0.2.94 / 0.2.80 | Module 07 của DevOps, module 08 của MLOps |
| kind | 0.30.0 / 0.30 | 0.33.0 | Module 10 của DevOps, `setup/mlops/kind/up.sh` (cài khi checksum của bản đang có không khớp 0.33.0) |
| kubectl | 1.34.13 / 1.33 | 1.35.8 | Module 10 của DevOps, `setup/mlops/kind/up.sh` (như trên) |

Hệ quả:

- act: hai track cài cùng bản 0.2.94 nên không giẫm lên nhau. Máy còn act cũ hơn 0.2.94 (ví dụ 0.2.89 theo hướng dẫn MLOps cũ) thì
  mọi bài DevOps chạy act (module 07, capstone m04) skip với thông báo `act 0.2.89 cũ hơn 0.2.94`; cài lại theo module 07 là hết.
- kubectl 1.35.8 vẫn trong mức lệch một minor với API server 1.34 của `devops-lab`, và đạt `KUBECTL_MIN_VERSION` nên test DevOps
  chạy tiếp.
- kind 0.33.0 qua được kiểm phiên bản tối thiểu của test DevOps (0.30), nhưng **chưa được kiểm** với `setup/kind/devops-lab.yaml`
  và node image `kindest/node:v1.34.0` ghim cho kind 0.30.0 (tạo cluster, kindnet thực thi NetworkPolicy, nạp image). Gặp lỗi khi
  tạo hay dùng `devops-lab` bằng kind 0.33.0 thì cài lại 0.30.0 theo module 10. `up.sh` của MLOps sẽ lại ghi đè bằng 0.33.0 ở lần
  chạy sau.
- Lệnh gỡ `rm -f ~/.local/bin/act`, `rm -f ~/.local/bin/kind ~/.local/bin/kubectl` trong module 07, 10 xoá cả bản track MLOps đang
  dùng. Còn học MLOps thì đừng gỡ, hoặc cài lại theo hướng dẫn của track đó.
- Prometheus và Alertmanager không phải binary trên máy mà là image Docker: track DevOps dùng đúng `prom/prometheus:v3.5.0` và
  `prom/alertmanager:v0.34.1` như track MLOps (cùng digest), nên không tải thêm và không hạ bản nào. `promtool`, `amtool` của
  hai track đều chạy trong hai image này. Đừng `docker image rm` hai image khi còn học track kia.

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

Module 08, 14 và capstone m05 tạo bucket S3, bảng DynamoDB, IAM role, khoá KMS, hàng đợi SQS... bằng OpenTofu trên một LocalStack riêng của track DevOps: service `localstack-devops` (cùng image `localstack/localstack:4.4.0` với track DE, bản community không cần `LOCALSTACK_AUTH_TOKEN`), profile `devops`, không thuộc `all`. Nó tách hẳn service `localstack` của track Data Engineer: cổng khác, volume khác (`devops-track-localstack-data`), nên bài DevOps không bao giờ đụng dữ liệu của DE.

```bash
docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
docker compose -f setup/docker-compose.yml --profile devops stop localstack-devops
docker compose -f setup/docker-compose.yml --profile devops rm -fsv localstack-devops
docker volume rm devops-track-localstack-data
```

Endpoint ở `http://127.0.0.1:14566`, chỉ mở trên `127.0.0.1`; đổi cổng bằng `LOCALSTACK_DEVOPS_PORT` trong `setup/.env` (không được trùng `LOCALSTACK_PORT` của DE, test sẽ từ chối). Service bật S3, IAM, STS, DynamoDB, KMS, SSM, Secrets Manager, SQS, EventBridge (`events`) và API Gateway REST (v1; API Gateway v2/HTTP API chỉ có ở bản Pro). Integration HTTP của API Gateway và API destination của EventBridge khiến chính `localstack-devops` gửi request ra ngoài tới URL do cấu hình chỉ định (bề mặt SSRF từ máy của bạn), nên bài tập không dùng hai tính năng này. Không bật Lambda và không mount socket Docker: LocalStack cần socket Docker để chạy code Lambda, tức là quyền root trên máy. LocalStack 4.4.0 vẫn nạp API `lambda` vì Secrets Manager phụ thuộc nó (rotation), nhưng function tạo ra luôn ở trạng thái `Failed` và không invoke được; code Lambda chạy trong `LambdaLab` (mục dưới). Đổi danh sách service chỉ cần tạo lại container, không cần xoá volume (không bật `PERSISTENCE`, tài nguyên chỉ nằm trong RAM; volume chỉ giữ cache):

```bash
docker compose -f setup/docker-compose.yml --profile devops rm -s -f localstack-devops && docker compose -f setup/docker-compose.yml --profile devops up -d --wait localstack-devops
```

RAM đo 2026-11-11 (`docker stats`, đã bật đủ service ở trên): khoảng 440 MB. Lần chạy test đầu tiên (cần mạng) tự tải đúng provider `hashicorp/aws` 6.12.0 (khoảng 150 MB, giải nén khoảng 780 MB) vào `~/.cache/devops-track/tofu-plugins`; từ đó test chạy offline. Provider mới hơn 6.12 chưa chạy được với LocalStack 4.4.0 (bảng DynamoDB, tag bucket S3), nên test chỉ cài bản này: ràng buộc như `~> 6.0` vẫn ra 6.12.0, ràng buộc loại trừ 6.12.0 thì test báo lỗi kèm lý do.

## Lambda local: LambdaLab

Module 14 chạy handler Lambda Python của người học bằng image Lambda chính thức của AWS (có sẵn Runtime Interface Emulator),
ghim theo tag có ngày và digest (bản 2026-10-22, Python 3.12.15, boto3 1.42.97). Tải một lần (khoảng 750 MB trên đĩa):

```bash
nice -n 15 docker pull public.ecr.aws/lambda/python:3.12.2026.10.22.03@sha256:25aee9bac65f131c5d090d3e3a36ccf232d65cf3e6c1dbd0bffd43ca7ce34406
```

Mỗi `LambdaLab` là một container chạy một mình trên một network Docker `--internal` riêng (`devops-ex-<id>-lambda-net`):
code mount chỉ đọc, filesystem chỉ đọc, không có socket Docker, credential giả `test`/`test`, `AWS_ENDPOINT_URL` trỏ
`localstack-devops`. Network internal nên handler không ra được Internet và không thấy container khác của bài; test gọi
handler thẳng qua IP container. Bài cần handler nói chuyện với container khác của lab (ví dụ Postgres thay RDS) dùng
`isolated=False`: khi đó container nằm trên network của lab và ra được Internet như mọi container của `DockerLab`. Dù
cách nào, container vẫn tới được các cổng mà máy mở trên `0.0.0.0` (qua IP gateway), như mọi container Docker. Credential
giả và endpoint bị ép chỉ bảo đảm client AWS mặc định gọi LocalStack và không có credential thật để lộ; đó không phải rào
mạng.

Container không tới được `127.0.0.1:14566` của máy, nên testkit mở một bộ chuyển tiếp TCP trong tiến trình pytest, nghe trên
IP gateway của network Lambda (dạng `172.x.0.1`) ở một cổng trong dải cố định `DEVOPS_LAMBDA_FORWARD_PORTS` (mặc định
`47100-47199`, đổi trong `setup/.env` hay env khi chạy pytest), chỉ nhận kết nối từ subnet đó, tối đa 64 kết nối cùng lúc,
và chỉ sống trong lúc test chạy. Nếu tường lửa của máy chặn container nói chuyện với IP gateway, test LambdaLab skip kèm lý do.
Cách đơn giản nhất là bỏ qua các bài này. Muốn chạy thì mở **đúng dải cổng đó, chỉ TCP, chỉ từ dải network Docker mặc định**:

```bash
sudo ufw allow proto tcp from 172.16.0.0/12 to any port 47100:47199
sudo ufw delete allow proto tcp from 172.16.0.0/12 to any port 47100:47199
sudo firewall-cmd --zone=docker --add-port=47100-47199/tcp
sudo firewall-cmd --zone=docker --remove-port=47100-47199/tcp
```

Luật này cho mọi địa chỉ trong `172.16.0.0/12` (mọi container Docker, và cả máy trong mạng LAN nếu LAN của bạn dùng dải
này) kết nối tới các cổng 47100-47199 của máy. Bình thường không có gì nghe ở đó ngoài bộ chuyển tiếp lúc test chạy; nhưng
nếu một chương trình khác dùng cổng trong dải này, nó cũng bị lộ. Đừng mở rộng thành `allow from 172.16.0.0/12` (mở mọi cổng
của máy). Xoá luật (dòng thứ hai) khi học xong; với firewalld, luật không có `--permanent` tự mất khi reload.

Handler chỉ dùng được thư viện chuẩn và gói có sẵn trong image (boto3, botocore, s3transfer, jmespath, python-dateutil,
urllib3, six, simplejson); `requirements.txt` có gói khác thì test báo lỗi. RAM đo 2026-11-11: khoảng 40 MB mỗi container
(giới hạn mặc định 256 MB), khởi động dưới 1 giây.

## Dịch vụ phụ trợ: Vault dev

Module 12 và capstone dùng một Vault chạy dev mode: service `vault-devops` (image `hashicorp/vault:2.2.1` ghim digest), profile `devops`, không thuộc `all`. Dev mode giữ mọi dữ liệu trong RAM, đã unseal sẵn, mất hết khi container dừng; không bao giờ dùng cấu hình này cho môi trường thật.

```bash
docker compose -f setup/docker-compose.yml --profile devops up -d --wait vault-devops
docker compose -f setup/docker-compose.yml --profile devops rm -s -f -v vault-devops
```

Vault ở `http://127.0.0.1:18200`, chỉ mở trên `127.0.0.1`; đổi cổng bằng `DEVOPS_VAULT_PORT` trong `setup/.env`. Token root của dev mode là chuỗi cố định cho lab `devops-lab-root` (không phải bí mật, đổi bằng `DEVOPS_VAULT_TOKEN`). Image khai báo `VOLUME /vault/file` và `/vault/logs`, nên lệnh tắt có `-v` để xoá luôn hai volume ẩn danh đi kèm. Test không đọc `VAULT_ADDR`, `VAULT_TOKEN` hay `~/.vault-token` của máy: `vault_env` dựng env từ đầu, với `HOME` tạm riêng nên `vault login` không ghi `.vault-token` vào project của bạn.

## Stack observability

Module 13, 16 và capstone m08, m09 dựng stack observability bằng `testkit.ObsStack` trong một `DockerLab`: OTel Collector,
Jaeger, Loki, Prometheus, Alertmanager và Grafana cùng project compose với app của bài, cổng trống trên `127.0.0.1`, xoá sạch khi
test xong. Cấu hình mặc định ở `setup/observability/`. Test không tự kéo image: thiếu image thì skip kèm lệnh. Admin hay người học
kéo một lần (khoảng 3,4 GB trên đĩa, Grafana chiếm 1,95 GB; Prometheus và Alertmanager có sẵn nếu đã học track MLOps):

```bash
nice -n 15 docker pull otel/opentelemetry-collector-contrib:0.163.2@sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849 &&
nice -n 15 docker pull jaegertracing/jaeger:2.22.0@sha256:836b967b5abcf1f7758066aa6b348619267a2f1459f72d472840570f9bd88a17 &&
nice -n 15 docker pull grafana/loki:3.7.9@sha256:0db216b630ae1f348a1584c67f3cead8b4c1fc839169a39501db664744158e28 &&
nice -n 15 docker pull prom/prometheus:v3.5.0@sha256:63805ebb8d2b3920190daf1cb14a60871b16fd38bed42b857a3182bc621f4996 &&
nice -n 15 docker pull prom/alertmanager:v0.34.1@sha256:e9733bafb1bdef9b00e25a21f8f99dc26a22224bf16641ad754d1649f4c3357a &&
nice -n 15 docker pull grafana/grafana:13.2.5@sha256:9f7aa1e1e3246aade5792d35a738049f7f32f89cd51d1956cf426a4e86268a84
```

Kéo bằng `tag@digest` thì `docker images` hiện tag là `<none>`; testkit tìm image theo đúng chuỗi `tag@digest` nên vẫn thấy.
Image Prometheus, Alertmanager đã kéo theo tag (track MLOps) cũng được nhận vì digest trùng.

| Thành phần | Bản | Ngày phát hành | Ghi chú |
|---|---|---|---|
| OTel Collector contrib | 0.163.2 | 2026-10-21 | Bản contrib vì cần `spanmetrics`, exporter `prometheus`, processor `attributes` |
| Jaeger | 2.22.0 | 2026-10-06 | Bản 2.x chỉ còn API query v3 (`/api/v3/traces`); lưu trace trong RAM |
| Loki | 3.7.9 | 2026-10-20 | Nhận log OTLP ở `/otlp`, `trace_id` thành structured metadata |
| Prometheus | v3.5.0 | LTS, cùng bản track MLOps | Kèm `promtool` |
| Alertmanager | v0.34.1 | 2026-09-17, cùng bản track MLOps | Kèm `amtool` |
| Grafana | 13.2.5 | 2026-10-27 | Đọc ẩn danh (Viewer), tắt tải plugin và báo cáo thống kê |

RAM đo 2026-11-11 (cpuset 12-35, `docker stats`): riêng stack khoảng 410 MB (Grafana khoảng 255 MB, Loki 46 MB, Collector 45 MB,
Prometheus 35 MB, Jaeger 15 MB, Alertmanager 15 MB), khởi động khoảng 13 giây; cùng Olist Shop (api, worker, postgres, redis)
khoảng 620 MB, khoảng 16 giây khi image app đã build. Mỗi container giới hạn 512 MB. Không service nào tạo volume: dữ liệu nằm
trong tmpfs và mất khi tắt.

Muốn tự chạy stack ngoài test (ví dụ xem dashboard khi làm module 13): `docker compose -f setup/observability/compose.yaml up -d`,
Grafana ở `http://127.0.0.1:13300`, Jaeger `16686`, Prometheus `19090`, Alertmanager `19093`, Loki `13100`, OTLP gRPC `14317`, HTTP
`14318` (đổi bằng biến `DEVOPS_*_PORT` trong tệp compose), tắt bằng `docker compose -f setup/observability/compose.yaml down -v`.
Olist Shop gửi trace và log tới đó khi đặt `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:14317`. Gõ `promtool`, `amtool` bằng tay:

```bash
docker run --rm --network none -u "$(id -u):$(id -g)" -v "$PWD:/work:ro" -w /work --entrypoint /bin/promtool \
  prom/prometheus:v3.5.0@sha256:63805ebb8d2b3920190daf1cb14a60871b16fd38bed42b857a3182bc621f4996 test rules tests.yml
docker run --rm --network none -u "$(id -u):$(id -g)" -v "$PWD:/work:ro" -w /work --entrypoint /bin/amtool \
  prom/alertmanager:v0.34.1@sha256:e9733bafb1bdef9b00e25a21f8f99dc26a22224bf16641ad754d1649f4c3357a check-config alertmanager.yml
```

## Cluster kind devops-lab

Module 10, 11 và capstone m06 chạy trên một cluster kind tên `devops-lab`, cấu hình ở `setup/kind/devops-lab.yaml`: một control plane và hai worker, node image `kindest/node:v1.34.0` ghim theo digest (mặc định của kind 0.30.0), API server và cổng 80/443 của ingress (`18180`, `18543`) chỉ mở trên `127.0.0.1`, control plane có nhãn `ingress-ready=true`. CNI là kindnet mặc định của kind, bản này thực thi NetworkPolicy (đã kiểm: policy deny-all chặn kết nối giữa hai pod), nên không cần Calico.

Cài kind, kubectl, helm vào `~/.local/bin` (kiểm checksum trước khi cài; module 10 dạy lại kind và kubectl, module 11 dạy helm):

```bash
mkdir -p ~/.cache/devops-track/dl && cd ~/.cache/devops-track/dl \
  && curl -fsSLO https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-amd64 \
  && curl -fsSLO https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-amd64.sha256sum \
  && sha256sum --check kind-linux-amd64.sha256sum \
  && install -m 0755 kind-linux-amd64 ~/.local/bin/kind \
  && curl -fsSLO https://dl.k8s.io/release/v1.34.13/bin/linux/amd64/kubectl \
  && curl -fsSLO https://dl.k8s.io/release/v1.34.13/bin/linux/amd64/kubectl.sha256 \
  && echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check \
  && install -m 0755 kubectl ~/.local/bin/kubectl \
  && curl -fsSLO https://get.helm.sh/helm-v3.22.1-linux-amd64.tar.gz \
  && curl -fsSLO https://get.helm.sh/helm-v3.22.1-linux-amd64.tar.gz.sha256sum \
  && sha256sum --check helm-v3.22.1-linux-amd64.tar.gz.sha256sum \
  && tar -xzf helm-v3.22.1-linux-amd64.tar.gz linux-amd64/helm \
  && install -m 0755 linux-amd64/helm ~/.local/bin/helm
kind version && kubectl version --client && helm version --short
```

Tạo cluster, luôn kèm `--kubeconfig ~/.kube/devops-lab.yaml` để kind không ghi vào `~/.kube/config` và không đổi current-context của bạn (tệp này là kubeconfig admin: để trong `~/.kube`, thư mục mà sandbox của test luôn che, nên script của bài không đọc được; đừng chép nó vào thư mục bài hay thư mục khác), rồi ghim CPU cho từng node khi `DEVOPS_CPUSET` có giá trị (không ghim thì bỏ `taskset -c "$DEVOPS_CPUSET"`):

```bash
mkdir -p ~/.kube
nice -n 15 taskset -c "$DEVOPS_CPUSET" kind create cluster --config setup/kind/devops-lab.yaml --kubeconfig ~/.kube/devops-lab.yaml
if [ -n "$DEVOPS_CPUSET" ]; then for node in $(kind get nodes --name devops-lab); do docker update --cpuset-cpus "$DEVOPS_CPUSET" "$node"; done; fi
KUBECONFIG=~/.kube/devops-lab.yaml kubectl get nodes
```

Tắt khi không dùng (giải phóng RAM, giữ nguyên trạng thái), bật lại (sau khi khởi động lại máy node cũng ở trạng thái dừng), xoá hẳn:

```bash
docker stop $(kind get nodes --name devops-lab)
docker start $(kind get nodes --name devops-lab)
kind delete cluster --name devops-lab --kubeconfig ~/.kube/devops-lab.yaml
```

### Image cho bài tập trên cluster

Pod của bài tập không bao giờ kéo image từ Internet lúc chấm: image phải có sẵn trong containerd của hai worker (control plane có
taint, pod của bài không chạy ở đó). `ex.require_kind_images(...)` skip kèm đúng lệnh nạp khi thiếu. Các image dùng chung của module
10, 11 và capstone m06:

| Image | Nguồn | Dùng cho |
| --- | --- | --- |
| `devops-track/olist-shop:1.0` | Build từ `setup/kind/olist-shop.Dockerfile` trên `python:3.12.16-slim-trixie`, user `10001`, context `tracks/devops/sample-app` | API và worker Olist Shop |
| `postgres:16.15-alpine` | Docker Hub | Postgres |
| `redis:7.4.12-alpine` | Docker Hub | Redis |
| `nginx:1.30.6-alpine` | Docker Hub (đã có từ module 05) | Sidecar reverse proxy |

Build image Olist Shop (lần đầu cần mạng cho `pip install`), kéo ba image còn lại, rồi nạp vào hai worker. Chạy từ thư mục gốc của
repo; không ghim thì bỏ `${DEVOPS_CPUSET:+...}`:

```bash
nice -n 15 docker build --pull=false -f setup/kind/olist-shop.Dockerfile -t devops-track/olist-shop:1.0 tracks/devops/sample-app ${DEVOPS_CPUSET:+--cpuset-cpus "$DEVOPS_CPUSET"} &&
docker pull postgres:16.15-alpine && docker pull redis:7.4.12-alpine && docker pull nginx:1.30.6-alpine &&
nice -n 15 kind load docker-image devops-track/olist-shop:1.0 postgres:16.15-alpine redis:7.4.12-alpine nginx:1.30.6-alpine --name devops-lab --nodes devops-lab-worker,devops-lab-worker2
```

Docker bật **containerd image store** (Docker Desktop mới, Docker Engine 29 cài mới; `docker info` có dòng
`driver-type: io.containerd.snapshotter.v1`) thì `kind load docker-image` lỗi `ctr: content digest sha256:...: not found`, vì kind
nhập tarball với `--all-platforms` mà store chỉ giữ layer của một nền tảng. Nạp qua tarball một nền tảng thay thế (cần Docker 28 trở
lên cho `docker save --platform`):

```bash
mkdir -p ~/.cache/devops-track/kind-images &&
for image in devops-track/olist-shop:1.0 postgres:16.15-alpine redis:7.4.12-alpine nginx:1.30.6-alpine; do
  archive=~/.cache/devops-track/kind-images/"$(echo "$image" | tr '/:' '__')".tar &&
  docker save --platform linux/amd64 -o "$archive" "$image" &&
  nice -n 15 kind load image-archive "$archive" --name devops-lab --nodes devops-lab-worker,devops-lab-worker2 &&
  rm -f "$archive" || break
done
docker exec devops-lab-worker crictl images | grep -E 'olist-shop|postgres|redis|nginx'
```

Máy ARM (Apple Silicon, Graviton) đổi `linux/amd64` thành `linux/arm64`. Lệnh cuối liệt kê image trong một worker; thiếu dòng nào thì
xem lỗi của vòng lặp. Xoá cluster là xoá luôn image đã nạp; tạo lại cluster thì nạp lại.

### Gateway dùng chung: Gateway API và Traefik

Bài Ingress và Gateway API (module 10 Intermediate 04, các bài sau) dùng một controller dùng chung do **admin cài một lần** sau khi
tạo cluster; test không bao giờ cài, thiếu thì `ex.require_gateway()` skip kèm lệnh dưới. Tệp ghim trong `setup/kind/gateway/`:

| Thành phần | Bản | Ghim |
| --- | --- | --- |
| CRD Gateway API, kênh standard | v1.6.3 (`standard-install.yaml` của release, chép nguyên) | `SHA256SUMS` trong thư mục |
| Traefik (Ingress provider cộng Kubernetes Gateway provider) | v3.7.17, hỗ trợ Gateway API standard v1.6.3 theo tài liệu của bản này | Image kéo theo digest `sha256:30ff62491aacdb862ceb8c9edcf2627da638d7deafdd4b6dab32fe34f8aa3e90` rồi gắn tag `traefik:v3.7.17` |
| Object dùng chung (`10-traefik.yaml`) | Namespace `devops-gateway` (Pod Security `restricted`), Deployment, Service `traefik` (ClusterIP cổng 80), IngressClass `devops-traefik`, GatewayClass `devops-traefik`, Gateway `devops-gateway/public` (listener HTTP 8000, chỉ nhận HTTPRoute từ namespace có nhãn `devops-ex`) | `SHA256SUMS` |

Manifest dùng tag vì `kind load` không giữ repo digest trong containerd của node (pod ghi digest sẽ khiến kubelet kéo lại từ Docker
Hub); digest được ghim ở bước `docker pull`, và Deployment đặt `imagePullPolicy: Never`: chưa nạp image thì pod báo
`ErrImageNeverPull` thay vì tự kéo một tag không ghim. `00-gateway-api-v1.6.3-standard-install.yaml` là bản chép nguyên của release;
`10-traefik.yaml` do track viết. Chạy từ thư mục gốc của repo, sau khi đã tạo cluster:

```bash
docker pull traefik@sha256:30ff62491aacdb862ceb8c9edcf2627da638d7deafdd4b6dab32fe34f8aa3e90 &&
docker tag traefik@sha256:30ff62491aacdb862ceb8c9edcf2627da638d7deafdd4b6dab32fe34f8aa3e90 traefik:v3.7.17 &&
(cd setup/kind/gateway && sha256sum --check SHA256SUMS) &&
mkdir -p ~/.cache/devops-track/kind-images &&
docker save --platform linux/amd64 -o ~/.cache/devops-track/kind-images/traefik.tar traefik:v3.7.17 &&
nice -n 15 kind load image-archive ~/.cache/devops-track/kind-images/traefik.tar --name devops-lab --nodes devops-lab-worker,devops-lab-worker2 &&
rm -f ~/.cache/devops-track/kind-images/traefik.tar &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side -f setup/kind/gateway/00-gateway-api-v1.6.3-standard-install.yaml &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml wait --for condition=Established crd --all --timeout=60s &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml apply -f setup/kind/gateway/10-traefik.yaml &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n devops-gateway rollout status deployment/traefik --timeout=120s &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n devops-gateway get gateway public
```

```text
NAME     CLASS            ADDRESS   PROGRAMMED   AGE
public   devops-traefik             True         6s
```

`--server-side` cần cho CRD vì annotation `last-applied-configuration` của chúng vượt giới hạn 256 KiB. Ranh giới cho bài: token của lab
chỉ ghi được `httproutes` và `ingresses` trong namespace của lab (không Gateway, GatewayClass, ReferenceGrant), và một
ValidatingAdmissionPolicy của lab buộc Ingress dùng `ingressClassName: devops-traefik`, không `defaultBackend`, và HTTPRoute chỉ gắn vào
`devops-gateway/public`; mọi host phải là `<namespace của lab>.olist.test` hay tên con, nên một lab không chiếm được host của lab khác.
Traffic vào Traefik chỉ qua Service ClusterIP trong cluster; test gọi từ một pod, không dùng cổng của máy. Gỡ:
`kubectl --kubeconfig ~/.kube/devops-lab.yaml delete -f setup/kind/gateway/10-traefik.yaml` rồi `delete -f` tệp CRD (xoá CRD là xoá
mọi HTTPRoute).

Test không bao giờ tạo hay xoá cluster. `require_cluster` skip khi kind cũ hơn 0.30 hay kubectl cũ hơn 1.33, và skip với thông báo riêng khi Docker tắt, khi chưa có cluster, khi node đang dừng (kèm lệnh `docker start`) và khi API server chưa trả `ok` cho `/readyz` trong 5 giây. Mỗi lần chạy, test lấy kubeconfig bằng `kind get kubeconfig --name devops-lab` vào thư mục tạm, không đọc `KUBECONFIG` hay `~/.kube` của bạn, nên cluster thật mà `~/.kube/config` đang trỏ tới không bao giờ bị đụng. Mỗi test làm việc trong namespace riêng `devops-ex-<id>` (nhãn `devops-ex=<id>`, Pod Security `baseline`) bằng token của một ServiceAccount chỉ có quyền trong namespace đó (không impersonate, không xin token cho ServiceAccount khác), và xoá namespace khi xong. Trong lúc có test chạy, cluster từ chối PersistentVolume hostPath của mọi user không phải thành phần hệ thống, kể cả admin; PV `local` chỉ testkit tạo, trong thư mục `/srv/devops-lab-pv` của worker. Test bị ngắt giữa chừng có thể để lại namespace; xem và xoá bằng:

```bash
KUBECONFIG=~/.kube/devops-lab.yaml kubectl get namespaces,clusterroles,clusterrolebindings,validatingadmissionpolicies,validatingadmissionpolicybindings -l devops-ex
KUBECONFIG=~/.kube/devops-lab.yaml kubectl delete namespaces,clusterroles,clusterrolebindings,validatingadmissionpolicies,validatingadmissionpolicybindings -l devops-ex
KUBECONFIG=~/.kube/devops-lab.yaml kubectl -n argocd delete appprojects.argoproj.io -l devops-ex
```

Lệnh xoá trên chỉ chọn object có nhãn `devops-ex`, không đụng gì khác; chỉ chạy khi không có test nào đang chạy. Node kind là container Docker chạy privileged, nên pod privileged, hostPath, hostNetwork trên cluster này chạm được tới máy của bạn: namespace của test chặn chúng bằng Pod Security, và bài thực hành tay cũng nên làm trong namespace có nhãn `pod-security.kubernetes.io/enforce=baseline`.

### metrics-server dùng chung

HPA và `kubectl top` (module 11, capstone m06) đọc CPU, bộ nhớ của pod qua API `metrics.k8s.io` do metrics-server phục vụ. **Admin cài
một lần** sau khi tạo cluster; test không bao giờ cài, thiếu thì `ex.require_metrics()` skip kèm lệnh dưới. Tệp ghim trong
`setup/kind/metrics-server/`:

| Thành phần | Bản | Ghim |
| --- | --- | --- |
| `00-metrics-server-v0.9.1-components.yaml` | `components.yaml` của release v0.9.1 (hỗ trợ Kubernetes 1.34 trở lên), chép nguyên | `SHA256SUMS` (`3c7f57cd...`) |
| `kustomization.yaml` (track viết) | Patch Deployment: thêm `--kubelet-insecure-tls`, `imagePullPolicy: Never` | `SHA256SUMS` |
| Image `registry.k8s.io/metrics-server/metrics-server:v0.9.1` | Kéo theo digest `sha256:9b0ba1926e1d3089673f45461c3c1416109dea33b3ba3434048defd380df329b` rồi gắn tag | Nạp vào hai worker bằng `kind load image-archive` |

Vì sao `--kubelet-insecure-tls`: metrics-server lấy số liệu từ endpoint `/metrics/resource` của kubelet trên từng node qua HTTPS. Kubelet
của kind dùng chứng chỉ serving tự ký, không có IP của node trong SAN và không do CA của cluster ký, nên metrics-server từ chối với
`x509: cannot validate certificate for 172.21.0.3 because it doesn't contain any IP SANs` và không bao giờ Ready (đã thử trên máy viết
bài). Cờ này bỏ kiểm chứng chỉ của kubelet, chỉ chấp nhận được trên cluster lab; cluster thật bật `serverTLSBootstrap` cho kubelet và
duyệt CSR để kubelet có chứng chỉ do CA ký. `imagePullPolicy: Never` giữ kiểu fail closed như Traefik: chưa nạp image thì pod báo
`ErrImageNeverPull` thay vì tự kéo tag không ghim. Chạy từ thư mục gốc của repo:

```bash
docker pull registry.k8s.io/metrics-server/metrics-server@sha256:9b0ba1926e1d3089673f45461c3c1416109dea33b3ba3434048defd380df329b &&
docker tag registry.k8s.io/metrics-server/metrics-server@sha256:9b0ba1926e1d3089673f45461c3c1416109dea33b3ba3434048defd380df329b registry.k8s.io/metrics-server/metrics-server:v0.9.1 &&
(cd setup/kind/metrics-server && sha256sum --check SHA256SUMS) &&
mkdir -p ~/.cache/devops-track/kind-images &&
docker save --platform linux/amd64 -o ~/.cache/devops-track/kind-images/metrics-server.tar registry.k8s.io/metrics-server/metrics-server:v0.9.1 &&
nice -n 15 kind load image-archive ~/.cache/devops-track/kind-images/metrics-server.tar --name devops-lab --nodes devops-lab-worker,devops-lab-worker2 &&
rm -f ~/.cache/devops-track/kind-images/metrics-server.tar &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml apply -k setup/kind/metrics-server &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n kube-system rollout status deployment/metrics-server --timeout=120s &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml wait --for condition=Available apiservice/v1beta1.metrics.k8s.io --timeout=120s
```

Lần lấy số liệu đầu tiên mất khoảng 30 giây sau khi rollout xong (`--metric-resolution=15s`); `kubectl --kubeconfig
~/.kube/devops-lab.yaml top nodes` có số là xong. Gỡ: `kubectl --kubeconfig ~/.kube/devops-lab.yaml delete -k setup/kind/metrics-server`.

### ArgoCD và git server dùng chung

Bài GitOps (module 12, capstone m07) dùng một ArgoCD và một git server trong cluster do **admin cài một lần** sau khi tạo cluster;
test không bao giờ cài, thiếu thì `ex.require_argocd()` skip kèm lệnh dưới. Tệp ghim trong `setup/kind/argocd/`:

| Thành phần | Bản | Ghim |
| --- | --- | --- |
| `00-argocd-v3.5.6-core-install.yaml` | `manifests/core-install.yaml` của tag v3.5.6 (`https://raw.githubusercontent.com/argoproj/argo-cd/v3.5.6/manifests/core-install.yaml`), chép nguyên. Bản 3.5 mới nhất phát hành từ hai tuần trước ngày cài (2026-10-20); 3.5.7 và 3.6.x ra sau 2026-10-27 nên chưa dùng | `SHA256SUMS` (`d3d9d3555ad77eb4...`) |
| Image `quay.io/argoproj/argocd:v3.5.6` | application-controller, repo-server, sidecar CMP và git server dùng chung image này | Kéo theo digest `sha256:8e5cc5bb008df8a09dba439462e58c94c55b7735888d3ebde0c25fc05e4e5335` rồi gắn tag |
| Image `public.ecr.aws/docker/library/redis:8.2.3-alpine` | Cache của ArgoCD, đúng tag trong manifest của release | Digest `sha256:08ad0b1d280850169a790dba1393ff7a90aef951fc19632cf4d3ce4f78e679ba` |
| Image `ghcr.io/getsops/sops:v3.13.3-alpine` | Init container chép binary `sops` (cùng bản `SOPS_VERSION`) cho sidecar CMP | Digest `sha256:ae501277bf742f1662e0f881f43dd8fd6798b489a8058e921dbf6cda597140ea` |
| `01-namespaces.yaml`, `10-sops-cmp.yaml`, `11-repo-tools.yaml`, `20-default-project.yaml`, `30-git-server.yaml`, `40-repo-server-egress.yaml`, `kustomization.yaml`, `namespace.yaml` (track viết) | Namespace `argocd`, `devops-git` (Pod Security `restricted`); plugin CMP; wrapper `kustomize` tắt git; AppProject `default` khoá trống; git server; NetworkPolicy egress của repo-server; patch cấu hình, tài nguyên, `imagePullPolicy: Never` | `SHA256SUMS` |

Lựa chọn và lý do:

- **Bản core** (`core-install.yaml`) thay vì `install.yaml`: chỉ có application-controller, repo-server, redis (applicationset-controller
  để 0 replica vì ApplicationSet chỉ học ở mức khái niệm). Không có API server, UI, Dex, notifications: nhẹ hơn, không có mật khẩu
  admin hay cổng nào để lộ. Test và người học đọc trạng thái Application bằng `kubectl` với token của lab.
- **Application trong namespace của lab** (`application.namespaces: devops-ex-*` trong `argocd-cmd-params-cm`): người học tạo
  `Application` ngay trong `devops-ex-<id>`, không cần quyền gì trong namespace `argocd`.
- **Sync bằng impersonation** (`application.sync.impersonation.enabled: "true"` trong `argocd-cm`): controller của ArgoCD có quyền
  admin cả cluster. AppProject của mỗi lab đặt `destinationServiceAccounts` là `devops-ex-learner` của lab, nên mọi object trong repo
  được apply bằng chính token của lab: RBAC, ValidatingAdmissionPolicy và Pod Security của lab vẫn áp dụng. Đã kiểm: repo có
  ServiceAccount mà Role không cho thì sync lỗi `forbidden: User "system:serviceaccount:<ns>:devops-ex-learner" cannot get resource
  "serviceaccounts"`.
- **SOPS bằng sidecar CMP `sops-kustomize`** thay vì ksops: ksops là plugin exec của kustomize, cần bật `--enable-alpha-plugins
  --enable-exec` cho repo-server, nghĩa là repo của bất kỳ lab nào cũng chạy được chương trình tuỳ ý trong repo-server (nơi có khoá
  age). Sidecar CMP chỉ chạy `sops --decrypt --in-place` cho mọi `*.enc.yaml` rồi `kustomize build --load-restrictor
  LoadRestrictionsRootOnly .` (không exec plugin, không Helm), trong một container riêng; khoá riêng chỉ mount vào container đó (chỉ
  đọc), container `argocd-repo-server` chính không thấy. Application chọn plugin bằng `spec.source.plugin.name: sops-kustomize`
  (plugin không có `discover`, không tự áp cho repo khác). kustomize lỗi sau khi giải mã thì output bị ẩn để không in giá trị Secret.
  Đã thử: `secretGenerator` đọc `/sops-age/keys.txt` bị kustomize từ chối, symlink trỏ ra ngoài repo bị repo-server từ chối
  (`repository contains out-of-bounds symlinks`).
- **Git server là `git daemon` chỉ đọc** (giao thức `git://`, cổng 9418) chạy bằng chính image ArgoCD (có sẵn `git-daemon`), thay vì
  `git http-backend` sau nginx: không thêm image nào, không cần web server hay CGI, không ai push được qua mạng. Testkit ghi repo
  bằng quyền admin (`kubectl cp` một git bundle vào pod rồi `git fetch` vào repo bare `/srv/git/<namespace>.git`). NetworkPolicy chỉ
  cho repo-server của ArgoCD kết nối, nên pod của lab không đọc được repo của lab khác. Repo nằm trong `emptyDir`: pod git khởi
  động lại (drain worker, máy khởi động lại) là mất repo của lab đang chạy; lab sau đẩy lại từ đầu.
- **AppProject `default` khoá trống**: không Application nào dùng được; mỗi lab dùng AppProject `devops-ex-<id>` do testkit tạo.
- **Repo-server không ra được ngoài cluster**: NetworkPolicy `argocd-repo-server-egress` (cả pod, gồm sidecar giữ khoá age) chỉ cho
  DNS của `kube-system` (53 UDP/TCP), git server (`devops-git`, 9418) và `argocd-redis` (6379). Cộng thêm, để lỗi trả về ngay thay vì
  chờ hết thời gian: `HTTP(S)_PROXY=http://127.0.0.1:1` (proxy chết) cho repo-server và sidecar, nên `resources: - https://...`
  trong kustomize hay dependency Helm/`oci://` lỗi trong khoảng 1 giây; sidecar tắt mọi giao thức git (`protocol.allow=never`,
  `GIT_ALLOW_PROTOCOL=none`); container repo-server chính chỉ cho git `git://` (để lấy repo của lab) và gọi `kustomize` qua wrapper
  `/devops-tools/kustomize` tắt git (kustomize 5.8 vốn không coi `git://` là remote base; wrapper là lớp dự phòng); submodule tắt
  (`reposerver.enable.git.submodule: "false"`); mỗi lần render tối đa 30 giây (`ARGOCD_EXEC_TIMEOUT`), 4 lần render song song.
- **Sidecar CMP từ chối sớm tệp không dùng age**: tệp `*.enc.yaml` có khoá `kms`, `gcp_kms`, `azure_kv`, `hc_vault`, `pgp` hay
  `key_groups` viết theo cách thường gặp bị từ chối trước khi giải mã, kèm thông báo dễ hiểu. Đây chỉ là kiểm theo tên (denylist,
  `grep`), lọt được bằng khoá trong nháy đơn, khoá tường minh `? hc_vault` hay escape `"hc_\x76ault"`; ranh giới thật để sops không
  gọi ra ngoài là NetworkPolicy egress cộng proxy chết ở trên. Sidecar giới hạn 1 GiB ephemeral storage, `/tmp` của nó tối đa
  512 MiB.

Chạy từ thư mục gốc của repo, sau khi đã tạo cluster:

```bash
ok=1
for ref in quay.io/argoproj/argocd:v3.5.6@sha256:8e5cc5bb008df8a09dba439462e58c94c55b7735888d3ebde0c25fc05e4e5335 \
           public.ecr.aws/docker/library/redis:8.2.3-alpine@sha256:08ad0b1d280850169a790dba1393ff7a90aef951fc19632cf4d3ce4f78e679ba \
           ghcr.io/getsops/sops:v3.13.3-alpine@sha256:ae501277bf742f1662e0f881f43dd8fd6798b489a8058e921dbf6cda597140ea; do
  image="${ref%@*}" && archive=~/.cache/devops-track/kind-images/"$(echo "$image" | tr '/:' '__')".tar &&
  docker pull "${image%:*}@${ref##*@}" && docker tag "${image%:*}@${ref##*@}" "$image" &&
  mkdir -p ~/.cache/devops-track/kind-images && docker save --platform linux/amd64 -o "$archive" "$image" &&
  nice -n 15 kind load image-archive "$archive" --name devops-lab --nodes devops-lab-worker,devops-lab-worker2 &&
  rm -f "$archive" || { ok=0; break; }
done
[ "$ok" = 1 ] &&
(cd setup/kind/argocd && sha256sum --check SHA256SUMS) &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side -k setup/kind/argocd &&
{ kubectl --kubeconfig ~/.kube/devops-lab.yaml wait --for condition=Established crd/appprojects.argoproj.io --timeout=60s ||
  { sleep 3 && kubectl --kubeconfig ~/.kube/devops-lab.yaml wait --for condition=Established crd/appprojects.argoproj.io --timeout=60s; }; } &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side --force-conflicts -f setup/kind/argocd/20-default-project.yaml
```

Khoá age dùng chung cho mọi lab (admin tạo một lần). Khoá riêng chỉ đi vào Secret `argocd/devops-sops-age` rồi bị xoá khỏi máy;
public key vào ConfigMap `argocd/devops-sops-age-public` để bài mã hoá (`lab.sops_age_recipient`). Testkit không bao giờ đọc Secret
đó, và không có gì của nó vào sandbox của bài:

```bash
keydir=$(mktemp -d) && age-keygen -o "$keydir/keys.txt" &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n argocd create secret generic devops-sops-age --from-file=keys.txt="$keydir/keys.txt" &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n argocd create configmap devops-sops-age-public --from-literal=recipient="$(age-keygen -y "$keydir/keys.txt")" &&
rm -rf "$keydir" &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n argocd rollout status deployment/argocd-repo-server --timeout=180s &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n argocd rollout status statefulset/argocd-application-controller --timeout=180s &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n devops-git rollout status deployment/git --timeout=120s
```

Repo-server chờ Secret này (pod kẹt `ContainerCreating` khi chưa có). Xoay khoá: tạo khoá mới, thay Secret và ConfigMap, `kubectl -n
argocd rollout restart deployment/argocd-repo-server`; tệp mã hoá bằng khoá cũ phải mã hoá lại (`sops updatekeys`).

**Đã kiểm 2026-11-10** (kind 0.30.0, node v1.34.0, CPU ghim `12-35`, image nạp sẵn): từ `apply` tới khi mọi pod sẵn sàng khoảng 21
giây. RAM (working set theo `crictl stats`): lúc nghỉ khoảng 145 MiB (application-controller 92, repo-server 27, sidecar CMP 19,
redis 5, git server 1), sau hai bài GitOps chạy song song khoảng 190 MiB (controller 136). Sync đầu tiên của một Application tự động
khoảng 2 giây; sau commit mới (`gitops_repo` yêu cầu hard refresh) khoảng 2 giây; Secret SOPS được giải mã khi sync và giá trị
không xuất hiện trong `status` của Application, log của repo-server hay của controller.

Giới hạn cần biết:

- Manifest ArgoCD render (kể cả Secret đã giải mã, dạng base64) được cache trong redis của namespace `argocd`; NetworkPolicy của
  release chỉ cho controller và repo-server kết nối redis.
- Một lần sync tự động đang lỗi được ArgoCD thử lại với backoff trên đúng commit cũ; commit mới chỉ được sync khi thao tác đó kết
  thúc (hết lượt thử hay bị admin huỷ bằng `kubectl --kubeconfig ~/.kube/devops-lab.yaml -n <namespace> patch application <tên>
  --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'`; token của lab không sửa được `status`).
- Mọi lab dùng chung một khoá age: ranh giới giữa các lab là AppProject (repo riêng) chứ không phải khoá.
- Ai ghi được Application: chỉ ServiceAccount trong namespace của lab (Role của lab, cả khi ArgoCD sync app-of-apps bằng
  impersonation) và admin. Policy `devops-ex-<id>-argocd` kiểm mọi ServiceAccount của namespace đó; admin và controller của ArgoCD
  không bị kiểm. ArgoCD 3.5.6 **không** đối chiếu `operation.sync.source` với `sourceRepos` của project (đã thử bằng admin: lab A
  render được repo của lab B), nên policy của lab từ chối `operation.sync.source`, `sources`, `manifests` và mọi lần tạo, sửa
  `status`; đừng tạo Application hộ người học bằng quyền admin. Vì Application không có subresource `status`, token của lab
  dùng được `kubectl apply`, `patch`, `annotate`, nhưng `kubectl replace` hay `apply --force` (gửi lại cả object, thiếu `status`
  hiện có) bị từ chối.
- Mỗi lần `gitops_repo` tối đa 2000 tệp và 20 MiB (đếm theo byte đọc được lúc chép), cả lịch sử repo của một lab (bundle) tối đa
  40 MiB. Lab bị giết trước `close()` để lại repo và AppProject: lab mở sau đó tự
  xoá repo, bundle và AppProject `devops-ex-<id>` không còn namespace tương ứng.

Gỡ: `kubectl --kubeconfig ~/.kube/devops-lab.yaml delete -k setup/kind/argocd` (xoá CRD là xoá mọi Application và AppProject; Secret
và ConfigMap khoá age nằm trong namespace `argocd` nên bị xoá cùng).

### Linkerd dùng chung

Bài service mesh (module 15, capstone) dùng một Linkerd do **admin cài một lần** sau khi tạo cluster và cài CRD Gateway API (bước đầu
của [Gateway dùng chung](#gateway-dùng-chung-gateway-api-và-traefik)); test không bao giờ cài, thiếu thì `ex.require_linkerd()` và
`KubeLab(mesh=True)` skip kèm lệnh dưới. Tệp ghim trong `setup/kind/linkerd/`:

| Thành phần | Bản | Ghim |
| --- | --- | --- |
| `00-linkerd-crds-edge-26.10.1.yaml` | `helm template` của chart `linkerd-crds` 2026.10.1 (CRD `policy.linkerd.io`, `linkerd.io`, `workload.linkerd.io`; không kèm CRD Gateway API) | `SHA256SUMS` |
| `10-linkerd-cni-edge-26.10.1.yaml` | `helm template` của chart `linkerd2-cni` 2026.10.1 với `values-cni.yaml` (`imagePullPolicy: Never`, request nhỏ) | `SHA256SUMS` |
| `20-linkerd-control-plane-edge-26.10.1.yaml` | `helm template` của chart `linkerd-control-plane` 2026.10.1 với `values-control-plane.yaml` | `SHA256SUMS` |
| `01-namespaces.yaml`, `kustomization.yaml`, `certs.sh`, `values-*.yaml` (track viết) | Namespace `linkerd` (Pod Security `restricted`) và `linkerd-cni` (`privileged`, CNI ghi vào `/etc/cni/net.d` của node), cả hai tắt webhook của Linkerd; script sinh chứng chỉ | `SHA256SUMS` |
| Image `cr.l5d.io/linkerd/controller:edge-26.10.1` | destination, policy controller, identity, proxy-injector | Digest `sha256:880437e01bbd4bf3d8fa7b56996c4ed5dd6551843363dc851ddd0b298b923e8a` |
| Image `cr.l5d.io/linkerd/proxy:edge-26.10.1` | Proxy sidecar và init container `linkerd-network-validator` của mọi pod trong mesh | Digest `sha256:f2add36071cfca33754d2930800860785aaed672590bc0207be2f4da9889eb11` |
| Image `cr.l5d.io/linkerd/cni-plugin:v1.7.0` | DaemonSet `linkerd-cni` trên cả ba node (kể cả control plane) | Digest `sha256:f710874e5d70edfcf6e9e2a8ad18175b928a3f572eae322d7123b96f9b40c5a4` |

Lựa chọn và lý do:

- **Bản edge-26.10.1.** Linkerd mã nguồn mở chỉ phát hành bản edge; bản "stable" do nhà phân phối (Buoyant) build và cần đăng ký.
  edge-26.10.1 (2026-10-05) là bản edge mới nhất đã ra đủ hai tuần trước ngày cài (2026-11-11): edge-26.10.2 ra 2026-10-29, chỉ
  thiếu một ngày. Bản này chỉ nâng dependency và proxy v2.370.0, không có thay đổi phá vỡ so với 26.9.x.
- **Render bằng `helm template` thay cho `linkerd install`.** `linkerd install --ignore-cluster` không cho dùng issuer ngoài
  (`--identity-external-issuer`), còn để CLI tự sinh thì trust anchor, issuer và khoá webhook nằm thẳng trong manifest, tức là
  trong repo. Chart Helm của đúng release, render với `identity.externalCA: true`, issuer `kubernetes.io/tls` và
  `externalSecret: true` cho ba webhook, cho ra manifest không có Secret hay khoá nào. Render lại được: lệnh ở dưới, chart ghim
  SHA-256.
- **linkerd-cni thay init container `linkerd-init`.** `linkerd-init` cần NET_ADMIN, NET_RAW để đặt iptables trong pod, mà namespace
  của lab là Pod Security baseline: pod sẽ bị từ chối. Với CNI, pod chỉ có thêm `linkerd-network-validator` (không capability, uid
  65534) và proxy native sidecar (`readOnlyRootFilesystem`, drop ALL), chạy được dưới baseline lẫn restricted.
- **Không cài viz.** `KubeLab.mesh_status` đọc thẳng `/metrics` và `/env.json` trên cổng admin 4191 của proxy qua API server
  (`kubectl get --raw /api/v1/namespaces/<ns>/pods/<pod>:4191/proxy/metrics`), nên không cần Prometheus và dashboard của viz
  (thêm vài trăm MiB). Heartbeat (CronJob gửi về linkerd.io) tắt.
- **Chứng chỉ do admin sinh bằng openssl** (không cần thêm binary `step`): `certs.sh` tạo trust anchor (ECDSA P-256, 10 năm), ký
  issuer (CA trung gian `identity.linkerd.cluster.local`, 1 năm), **xoá khoá trust anchor ngay sau khi ký**, rồi đưa trust anchor vào
  ConfigMap `linkerd/linkerd-identity-trust-roots`, issuer vào Secret `linkerd/linkerd-identity-issuer`. Ba webhook dùng một CA
  riêng (khoá cũng bị xoá sau khi ký) và Secret `linkerd-*-k8s-tls`; script vá `caBundle` của ba webhook rồi khởi động lại control
  plane. Mọi tệp nằm trong `mktemp -d`, `umask 077`, xoá khi thoát; Secret tạo bằng server-side apply nên khoá không bị chép vào
  annotation `last-applied-configuration`. Khoá viết dạng PKCS#8: policy controller (Rust) không đọc khoá EC dạng SEC1 (`could not
  load private key`). Testkit không bao giờ đọc các Secret này.
- **Tài nguyên:** request 5-10m CPU, 16-32 MiB cho mỗi container control plane, giới hạn 128-256 MiB; proxy request 10m, 16 MiB,
  giới hạn 128 MiB (áp cho cả proxy trong pod của bài).

Chạy từ thư mục gốc của repo, sau khi đã tạo cluster và cài CRD Gateway API:

```bash
ok=1
for ref in cr.l5d.io/linkerd/controller:edge-26.10.1@sha256:880437e01bbd4bf3d8fa7b56996c4ed5dd6551843363dc851ddd0b298b923e8a \
           cr.l5d.io/linkerd/proxy:edge-26.10.1@sha256:f2add36071cfca33754d2930800860785aaed672590bc0207be2f4da9889eb11 \
           cr.l5d.io/linkerd/cni-plugin:v1.7.0@sha256:f710874e5d70edfcf6e9e2a8ad18175b928a3f572eae322d7123b96f9b40c5a4; do
  image="${ref%@*}" && archive=~/.cache/devops-track/kind-images/"$(echo "$image" | tr '/:' '__')".tar &&
  nodes=devops-lab-worker,devops-lab-worker2 && case "$image" in *cni-plugin*) nodes="devops-lab-control-plane,$nodes";; esac &&
  docker pull "${image%:*}@${ref##*@}" && docker tag "${image%:*}@${ref##*@}" "$image" &&
  mkdir -p ~/.cache/devops-track/kind-images && docker save --platform linux/amd64 -o "$archive" "$image" &&
  nice -n 15 kind load image-archive "$archive" --name devops-lab --nodes "$nodes" &&
  rm -f "$archive" || { ok=0; break; }
done
[ "$ok" = 1 ] &&
(cd setup/kind/linkerd && sha256sum --check SHA256SUMS) &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml apply --server-side -k setup/kind/linkerd &&
bash setup/kind/linkerd/certs.sh &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n linkerd-cni rollout status daemonset/linkerd-cni --timeout=120s &&
kubectl --kubeconfig ~/.kube/devops-lab.yaml -n linkerd rollout status deployment/linkerd-identity deployment/linkerd-destination deployment/linkerd-proxy-injector --timeout=180s
```

`certs.sh` đọc kubeconfig admin ở `~/.kube/devops-lab.yaml` (đổi bằng biến `DEVOPS_LAB_KUBECONFIG`). Chạy lại `certs.sh` là xoay
toàn bộ chứng chỉ: trust anchor mới, nên phải khởi động lại mọi pod đang trong mesh (`kubectl rollout restart`); không có khoá trust
anchor cũ để ký issuer mới chung gốc. `apply -k` lại thư mục này đặt `caBundle` của webhook về chuỗi giữ chỗ
`devops-linkerd-certs-sh`: chạy lại `certs.sh` sau đó (`require_linkerd` báo đúng lỗi này). CRD Gateway API cài sau Linkerd thì
policy controller không theo dõi HTTPRoute của Gateway API cho tới khi `kubectl -n linkerd rollout restart deployment/linkerd-destination`.

Render lại manifest (người bảo trì track, khi nâng bản; chart lấy từ `https://helm.linkerd.io/edge`, SHA-256 là `digest` trong
`index.yaml` của repo chart):

```bash
mkdir -p ~/.cache/devops-track/dl/linkerd-charts && cd ~/.cache/devops-track/dl/linkerd-charts &&
for chart in linkerd-crds-2026.10.1 linkerd2-cni-2026.10.1 linkerd-control-plane-2026.10.1; do
  curl -fsSLO "https://helm.linkerd.io/edge/$chart.tgz" || break
done &&
printf '%s\n' "455eb0dd8934e1e832a14cdd255de48c4f7861caeb175573ec8d17e5c4a1ce94  linkerd-crds-2026.10.1.tgz" \
  "05acb652a9651d3a0a02d14d302e89686e116414bf35bdf5bd56547787c2ca1b  linkerd2-cni-2026.10.1.tgz" \
  "e8db107da4932f09f67316ff305e9d097815396a56f6a401ca940a994a137567  linkerd-control-plane-2026.10.1.tgz" | sha256sum --check &&
cd - && cd setup/kind/linkerd &&
helm template linkerd-crds ~/.cache/devops-track/dl/linkerd-charts/linkerd-crds-2026.10.1.tgz --namespace linkerd > 00-linkerd-crds-edge-26.10.1.yaml &&
helm template linkerd2-cni ~/.cache/devops-track/dl/linkerd-charts/linkerd2-cni-2026.10.1.tgz --namespace linkerd-cni -f values-cni.yaml > 10-linkerd-cni-edge-26.10.1.yaml &&
helm template linkerd-control-plane ~/.cache/devops-track/dl/linkerd-charts/linkerd-control-plane-2026.10.1.tgz --namespace linkerd -f values-control-plane.yaml > 20-linkerd-control-plane-edge-26.10.1.yaml
```

CLI `linkerd` (tuỳ chọn, cho người học xem tay; release không kèm tệp checksum, SHA-256 dưới đây là digest GitHub ghi cho asset):

```bash
mkdir -p ~/.cache/devops-track/dl && cd ~/.cache/devops-track/dl &&
curl -fsSLO https://github.com/linkerd/linkerd2/releases/download/edge-26.10.1/linkerd2-cli-edge-26.10.1-linux-amd64 &&
echo "66d634f5318c8016f0b5face246a688964b6e2c86d6c3be34be68ab9fcd2a8cc  linkerd2-cli-edge-26.10.1-linux-amd64" | sha256sum --check &&
install -m 0755 linkerd2-cli-edge-26.10.1-linux-amd64 ~/.local/bin/linkerd
linkerd version --client
```

`linkerd --kubeconfig ~/.kube/devops-lab.yaml check` cho kết quả `√` (chỉ cảnh báo có bản edge mới hơn). Gỡ CLI: `rm -f
~/.local/bin/linkerd`.

**Đã kiểm 2026-11-11** (kind 0.30.0, node v1.34.0, CPU ghim `12-35`, image đã kéo về máy): cả khối lệnh cài ở trên, gồm nạp ba
image vào node, chạy xong trong khoảng 30 giây trên cluster mới. RAM (working set theo `crictl stats`) lúc nghỉ khoảng 85 MiB cho cả Linkerd:
destination 17, sp-validator 14, policy 5, identity 14, proxy-injector 18, ba proxy của control plane 3 mỗi cái, `linkerd-cni` 3
mỗi node. Mỗi pod trong mesh thêm một proxy khoảng 3-4 MiB. Hai Deployment nginx trong namespace mesh gọi nhau qua mTLS
(`client_id` và `server_id` là `<sa>.<ns>.serviceaccount.identity.linkerd.cluster.local`); sau khi có `Server`,
`MeshTLSAuthentication` và `AuthorizationPolicy` chỉ cho ServiceAccount `api`, pod thứ ba nhận 403 và
`inbound_http_authz_deny_total` tăng; pod ngoài mesh gọi thẳng cũng nhận 403.

Linkerd và ghim CPU: node kind đã ghim bằng `docker update --cpuset-cpus "$DEVOPS_CPUSET"`, nên mọi container của Linkerd (control
plane, CNI, proxy trong pod của bài) chỉ chạy trên các core đó. Proxy dùng một worker thread (`proxy.runtime.workers.minimum: 1`,
`LINKERD2_PROXY_CORES=1`), không tự giãn theo số core thấy được, nên ghim 24 core không làm proxy ăn nhiều CPU hơn. Các thành phần
Go (destination, identity, injector) đặt `GOMAXPROCS` theo số core được phép chạy, tức theo dải ghim.

Giới hạn cần biết:

- Webhook proxy-injector có `failurePolicy: Ignore` (mặc định của Linkerd): injector không chạy thì pod vẫn được tạo nhưng không có
  proxy. `mesh_status` báo `injected: False` cho trường hợp này.
- Cổng admin 4191 của mọi proxy mở cho mọi pod trong cluster: `/metrics` và `/env.json` (biến môi trường của container proxy, không
  có token) đọc được từ lab khác; `/proxy-log-level` và `/shutdown` chỉ nhận từ localhost (đã thử: 403). Điều này không lộ thêm gì
  so với quyền `view` mọi namespace mà lab vốn có.
- Lab ghi được `servers`, `authorizationpolicies`, `httproutes`, `meshtlsauthentications` trong namespace của lab; không
  `networkauthentications`, `httplocalratelimitpolicies`, `serverauthorizations`, `egressnetworks`, `serviceprofiles`. Policy
  `devops-ex-<id>-mesh` chặn mọi tham chiếu ra ngoài namespace của lab (HTTPRoute gắn vào `Server` của lab khác làm request không khớp
  route nào của lab đó nhận 404) và danh tính `*` trần trong `MeshTLSAuthentication`.
- Danh tính mTLS dựa trên token ServiceAccount của pod; token của lab không xin được token cho ServiceAccount khác, nên pod của
  lab chỉ mang danh tính của namespace mình.

Gỡ: `kubectl --kubeconfig ~/.kube/devops-lab.yaml delete -k setup/kind/linkerd` (xoá CRD là xoá mọi object `policy.linkerd.io`;
ConfigMap và Secret do `certs.sh` tạo nằm trong namespace `linkerd` nên bị xoá cùng), rồi `kubectl rollout restart` các workload
còn proxy.

### Bài thao tác node (cordon, drain, taint)

Bài cần cordon, drain hay taint worker (module 11) làm qua `KubeLab.node_action` của testkit, chỉ trên worker, `close()` hoàn tác.
Trạng thái node là của cả cluster, nên testkit giữ khoá `~/.cache/devops-track/kube-nodes.lock` suốt từ lần thao tác node đầu tiên
tới khi hoàn tác xong: hai bài như vậy không bao giờ chạy chồng nhau, kể cả ở hai terminal. Tệp test của các bài này mang marker
`kube_nodes`; muốn chạy song song phần còn lại thì loại chúng ra (`-m "not kube_nodes"`). Bài bị giết giữa chừng (SIGKILL, tắt terminal) không kịp hoàn tác: testkit ghi mọi thao tác node vào `~/.cache/devops-track/kube-nodes.state.json`, và bài cluster chạy sau đó (khi không có bài thao tác node nào đang chạy) tự so tệp với trạng thái thật của node, hoàn tác phần còn sót rồi chạy tiếp. Chỉ khi việc hoàn tác lỗi, test mới skip kèm đúng lệnh `kubectl uncordon`, `kubectl taint ... -` cần chạy. Testkit coi mọi cordon, taint ghi trong tệp mà còn trên node là của bài bị ngắt, nên đừng tự cordon đúng node đó bằng tay trước khi chạy lại test. Trong lúc bài drain một worker, pod của bài
khác, Traefik, metrics-server, ArgoCD, git server và control plane của Linkerd đang nằm trên worker đó cũng bị dời (repo trong git server mất theo pod); sau khi hoàn tác, testkit chờ chúng available lại rồi mới trả.

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
