# DevOps cho Data

Pipeline dữ liệu chạy được trên laptop chưa phải pipeline dùng được trong production. Để một job
nạp đơn hàng Olist chạy mỗi giờ, đúng phiên bản thư viện, có người biết khi nó hỏng và sửa xong thì
deploy lại trong vài phút, bạn cần các kỹ thuật của DevOps: đóng gói bằng **container**, điều phối
bằng **Kubernetes**, tự động kiểm thử và triển khai bằng **CI/CD**, dựng hạ tầng bằng
**Infrastructure as Code**, và quan sát hệ thống bằng **monitoring**. Module này đi qua từng mảnh,
luôn từ góc nhìn Data Engineer: cái gì cần biết sâu, cái gì chỉ cần biết đủ để làm việc với đội
platform.

## 1. Vì sao Data Engineer cần DevOps

Data Analyst/Data Scientist thường dừng ở notebook hoặc script. Data Engineer chịu trách nhiệm cho
việc **dữ liệu đến đúng, đủ, đúng giờ, mỗi ngày**. Những lỗi thường gặp khi thiếu DevOps:

| Triệu chứng | Nguyên nhân gốc | Kỹ thuật giải quyết |
| --- | --- | --- |
| "Chạy trên máy em thì được" | Môi trường khác nhau (Python, pandas, driver) | Docker image pin version |
| Sửa một dòng SQL làm vỡ dashboard | Không có test, merge thẳng vào `main` | CI chạy unit/integration test cho mỗi PR |
| Không ai biết job hôm qua không chạy | Không có metric, không có cảnh báo | Monitoring freshness/volume + alert |
| Bucket S3 ở staging khác production | Tạo bằng tay trên console | Terraform/OpenTofu, mỗi môi trường một workspace/biến |
| Deploy là SSH vào server rồi `git pull` | Không có quy trình phát hành | CD: build image, deploy theo môi trường, rollback |

Khái niệm nền tảng của DevOps áp vào data (đôi khi gọi là **DataOps**):

- **Reproducibility**: cùng input + cùng code + cùng môi trường = cùng output. Container và lock file
  (`uv.lock`, `requirements.txt` có pin) là công cụ chính.
- **Automation**: mọi bước lặp lại (test, build, deploy, tạo hạ tầng) đều chạy bằng máy.
- **Idempotency**: chạy lại một job hay một lệnh `terraform apply` không làm hỏng trạng thái
  (không nhân đôi dòng, không tạo hai bucket).
- **Observability**: biết hệ thống đang ở trạng thái nào mà không cần SSH vào xem log.
- **Shift-left testing**: bắt lỗi sớm nhất có thể (ở PR thay vì ở dashboard của sếp).

```mermaid
flowchart LR
    Dev[Code pipeline<br/>+ test] -->|git push| CI[CI: lint, unit,<br/>integration test]
    CI -->|build| IMG[(Container registry<br/>image:sha)]
    IaC[Terraform] -->|apply| INFRA[Bucket, DB,<br/>K8s cluster]
    IMG -->|CD deploy| K8S[Kubernetes CronJob]
    INFRA --> K8S
    K8S -->|metrics, logs| MON[Prometheus / Datadog]
    MON -->|alert| ONCALL[Slack / PagerDuty]
    ONCALL -->|fix| Dev
```

## 2. Docker: đóng gói job dữ liệu

### 2.1. Image, container, layer

- **Image**: một gói chỉ đọc gồm hệ điều hành tối giản + Python + thư viện + code. Được build từ
  `Dockerfile`, đặt tên `repo:tag` (vd. `olist-ingest:1.4.0`).
- **Container**: một tiến trình chạy từ image, có filesystem riêng, mạng riêng. Container là
  ephemeral: dữ liệu ghi bên trong mất khi container bị xoá, trừ khi mount **volume**.
- **Layer**: mỗi lệnh `RUN`, `COPY`, `ADD` tạo một layer. Layer được cache; khi một layer thay đổi,
  **mọi layer sau nó phải build lại**. Vì thế thứ tự lệnh quyết định tốc độ build.
- **Registry**: nơi lưu image (Docker Hub, GHCR, ECR, GCR/Artifact Registry).

So sánh nhanh với các cách cô lập môi trường khác:

| | virtualenv / uv | Docker container | Virtual Machine |
| --- | --- | --- | --- |
| Cô lập | Chỉ thư viện Python | Process, filesystem, network | Toàn bộ OS, kernel riêng |
| Khởi động | Tức thì | Vài trăm ms – vài giây | Vài chục giây |
| Kích thước | MB | Vài chục – vài trăm MB | GB |
| Mang sang máy khác | Phải cài lại, phụ thuộc OS | Chạy y hệt ở mọi nơi có Docker | Nặng, phụ thuộc hypervisor |
| Dùng cho | Phát triển local | Đóng gói job, service, CI | Cô lập mạnh, OS khác |

### 2.2. Dockerfile cho một job Python

Job `ingest_orders.py` đọc CSV đơn hàng Olist rồi ghi vào PostgreSQL:

```dockerfile
# Pin phiên bản: không dùng python:latest (hôm nay 3.12, mai 3.13 là vỡ)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) Copy riêng file dependency trước -> layer này chỉ build lại khi requirements đổi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy code sau -> sửa code chỉ build lại từ đây
COPY src/ ./src/

# 3) Không chạy bằng root
RUN useradd --create-home --uid 10001 appuser
USER appuser

# 4) Exec form (JSON array): tín hiệu SIGTERM tới thẳng Python, không qua /bin/sh
ENTRYPOINT ["python", "-m", "src.ingest_orders"]
CMD ["--date", "2018-08-01"]
```

`.dockerignore` giữ build context nhỏ và không lỡ đưa bí mật hay dữ liệu vào image:

```text
.git
.venv
__pycache__/
*.pyc
data/
.env
```

Các quy tắc hay bị hỏi khi review Dockerfile:

1. **Pin base image** (`python:3.12-slim`, tốt hơn nữa là pin digest `@sha256:...`).
2. **Sắp xếp layer từ ít đổi tới hay đổi**: dependency trước, code sau.
3. **`--no-cache-dir`** cho pip, xoá cache apt (`rm -rf /var/lib/apt/lists/*`) trong cùng `RUN`.
4. **Non-root `USER`**: nếu container bị chiếm quyền, kẻ tấn công không có root.
5. **Exec form** cho `CMD`/`ENTRYPOINT` để nhận tín hiệu dừng đúng cách (graceful shutdown).
6. **Không nhét secret** vào image (`ENV DB_PASSWORD=...` nằm vĩnh viễn trong layer). Truyền qua
   biến môi trường lúc chạy hoặc secret manager.
7. **Một container một việc**: job ingest và database là hai container.

### 2.3. Multi-stage build

Thư viện như `psycopg` hoặc `pyarrow` đôi khi cần compiler để build wheel. Compiler không cần lúc
chạy. Multi-stage build tách **stage build** (đủ công cụ) và **stage runtime** (tối giản):

```dockerfile
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY src/ ./src/
RUN useradd --uid 10001 appuser
USER appuser
HEALTHCHECK --interval=30s --timeout=3s CMD ["python", "-c", "import src"]
ENTRYPOINT ["python", "-m", "src.ingest_orders"]
```

Image cuối không chứa `gcc`, nhỏ hơn và ít lỗ hổng (CVE) hơn.

### 2.4. Docker Compose cho môi trường local

Compose mô tả nhiều container chạy cùng nhau. Repo này dùng `setup/docker-compose.yml` cho
PostgreSQL, Kafka, MinIO… Một compose cho job ingest + Postgres:

```yaml
services:
  postgres:
    image: postgres:16.4
    environment:
      POSTGRES_USER: de
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}   # đọc từ .env, không hardcode
      POSTGRES_DB: olist
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U de -d olist"]
      interval: 5s
      retries: 10
  ingest:
    build: .
    environment:
      DATABASE_URL: postgresql://de:${POSTGRES_PASSWORD}@postgres:5432/olist
    depends_on:
      postgres:
        condition: service_healthy   # chờ DB sẵn sàng, không chỉ "đã start"
volumes:
  pgdata:
```

Lưu ý: trong mạng compose, các service gọi nhau bằng **tên service** (`postgres:5432`), không phải
`localhost`.

## 3. Kubernetes cho job dữ liệu

Docker chạy container trên một máy. Khi cần chạy hàng trăm job trên nhiều máy, tự khởi động lại
khi lỗi, giới hạn CPU/RAM, lên lịch, bạn cần **orchestrator**: Kubernetes (K8s).

### 3.1. Các object cần biết

| Object | Vai trò | Ví dụ trong data |
| --- | --- | --- |
| **Pod** | Đơn vị chạy nhỏ nhất, 1+ container chung network/volume | Một lần chạy job ingest |
| **Deployment** | Giữ N bản sao Pod luôn chạy, rolling update | API phục vụ feature, Kafka consumer |
| **Job** | Chạy Pod tới khi xong (exit 0), retry với `backoffLimit` | Backfill một ngày dữ liệu |
| **CronJob** | Tạo Job theo lịch cron | Ingest đơn hàng Olist mỗi giờ |
| **ConfigMap** | Cấu hình không bí mật (key-value) | `TARGET_SCHEMA=staging` |
| **Secret** | Cấu hình bí mật (base64, nên bật encryption at rest) | Mật khẩu Postgres |
| **Service** | Địa chỉ mạng ổn định cho một nhóm Pod | Endpoint của Postgres trong cluster |
| **PersistentVolumeClaim** | Ổ đĩa bền vững | Dữ liệu của Postgres/Kafka |
| **Namespace** | Phân vùng logic | `data-staging`, `data-prod` |

```mermaid
flowchart TB
    CJ[CronJob<br/>schedule: 0 * * * *] -->|mỗi giờ tạo| J[Job<br/>backoffLimit: 3]
    J -->|tạo| P[Pod]
    CM[ConfigMap<br/>TARGET_SCHEMA] -.envFrom.-> P
    S[Secret<br/>DB_PASSWORD] -.envFrom.-> P
    P -->|ghi| SVC[Service postgres]
    SVC --> PG[(Postgres Pod + PVC)]
```

### 3.2. CronJob cho job ingest

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: olist-ingest
  namespace: data
spec:
  schedule: "0 * * * *"
  concurrencyPolicy: Forbid          # lần chạy trước chưa xong thì không chạy chồng
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      backoffLimit: 3
      activeDeadlineSeconds: 1800
      template:
        spec:
          restartPolicy: OnFailure
          securityContext:
            runAsNonRoot: true
          containers:
            - name: ingest
              image: ghcr.io/acme/olist-ingest:1.4.0
              envFrom:
                - configMapRef: { name: olist-ingest-config }
                - secretRef: { name: olist-db }
              resources:
                requests: { cpu: "250m", memory: "512Mi" }
                limits: { cpu: "1", memory: "1Gi" }
```

Những điểm đáng nhớ:

- **`requests`** dùng để xếp Pod lên node; **`limits`** là trần. Vượt memory limit, Pod bị
  `OOMKilled`; đây là lỗi kinh điển của job pandas đọc nguyên file to vào RAM.
- **`concurrencyPolicy: Forbid`** tránh hai lần chạy ghi cùng một partition. Dù vậy job vẫn nên
  idempotent, vì retry vẫn có thể xảy ra.
- **Secret không phải mã hoá**: base64 chỉ là encoding. Dùng External Secrets/Vault/Sealed Secrets
  và RBAC để bảo vệ.

### 3.3. Managed Kubernetes: GKE, EKS, AKS

Tự vận hành control plane rất tốn công, nên đa số công ty dùng dịch vụ managed:

| | GKE (Google) | EKS (AWS) | AKS (Azure) |
| --- | --- | --- | --- |
| Control plane | Managed, có chế độ Autopilot (không quản node) | Managed, tính phí theo giờ cluster | Managed, control plane miễn phí ở tier cơ bản |
| Node | Node pool hoặc Autopilot | Managed node group, Fargate | Node pool, virtual nodes |
| IAM cho Pod | Workload Identity | IRSA / EKS Pod Identity | Workload Identity |
| Hệ sinh thái data | BigQuery, GCS, Dataproc | S3, Glue, EMR on EKS, MSK | ADLS, Synapse, Event Hubs |

Data Engineer thường không dựng cluster, nhưng phải viết được manifest, đọc được
`kubectl get pods`, `kubectl logs`, `kubectl describe pod` để debug job của mình. Airflow có
`KubernetesPodOperator`, Spark có `spark-submit --master k8s://...` chạy thẳng trên K8s.

## 4. CI/CD cho pipeline dữ liệu

- **Continuous Integration (CI)**: mỗi lần push/PR, máy tự chạy lint, test, build. Mục tiêu: nhánh
  `main` luôn ở trạng thái xanh.
- **Continuous Delivery/Deployment (CD)**: sau khi CI xanh, tự đóng gói và triển khai lên
  staging, rồi production (tự động hoặc qua bước duyệt).

```mermaid
flowchart LR
    PR[Pull request] --> L[Lint<br/>ruff, sqlfluff]
    L --> U[Unit test<br/>pytest]
    U --> I[Integration test<br/>Postgres service container]
    I -->|merge vào main| B[Build image<br/>tag = git sha]
    B --> STG[Deploy staging<br/>+ smoke test]
    STG -->|approval| PRD[Deploy production]
```

### 4.1. GitHub Actions

Workflow là tệp YAML trong `.github/workflows/`. Cấu trúc: `on` (sự kiện) → `jobs` → `steps`.

```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
permissions:
  contents: read            # least privilege cho GITHUB_TOKEN
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true  # push mới huỷ lần chạy cũ của cùng nhánh
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_USER: de, POSTGRES_PASSWORD: de, POSTGRES_DB: de }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U de" --health-interval 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: pytest -q
        env:
          POSTGRES_DSN: postgresql://de:de@localhost:5432/de
```

Khái niệm chính: **job** chạy song song trừ khi có `needs`; **matrix** chạy cùng job với nhiều
phiên bản; **secrets** (`${{ secrets.X }}`) không in ra log; **environment** (`staging`,
`production`) gắn secret riêng và quy tắc duyệt; **OIDC** (`permissions: id-token: write`) cho
phép đăng nhập AWS/GCP không cần lưu access key dài hạn.

### 4.2. So sánh công cụ CI/CD

| Công cụ | Kiểu | Điểm mạnh | Khi nào chọn |
| --- | --- | --- | --- |
| **GitHub Actions** | CI/CD, YAML trong repo | Marketplace action lớn, gắn chặt GitHub | Code trên GitHub |
| **GitLab CI** | CI/CD, `.gitlab-ci.yml` với `stages` | Tích hợp sẵn registry, environments, self-host | Code trên GitLab, on-prem |
| **CircleCI** | CI/CD SaaS, `orbs` | Nhanh, cache tốt, resource class linh hoạt | Đội cần tốc độ CI, đa nền tảng |
| **Jenkins** | Server tự host, Groovy | Linh hoạt tuyệt đối, plugin nhiều | Doanh nghiệp có sẵn hạ tầng |
| **ArgoCD** | CD kiểu **GitOps** cho K8s | Cluster tự đồng bộ theo Git, rollback = revert commit | Deploy lên Kubernetes |

**GitOps (ArgoCD, Flux)** đảo chiều: thay vì CI `kubectl apply` vào cluster (push), một agent
trong cluster liên tục so sánh manifest trong Git với trạng thái thật và tự đồng bộ (pull). Git là
nguồn sự thật duy nhất, mọi thay đổi có lịch sử và review.

### 4.3. CI/CD riêng cho data khác gì phần mềm thường

- **Test cần dữ liệu**: dùng fixture nhỏ, tổng hợp (Faker), không dùng dữ liệu production chứa PII.
- **Thay đổi schema**: migration (Alembic, Flyway), kiểm tra backward compatibility.
- **dbt**: `dbt build --select state:modified+` chỉ chạy model bị đổi và hạ nguồn của nó (slim CI).
- **Data diff**: so sánh output của nhánh mới với production trước khi merge.
- **Deploy DAG**: Airflow đọc DAG từ thư mục; CD là đồng bộ thư mục DAG + image task.

### 4.4. GitLab CI, CircleCI và ArgoCD trong thực tế

Ba công cụ trong bảng 4.2 giải cùng bài toán với GitHub Actions nhưng khác chỗ đặt cấu hình và mô hình
chạy. Cùng pipeline "lint → test → build image → deploy" viết bằng từng công cụ:

**GitLab CI** (`.gitlab-ci.yml`): job gom theo `stages`, chạy trên **runner** (shared của gitlab.com hoặc
runner tự host trong mạng công ty, đọc được database nội bộ mà không mở firewall). Registry, environments,
review app và quét bảo mật có sẵn trong cùng sản phẩm.

```yaml
stages: [test, build, deploy]

test:
  stage: test
  image: python:3.12-slim
  services: [postgres:16]
  variables: { POSTGRES_USER: de, POSTGRES_PASSWORD: de, POSTGRES_DB: de }
  script:
    - pip install -r requirements.txt
    - ruff check . && pytest -q

build:
  stage: build
  image: docker:27
  services: [docker:27-dind]
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  rules: [{ if: '$CI_COMMIT_BRANCH == "main"' }]

deploy_prod:
  stage: deploy
  environment: production
  when: manual                       # bước duyệt tay trước production
  script: ./deploy.sh $CI_COMMIT_SHA
  rules: [{ if: '$CI_COMMIT_BRANCH == "main"' }]
```

**CircleCI** (`.circleci/config.yml`): SaaS chuyên CI, mạnh ở tốc độ (cache layer Docker, chia test song
song theo thời gian chạy bằng `circleci tests split`), chọn cỡ máy bằng `resource_class`, và **orbs** là gói
cấu hình dùng lại (vd. orb `aws-ecr` để build/push image trong vài dòng). Hợp khi bộ test lớn và thời gian CI
là vấn đề, còn code có thể ở GitHub hay Bitbucket.

**ArgoCD** chỉ làm phần CD cho Kubernetes theo GitOps. CI (bất kỳ công cụ nào ở trên) build image rồi sửa
tag trong repo manifest; ArgoCD thấy Git đổi và tự đồng bộ cluster:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: { name: olist-ingest, namespace: argocd }
spec:
  project: default
  source:
    repoURL: https://github.com/your-org/data-platform-manifests
    path: apps/olist-ingest/overlays/prod      # Kustomize overlay của môi trường prod
    targetRevision: main
  destination: { server: https://kubernetes.default.svc, namespace: data-jobs }
  syncPolicy:
    automated: { prune: true, selfHeal: true }   # ai sửa tay trên cluster sẽ bị đưa về đúng Git
```

Chọn thế nào:

| Tình huống | Chọn |
| --- | --- |
| Code trên GitHub, đội nhỏ, deploy lên Airflow/VM/cloud function | GitHub Actions |
| Công ty dùng GitLab tự host, cần runner trong mạng nội bộ | GitLab CI |
| Bộ test chạy lâu, cần song song hoá và cache mạnh | CircleCI |
| Job dữ liệu chạy trên Kubernetes, nhiều môi trường, cần audit mọi thay đổi | CI bất kỳ + ArgoCD (hoặc Flux) |

Không chọn hai công cụ CI cho cùng một repo. Kết hợp hợp lý duy nhất là một CI + một công cụ GitOps cho CD.

## 5. Infrastructure as Code (IaC)

Tạo bucket bằng tay trên console thì nhanh lần đầu, nhưng không review được, không lặp lại được
cho staging/production, không biết ai đổi gì. IaC mô tả hạ tầng bằng code, đưa vào Git.

### 5.1. Declarative vs imperative

| | Declarative | Imperative |
| --- | --- | --- |
| Bạn viết | Trạng thái mong muốn: "cần 2 bucket có versioning" | Các bước: "tạo bucket A, rồi bật versioning" |
| Công cụ | Terraform/OpenTofu, CloudFormation, K8s manifest | Script `aws cli`, boto3, Ansible (một phần) |
| Chạy lại | Tự tính diff, không có gì đổi thì không làm gì | Phải tự kiểm tra tồn tại, dễ tạo trùng |
| Drift | Phát hiện được bằng `plan` | Khó phát hiện |

Các tính chất cần đạt:

- **Idempotency**: `terraform apply` lần hai không thay đổi gì nếu code không đổi.
- **Reusability**: đóng gói thành **module** (vd. module `data_lake` tạo bucket raw/curated với
  chuẩn bảo mật) dùng lại cho nhiều dự án.
- **Environment management**: cùng code, khác biến (`environment = "staging"`), state tách riêng
  (backend S3 khác key, hoặc workspace).

### 5.2. Terraform / OpenTofu

Quy trình: `terraform init` (tải provider) → `plan` (xem diff) → `apply` (thực thi) → state được
lưu (nên ở remote backend có khoá, vd. S3 + DynamoDB lock).

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment phải là dev, staging hoặc prod."
  }
}

locals {
  tags = { project = "olist", environment = var.environment, managed_by = "terraform" }
}

resource "aws_s3_bucket" "raw" {
  bucket = "olist-raw-${var.environment}"
  tags   = local.tags
}

resource "aws_s3_bucket_versioning" "raw" {
  bucket = aws_s3_bucket.raw.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

output "raw_bucket_name" { value = aws_s3_bucket.raw.bucket }
```

**OpenTofu** là fork mã nguồn mở của Terraform (sau khi HashiCorp đổi giấy phép sang BSL năm
2023), cú pháp HCL tương thích, lệnh `tofu` thay `terraform`.

### 5.3. So sánh công cụ IaC

| Công cụ | Ngôn ngữ | Cloud | Ghi chú |
| --- | --- | --- | --- |
| Terraform | HCL | Đa cloud, hàng nghìn provider | Phổ biến nhất, giấy phép BSL |
| OpenTofu | HCL | Như Terraform | Mã nguồn mở (MPL), Linux Foundation |
| AWS CDK | TypeScript, Python… | AWS (sinh CloudFormation) | Dùng vòng lặp, class của ngôn ngữ thật |
| Pulumi | Python, TS, Go… | Đa cloud | Như CDK nhưng đa cloud, có state riêng |
| CloudFormation | YAML/JSON | AWS | Native AWS, không cần quản state |

Ví dụ AWS CDK bằng Python cho cùng bucket:

```python
from aws_cdk import App, Stack, aws_s3 as s3
from constructs import Construct

class DataLakeStack(Stack):
    def __init__(self, scope: Construct, id: str, env_name: str, **kw):
        super().__init__(scope, id, **kw)
        for zone in ["raw", "curated"]:
            s3.Bucket(self, f"{zone}-bucket",
                      bucket_name=f"olist-{zone}-{env_name}",
                      versioned=True,
                      encryption=s3.BucketEncryption.S3_MANAGED,
                      block_public_access=s3.BlockPublicAccess.BLOCK_ALL)

app = App()
DataLakeStack(app, "olist-staging", env_name="staging")
app.synth()
```

### 5.4. Declarative, imperative và reusability trong thực tế

Ranh giới ở 5.1 không tuyệt đối. **Pulumi** và **AWS CDK** cho viết bằng Python/TypeScript (vòng lặp,
hàm, class: phong cách imperative), nhưng kết quả vẫn là một mô tả trạng thái mong muốn mà engine so diff
rồi áp dụng; tức là imperative ở cách viết, declarative ở cách chạy. Ngược lại, **Ansible** viết YAML trông
như declarative nhưng chạy tuần tự từng task, idempotent hay không tuỳ module. Câu hỏi đúng không phải
"YAML hay Python" mà là: công cụ có giữ **state** và tính **diff** trước khi thay đổi không? Có thì xem trước
được (`plan`, `cdk diff`, `pulumi preview`) và phát hiện drift.

Dùng script imperative (boto3, `gcloud`, `aws cli`) cho việc một lần hoặc thao tác vận hành (xoay key, chạy
backfill), không dùng để dựng hạ tầng lâu dài.

**Reusability** đến từ module có giao diện rõ ràng. Một module `data_lake` tốt nhận vài biến (tên dự án,
môi trường, số ngày giữ dữ liệu), tự áp chuẩn bắt buộc (mã hoá, chặn public, tag, lifecycle) và trả output
(tên bucket, ARN):

```hcl
module "data_lake" {
  source         = "git::https://github.com/your-org/tf-modules.git//data_lake?ref=v1.4.0"
  project        = "olist"
  environment    = var.environment
  raw_retention_days = 90
}

output "raw_bucket" { value = module.data_lake.raw_bucket_name }
```

Ghim phiên bản module (`ref=v1.4.0`) để nâng cấp module không âm thầm đổi hạ tầng production. Module nên
nhỏ và làm một việc; module "làm cả platform" với 80 biến thì không ai dám sửa.

### 5.5. Environment management

Mục tiêu: dev, staging, prod **cùng code**, khác **biến** và khác **state**, để thứ đã thử ở staging chính
là thứ lên prod.

| Cách | Cấu trúc | Ưu | Nhược |
| --- | --- | --- | --- |
| Thư mục theo môi trường | `envs/dev/main.tf`, `envs/prod/main.tf` cùng gọi module, mỗi thư mục một backend | Rõ ràng, prod tách hẳn, phân quyền theo thư mục | Lặp vài dòng gọi module |
| Terraform workspace | Một thư mục, `terraform workspace select prod` | Ít file | Dễ apply nhầm môi trường, cùng backend nên khó tách quyền |
| Terragrunt | `terragrunt.hcl` mỗi môi trường kế thừa cấu hình chung | DRY cho nhiều môi trường/region | Thêm một công cụ phải học |

Thực tế phổ biến: thư mục theo môi trường, mỗi môi trường **một tài khoản/project cloud riêng** (dev không
thể chạm prod kể cả khi lỗi cấu hình), biến trong `*.tfvars`, secret lấy từ secret manager chứ không nằm
trong tfvars. Thay đổi đi theo thứ tự: PR chạy `plan` cho cả ba môi trường, merge thì apply dev, staging,
rồi prod sau khi duyệt.

### 5.6. Công cụ IaC native của cloud: CloudFormation, ARM/Bicep, Google Deployment Manager

Mỗi cloud có công cụ declarative riêng, không cần quản state vì cloud giữ hộ:

| Cloud | Công cụ | Định dạng | Ghi chú |
| --- | --- | --- | --- |
| AWS | CloudFormation | YAML/JSON (stack) | CDK sinh ra CloudFormation; rollback tự động khi stack lỗi |
| Azure | ARM template, **Bicep** | JSON, Bicep DSL | Bicep là cú pháp gọn hơn, biên dịch ra ARM |
| GCP | **Cloud Deployment Manager** | YAML + template Jinja2/Python | Tạo "deployment" gồm nhiều resource GCP |
| GCP | **Infrastructure Manager** | Terraform | Dịch vụ chạy Terraform được Google quản lý (state, log) |

Ví dụ Deployment Manager tạo bucket cho dữ liệu raw:

```yaml
# config.yaml, chạy: gcloud deployment-manager deployments create olist-raw --config config.yaml
resources:
  - name: olist-raw-dev
    type: storage.v1.bucket
    properties:
      location: ASIA-SOUTHEAST1
      versioning: { enabled: true }
      iamConfiguration: { uniformBucketLevelAccess: { enabled: true } }
```

Google đã thông báo ngừng hỗ trợ Deployment Manager (mốc 31/3/2026) và khuyên chuyển sang Infrastructure
Manager hoặc Terraform; bạn vẫn có thể gặp nó ở hạ tầng GCP cũ và cần đọc hiểu để migrate. Chọn công cụ
native khi tổ chức chỉ dùng một cloud và muốn hỗ trợ chính hãng; chọn Terraform/OpenTofu khi đa cloud, hoặc
cần quản cả tài nguyên ngoài cloud (Snowflake, Datadog, GitHub, Kafka topic) bằng cùng một công cụ, điều
rất thường gặp ở data platform.

## 6. Monitoring và observability cho pipeline

Ba trụ cột của observability: **metrics** (số liệu theo thời gian), **logs** (sự kiện chi tiết),
**traces** (đường đi của một request qua nhiều service). Với pipeline dữ liệu, thêm một lớp nữa:
**data observability**, tức là giám sát chính dữ liệu.

### 6.1. Metric quan trọng cho pipeline

| Metric | Câu hỏi trả lời | Ví dụ cảnh báo |
| --- | --- | --- |
| **Freshness** | Dữ liệu mới nhất cách đây bao lâu? | `orders` không cập nhật quá 2 giờ |
| **Volume** | Số dòng có bất thường không? | Hôm nay 120 đơn, trung bình 7 ngày là 3.000 |
| **Latency / duration** | Job chạy mất bao lâu, p95? | p95 vượt 30 phút |
| **Error rate** | Bao nhiêu lần chạy/bản ghi lỗi? | > 5% bản ghi vào dead-letter |
| **Schema** | Cột có bị thêm/xoá/đổi kiểu? | Cột `order_status` biến mất |
| **Distribution** | Giá trị có lệch? | Tỉ lệ `payment_value` null tăng vọt |

Freshness và volume quan trọng hơn "job có exit 0 không": job có thể thành công nhưng nạp 0 dòng.

### 6.2. Prometheus

Prometheus **pull** metric: nó định kỳ gọi HTTP `/metrics` của ứng dụng (scrape). Job batch chạy
ngắn không kịp bị scrape nên đẩy metric lên **Pushgateway**. Định dạng text exposition:

```text
# HELP pipeline_rows_processed_total Số dòng đã xử lý.
# TYPE pipeline_rows_processed_total counter
pipeline_rows_processed_total{pipeline="orders"} 98666
# HELP pipeline_last_success_timestamp_seconds Unix time lần chạy thành công gần nhất.
# TYPE pipeline_last_success_timestamp_seconds gauge
pipeline_last_success_timestamp_seconds{pipeline="orders"} 1.7301e+09
```

Bốn loại metric: **counter** (chỉ tăng, vd. tổng số dòng), **gauge** (lên xuống, vd. lag),
**histogram** (phân phối theo bucket, tính được p95 bằng `histogram_quantile`), **summary**.
Cảnh báo freshness bằng PromQL:

```text
time() - pipeline_last_success_timestamp_seconds{pipeline="orders"} > 7200
```

Code Python dùng thư viện `prometheus_client`:

```python
from prometheus_client import CollectorRegistry, Counter, Gauge, generate_latest

registry = CollectorRegistry()
rows = Counter("pipeline_rows_processed", "Số dòng đã xử lý.", ["pipeline"], registry=registry)
last_ok = Gauge("pipeline_last_success_timestamp_seconds", "Lần chạy OK gần nhất.",
                ["pipeline"], registry=registry)

rows.labels(pipeline="orders").inc(98666)
last_ok.labels(pipeline="orders").set_to_current_time()
print(generate_latest(registry).decode())
# push_to_gateway("pushgateway:9091", job="olist_ingest", registry=registry)  # cho batch job
```

Cẩn thận **cardinality**: không đặt label là `order_id` hay `customer_id`; mỗi giá trị label tạo
một time series riêng, hàng triệu series sẽ làm sập Prometheus.

### 6.3. Các công cụ khác

| Công cụ | Loại | Dùng cho |
| --- | --- | --- |
| Prometheus + Grafana | Metrics mã nguồn mở + dashboard | Tự host, chuẩn trong K8s |
| Datadog | SaaS metrics, logs, APM, data jobs monitoring | Một nơi cho mọi thứ, trả phí theo host |
| New Relic | SaaS APM, observability | Tương tự Datadog, mạnh về APM |
| Sentry | Error tracking | Gom exception kèm stack trace, biết lỗi nào mới xuất hiện |
| Great Expectations, Soda, Monte Carlo | Data quality / data observability | Kiểm tra dữ liệu (null, unique, freshness) |

Nguyên tắc cảnh báo: cảnh báo theo **triệu chứng người dùng thấy** (dữ liệu trễ, thiếu), có
**runbook** đi kèm, tránh alert fatigue (quá nhiều cảnh báo vô nghĩa khiến người trực bỏ qua).

### 6.4. Datadog, Sentry, New Relic: chọn thế nào

Ba công cụ thương mại này hay bị gộp chung là "monitoring" nhưng trả lời câu hỏi khác nhau:

- **Sentry** trả lời "**code nào vừa ném exception, lần đầu khi nào, ảnh hưởng bao nhiêu lần chạy?**". Nó gom
  các exception giống nhau thành một issue, kèm stack trace, biến cục bộ, release/commit gây lỗi. Không thay
  được metric: job chạy "thành công" nhưng nạp 0 dòng thì Sentry im lặng.
- **Datadog** là nền tảng gộp metrics, logs, traces (APM), dashboard, alert, và có sản phẩm riêng cho
  pipeline (Data Jobs Monitoring cho Spark/Databricks/Airflow, Data Streams Monitoring cho độ trễ Kafka).
  Agent cài trên host/K8s tự thu thập; tính phí theo host, theo GB log, theo số custom metric.
- **New Relic** cùng nhóm với Datadog (full-stack observability), mạnh truyền thống về APM, tính phí theo
  lượng dữ liệu nạp và số user, có gói miễn phí 100 GB/tháng nên hợp để học và đội nhỏ.

| Tiêu chí | Prometheus + Grafana | Datadog | New Relic | Sentry |
| --- | --- | --- | --- | --- |
| Loại | Metrics OSS tự host | Observability SaaS | Observability SaaS | Error tracking (SaaS hoặc tự host) |
| Mạnh nhất ở | Metric K8s, chi phí thấp | Một nơi cho mọi tín hiệu, tích hợp sẵn 800+ | APM, truy vấn NRQL | Exception theo release |
| Chi phí | Công vận hành | Cao, tăng theo host/log/metric | Theo GB nạp + user | Theo số event lỗi |
| Bẫy | Tự lo HA, lưu trữ dài hạn | Hoá đơn tăng vọt vì log/metric cardinality cao | Như Datadog | Gửi cả lỗi kỳ vọng làm loãng issue |

Cách kết hợp phổ biến cho một đội data: **Sentry** cho exception của job Python + **một** nền tảng metric
(Prometheus/Grafana nếu đã có K8s và người vận hành, Datadog/New Relic nếu muốn mua dịch vụ) + data quality
check (Great Expectations, Soda, dbt test) cho chính dữ liệu. Instrument bằng **OpenTelemetry** khi có thể
để đổi nhà cung cấp không phải sửa code.

Gắn Sentry vào job batch chỉ vài dòng; đặt `release` bằng git SHA để biết lỗi xuất hiện từ phiên bản nào:

```python
import os
import sentry_sdk

sentry_sdk.init(
    dsn=os.environ["SENTRY_DSN"],
    environment=os.environ.get("ENV", "dev"),
    release=os.environ.get("GIT_SHA"),
    traces_sample_rate=0.0,          # job batch: chỉ cần lỗi, không cần trace
)

def main(run_date: str) -> None:
    sentry_sdk.set_tag("pipeline", "olist_ingest")
    sentry_sdk.set_tag("run_date", run_date)   # lọc lỗi theo ngày chạy khi backfill
    ...
```

## 7. Testing cho pipeline dữ liệu

```mermaid
flowchart TB
    E2E["End-to-end<br/>(ít, chậm, đắt)"] --- INT["Integration<br/>(DB thật/container)"]
    INT --- UNIT["Unit test<br/>(nhiều, nhanh, rẻ)"]
    DQ["Data quality checks<br/>chạy trong production"] -.-> E2E
```

| Loại test | Kiểm tra gì | Ví dụ với Olist | Chạy khi nào |
| --- | --- | --- | --- |
| **Unit** | Một hàm thuần, input nhỏ | `clean_orders` bỏ đơn thiếu `order_id`, chuẩn hoá status | Mỗi commit |
| **Integration** | Code + hệ thống thật (DB, S3) | Nạp vào SQLite/Postgres, chạy 2 lần vẫn đúng số dòng | Mỗi PR |
| **End-to-end** | Toàn bộ luồng nguồn → dashboard | CSV → staging → mart → truy vấn doanh thu theo bang | Trước release, nightly |
| **Functional** | Hành vi đúng yêu cầu nghiệp vụ | "Doanh thu tháng không tính đơn `canceled`" | Mỗi PR |
| **Smoke** | Hệ thống có sống không sau deploy | Job khởi động, kết nối DB, bảng có dữ liệu hôm nay | Ngay sau deploy |
| **Load / performance** | Chịu được khối lượng lớn | 10 triệu dòng trong < 15 phút, RAM < 2 GB | Trước thay đổi lớn |
| **A/B test** | So sánh hai phiên bản trên người dùng/dữ liệu thật | Thuật toán gợi ý mới vs cũ; hoặc chạy song song pipeline cũ/mới so output (shadow) | Khi ra quyết định |

Ví dụ unit + integration test bằng pytest và SQLite:

```python
import sqlite3
import pandas as pd

def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["order_id"]).drop_duplicates("order_id", keep="last")
    return df.assign(order_status=df["order_status"].str.strip().str.lower())

def load(df: pd.DataFrame, conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, order_status TEXT)")
    conn.executemany("INSERT OR REPLACE INTO orders VALUES (?, ?)",
                     df[["order_id", "order_status"]].itertuples(index=False))
    conn.commit()

def test_clean_orders_dedup_and_normalize():
    raw = pd.DataFrame({"order_id": ["a", "a", None], "order_status": [" Shipped", "DELIVERED ", "x"]})
    out = clean_orders(raw)
    assert out.to_dict("records") == [{"order_id": "a", "order_status": "delivered"}]

def test_load_is_idempotent():
    conn = sqlite3.connect(":memory:")
    df = clean_orders(pd.DataFrame({"order_id": ["a", "b"], "order_status": ["x", "y"]}))
    load(df, conn); load(df, conn)
    assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 2
```

Mẹo: test hành vi biên (rỗng, null, trùng, timezone, ký tự Unicode như "São Paulo"), dùng
**fixture** nhỏ viết tay, và với test chất lượng của chính bộ test có thể dùng **mutation testing**
(cố tình cài bug, test phải bắt được) như bài tập intermediate 03.

### 7.1. Functional, smoke, load và A/B testing: làm thế nào

Bảng trên nói mỗi loại test kiểm gì; phần này nói cách làm cụ thể cho pipeline dữ liệu và data API.

**Functional test** viết theo quy tắc nghiệp vụ, đọc như đặc tả: "cho dữ liệu X, khi chạy pipeline, thì
Y". Nguồn của nó là định nghĩa metric đã thống nhất với stakeholder, không phải cách code đang làm.

```python
def test_monthly_revenue_excludes_canceled_orders(run_pipeline):
    # Given: 2 đơn delivered (100 + 50) và 1 đơn canceled (999) trong tháng 2018-08
    orders = [("o1", "delivered", "2018-08-02", 100.0), ("o2", "delivered", "2018-08-20", 50.0),
              ("o3", "canceled", "2018-08-21", 999.0)]
    # When
    mart = run_pipeline(orders)
    # Then
    assert mart["2018-08"]["revenue"] == 150.0
```

**Smoke test** chạy ngay sau deploy, trên môi trường thật, dưới một phút, chỉ hỏi "có sống không": image
khởi động, kết nối được database/bucket bằng credential của môi trường đó, bảng đích có dữ liệu ngày gần
nhất, API trả 200 ở `/health` và một truy vấn mẫu. Fail thì rollback ngay, không chờ người dùng báo.

```bash
set -euo pipefail
curl -fsS --max-time 5 "$API_URL/health"
rows=$(psql "$DSN" -tAc "SELECT count(*) FROM mart.fct_orders WHERE order_date >= current_date - 1")
[ "$rows" -gt 0 ] || { echo "Smoke test: fct_orders không có dữ liệu mới"; exit 1; }
```

**Load / performance test** có hai dạng với DE:

- **Volume test cho batch**: chạy job trên dữ liệu gấp 3–10 lần hiện tại (sinh bằng Faker hoặc nhân bản
  có đổi khoá), đo thời gian, RAM peak, số file output, chi phí. Trả lời "năm sau dữ liệu gấp đôi thì job
  còn kịp trong cửa sổ 2 giờ không".
- **Load test cho serving** (API, dashboard, warehouse dưới truy vấn đồng thời): bắn N request với C client
  đồng thời, đo **p50/p95/p99 latency**, **throughput**, **error rate**, rồi so với **SLO** đã công bố
  (vd. p95 không quá 300 ms, lỗi dưới 0,1% ở 50 request/giây). Tách cache lạnh với cache nóng.

```mermaid
flowchart LR
    G[Load generator<br/>C client đồng thời] -->|N request| API[Serving API]
    API --> C[(Cache)]
    API --> W[(Warehouse / DuckDB)]
    G --> R[Kết quả từng request<br/>status, latency]
    R --> S[Tổng hợp<br/>p50, p95, throughput, error rate]
    S --> D{So với SLO}
    D -->|đạt| OK[Cho deploy tiếp]
    D -->|vi phạm| FAIL[Fail pipeline CI/CD]
```

Công cụ: **k6** (kịch bản JavaScript, khai báo ngưỡng SLO bằng `thresholds`, chạy trong CI), **Locust**
(kịch bản Python), **Vegeta**/**wrk** (CLI). Bài intermediate 04 tự viết một load generator nhỏ bằng
`httpx` + `asyncio` và chạy nó trên API metric của module 09 để hiểu các con số này được tính ra sao.
Hai lỗi đọc kết quả hay gặp: lấy trung bình các p95 (percentile không cộng trung bình được) và chỉ nhìn
latency mà bỏ qua error rate (lỗi 400 trả rất nhanh làm latency "đẹp").

**A/B testing** với DE có hai nghĩa:

1. **Thử nghiệm trên người dùng** (thuật toán gợi ý, giao diện): DE chịu trách nhiệm phần dữ liệu. Gán nhóm
   ổn định theo người dùng (`hash64(experiment_id + ":" + user_id) % 100 < 50` với hàm băm tất định,
   cùng ý tưởng hash partitioning ở module 01; không dùng `hash()` của Python vì nó đổi mỗi tiến trình), ghi log **exposure** (ai thấy phiên bản nào, lúc nào) tách khỏi log hành vi, kiểm tra
   **sample ratio mismatch** (chia 50/50 mà dữ liệu ra 47/53 nghĩa là pipeline mất sự kiện của một nhóm),
   và dựng bảng metric theo nhóm để analyst chạy kiểm định.
2. **Thay pipeline mới bằng cách chạy song song** (shadow / parallel run): pipeline cũ vẫn phục vụ, pipeline
   mới ghi vào schema riêng trên cùng input; mỗi ngày so số dòng, tổng tiền, tập khoá (data diff). Chỉ chuyển
   khi khớp trong vài chu kỳ liên tiếp, kể cả ngày cuối tháng và ngày có dữ liệu đến muộn.

## 8. Trực vận hành, rollback và khôi phục dữ liệu

### Từ cảnh báo tới hành động

**SLI** là số đo, ví dụ độ trễ dữ liệu. **SLO** là mục tiêu bạn đặt cho số đo đó.
Ví dụ của lab: 99% lô xuất bản trong 15 phút kể từ lúc nguồn sẵn sàng; ghi cách tính mẫu số,
khoảng đo và cách xử lý thời gian nguồn chưa sẵn sàng. Không gắn một ngưỡng cho mọi dataset.

Runbook là hướng dẫn người trực làm theo: ảnh hưởng gì, nhìn log/metric nào, ai sở hữu, điều kiện
dừng ghi, cách sửa và tiêu chí xác nhận phục hồi. Chỉ ghi “restart Airflow” chưa đủ.

| Tình huống | Hành động đầu | Xác nhận phục hồi |
| --- | --- | --- |
| Nguồn không truy cập được | Kiểm endpoint, credential, timeout; giữ checkpoint | Bắt kịp dữ liệu, freshness đạt mục tiêu |
| Job ghi nửa chừng | Dừng writer, xác định partition/run bị ảnh hưởng | Chạy lại không thiếu/trùng, đối chiếu nguồn |
| Deploy SQL sai làm tiền tăng đôi | Chặn xuất bản, rollback code, dựng lại dữ liệu bị sai | Tổng tiền theo ngày khớp bản chuẩn |
| Mất bảng hoặc bucket lab | Khôi phục vào nơi riêng từ backup đã kiểm | Tập khóa, tổng tiền và quyền truy cập đúng |

Rollback code chỉ phục hồi cách tính; dữ liệu đã bị ghi sai còn cần tính lại hoặc restore.
Đừng cho rằng deploy phiên bản cũ tự sửa được bảng hiện có.

### Backup phải được thử restore

**RPO** là lượng dữ liệu có thể chấp nhận mất, tính theo thời gian; **RTO** là thời gian mục tiêu để
dịch vụ dùng lại được. Ví dụ lab: RPO 1 giờ, RTO 30 phút. Đây là mục tiêu thực hành tự đặt, không phải
cam kết của hệ thống. Backup hằng ngày không đủ cho RPO 1 giờ nếu không có phần log/thay đổi bổ sung.

Bắt đầu với database lab riêng: dump bằng `pg_dump` bản phù hợp, restore vào database mới bằng
`pg_restore`, đối chiếu số dòng, khóa, tiền và quyền. Với object storage, lưu cả manifest/schema và
định nghĩa quyền; file dữ liệu riêng lẻ có thể chưa đủ dựng lại bảng. Kiểm tra backup đọc được sau khi
credential chính bị thu hồi. Bản backup chứa PII phải được bảo vệ theo chính sách retention và truy cập.

### Diễn tập M08

Tạo một lỗi sau khi đã có baseline, ghi thời điểm phát hiện và phục hồi. Nộp:
`incident.md` (ảnh hưởng, timeline, nguyên nhân), `runbook.md`, lệnh restore dùng database lab và
bảng đối chiếu. Đạt khi một người khác làm theo runbook có thể khôi phục mà không đoán bước còn thiếu.
Không thử xóa hoặc stop tài nguyên dùng chung của người khác; dùng database/thư mục lab do bạn tạo.

Tài liệu gốc: [PostgreSQL Backup and Restore](https://www.postgresql.org/docs/16/backup.html).

Có thể bắt đầu từ [kịch bản backup/restore của lab CDC](../07-streaming-kafka/cdc-lab.md):
lệnh dump và restore dùng container riêng của lab, khôi phục vào database mới để dễ đối chiếu.

## 9. Tài liệu tham khảo

- roadmap.sh, Data Engineer Roadmap: https://roadmap.sh/data-engineer
- Docker docs, Dockerfile best practices: https://docs.docker.com/build/building/best-practices/
- Docker docs, Multi-stage builds: https://docs.docker.com/build/building/multi-stage/
- Docker Compose specification: https://docs.docker.com/reference/compose-file/
- Kubernetes docs, CronJob: https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/
- Kubernetes docs, ConfigMap và Secret: https://kubernetes.io/docs/concepts/configuration/
- GitHub Actions docs: https://docs.github.com/en/actions
- GitLab CI/CD docs: https://docs.gitlab.com/ee/ci/
- CircleCI docs: https://circleci.com/docs/
- Argo CD docs: https://argo-cd.readthedocs.io/
- Terraform docs: https://developer.hashicorp.com/terraform/docs
- Terraform, Module structure và module sources: https://developer.hashicorp.com/terraform/language/modules
- Terragrunt docs: https://terragrunt.gruntwork.io/docs/
- Google Cloud Deployment Manager: https://cloud.google.com/deployment-manager/docs
- Google Cloud Infrastructure Manager: https://cloud.google.com/infrastructure-manager/docs
- Azure Bicep: https://learn.microsoft.com/azure/azure-resource-manager/bicep/overview
- OpenTofu docs: https://opentofu.org/docs/
- AWS CDK Developer Guide: https://docs.aws.amazon.com/cdk/v2/guide/home.html
- Prometheus, exposition formats: https://prometheus.io/docs/instrumenting/exposition_formats/
- Prometheus, naming best practices: https://prometheus.io/docs/practices/naming/
- Google SRE Book, chương Monitoring Distributed Systems: https://sre.google/sre-book/monitoring-distributed-systems/
- Sentry Python SDK: https://docs.sentry.io/platforms/python/
- Datadog Data Jobs Monitoring: https://docs.datadoghq.com/data_jobs/
- New Relic docs: https://docs.newrelic.com/
- OpenTelemetry docs: https://opentelemetry.io/docs/
- Grafana k6 docs, thresholds: https://grafana.com/docs/k6/latest/using-k6/thresholds/
- Locust docs: https://docs.locust.io/
- Ron Kohavi, Diane Tang, Ya Xu, *Trustworthy Online Controlled Experiments* (Cambridge, 2020), chương về sample ratio mismatch.
- Sách: Joe Reis & Matt Housley, *Fundamentals of Data Engineering* (O'Reilly, 2022), chương về undercurrents (DataOps).
- Sách: Kief Morris, *Infrastructure as Code* (O'Reilly, 2nd ed., 2020).
