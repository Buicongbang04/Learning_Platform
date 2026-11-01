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
| tofu (OpenTofu) | 08 IaC & provisioning (bản đã kiểm 1.13.2; test chạy `tofu` trong sandbox với LocalStack riêng `localstack-devops`, provider `hashicorp/aws` 6.12.0 tải một lần vào `~/.cache/devops-track/tofu-plugins` rồi dùng offline; trivy của module 06 quét chính sách ở Intermediate 04) | 1.10 (Basic 02 cần 1.11 cho biến `ephemeral`) | [Cài đặt](../tracks/devops/modules/08-iac-provisioning/README.md#0-cài-đặt) |
| ansible-core (`ansible`, `ansible-playbook`, `ansible-inventory`, `ansible-vault`...) | 09 Configuration management (bản đã kiểm 2.21.5, cài vào venv riêng `~/.cache/devops-track/ansible` bằng `uv pip install --require-hashes -r setup/ansible/requirements.txt`, symlink vào `~/.local/bin`; không thêm vào `pyproject.toml` gốc; test chạy Ansible trong sandbox tới target là container SSH build từ `setup/ansible-target/` trên `python:3.12.16-slim-trixie`) | 2.21 | [Cài đặt](../tracks/devops/modules/09-config-management/README.md#0-cài-đặt) |
| kind | 10 Kubernetes core (cluster dùng chung `devops-lab`, xem [Cluster kind devops-lab](#cluster-kind-devops-lab)) | 0.30.0 (node image ghim `kindest/node:v1.34.0` theo digest) | [Cài đặt](../tracks/devops/modules/10-kubernetes-core/README.md#0-cài-đặt) |
| kubectl | 10 Kubernetes core (bản đã kiểm 1.34.13, khớp minor của node image) | 1.33 (lệch tối đa một minor với API server 1.34) | [Cài đặt](../tracks/devops/modules/10-kubernetes-core/README.md#0-cài-đặt) |
| helm | 11 Kubernetes production (bản đã kiểm 3.22.1; Kustomize có sẵn trong kubectl) | 3.18 | [Cài đặt](../tracks/devops/modules/11-kubernetes-production/README.md#0-cài-đặt) |
| metrics-server (trong cluster, không cài lên máy) | 11 Kubernetes production (HPA, `kubectl top`; bản 0.9.1 ghim trong `setup/kind/metrics-server/`, xem [metrics-server dùng chung](#metrics-server-dùng-chung)) | Đúng bản đã ghim | [Cài đặt](../tracks/devops/modules/11-kubernetes-production/README.md#0-cài-đặt) |

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

Endpoint ở `http://127.0.0.1:14566`, chỉ mở trên `127.0.0.1`; đổi cổng bằng `LOCALSTACK_DEVOPS_PORT` trong `setup/.env` (không được trùng `LOCALSTACK_PORT` của DE, test sẽ từ chối). Service bật S3, IAM, STS, DynamoDB, KMS, SSM và Secrets Manager. Lần chạy test đầu tiên (cần mạng) tự tải đúng provider `hashicorp/aws` 6.12.0 (khoảng 150 MB, giải nén khoảng 780 MB) vào `~/.cache/devops-track/tofu-plugins`; từ đó test chạy offline. Provider mới hơn 6.12 chưa chạy được với LocalStack 4.4.0 (bảng DynamoDB, tag bucket S3), nên test chỉ cài bản này: ràng buộc như `~> 6.0` vẫn ra 6.12.0, ràng buộc loại trừ 6.12.0 thì test báo lỗi kèm lý do.

## Cluster kind devops-lab

Module 10, 11 và capstone m06 chạy trên một cluster kind tên `devops-lab`, cấu hình ở `setup/kind/devops-lab.yaml`: một control plane và hai worker, node image `kindest/node:v1.34.0` ghim theo digest (mặc định của kind 0.30.0), API server và cổng 80/443 của ingress (`18080`, `18443`) chỉ mở trên `127.0.0.1`, control plane có nhãn `ingress-ready=true`. CNI là kindnet mặc định của kind, bản này thực thi NetworkPolicy (đã kiểm: policy deny-all chặn kết nối giữa hai pod), nên không cần Calico.

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

Test không bao giờ tạo hay xoá cluster. `require_cluster` skip với thông báo riêng khi Docker tắt, khi chưa có cluster, khi node đang dừng (kèm lệnh `docker start`) và khi API server chưa trả `ok` cho `/readyz` trong 5 giây. Mỗi lần chạy, test lấy kubeconfig bằng `kind get kubeconfig --name devops-lab` vào thư mục tạm, không đọc `KUBECONFIG` hay `~/.kube` của bạn, nên cluster thật mà `~/.kube/config` đang trỏ tới không bao giờ bị đụng. Mỗi test làm việc trong namespace riêng `devops-ex-<id>` (nhãn `devops-ex=<id>`, Pod Security `baseline`) bằng token của một ServiceAccount chỉ có quyền trong namespace đó (không impersonate, không xin token cho ServiceAccount khác), và xoá namespace khi xong. Trong lúc có test chạy, cluster từ chối PersistentVolume hostPath của mọi user không phải thành phần hệ thống, kể cả admin; PV `local` chỉ testkit tạo, trong thư mục `/srv/devops-lab-pv` của worker. Test bị ngắt giữa chừng có thể để lại namespace; xem và xoá bằng:

```bash
KUBECONFIG=~/.kube/devops-lab.yaml kubectl get namespaces,clusterroles,clusterrolebindings,validatingadmissionpolicies,validatingadmissionpolicybindings -l devops-ex
KUBECONFIG=~/.kube/devops-lab.yaml kubectl delete namespaces,clusterroles,clusterrolebindings,validatingadmissionpolicies,validatingadmissionpolicybindings -l devops-ex
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

### Bài thao tác node (cordon, drain, taint)

Bài cần cordon, drain hay taint worker (module 11) làm qua `KubeLab.node_action` của testkit, chỉ trên worker, `close()` hoàn tác.
Trạng thái node là của cả cluster, nên testkit giữ khoá `~/.cache/devops-track/kube-nodes.lock` suốt từ lần thao tác node đầu tiên
tới khi hoàn tác xong: hai bài như vậy không bao giờ chạy chồng nhau, kể cả ở hai terminal. Tệp test của các bài này mang marker
`kube_nodes`; muốn chạy song song phần còn lại thì loại chúng ra (`-m "not kube_nodes"`). Trong lúc bài drain một worker, pod của bài
khác, Traefik và metrics-server đang nằm trên worker đó cũng bị dời; sau khi hoàn tác, testkit chờ chúng available lại rồi mới trả.

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
