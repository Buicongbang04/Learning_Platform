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

## 8. Tài liệu tham khảo

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
- OpenTofu docs: https://opentofu.org/docs/
- AWS CDK Developer Guide: https://docs.aws.amazon.com/cdk/v2/guide/home.html
- Prometheus, exposition formats: https://prometheus.io/docs/instrumenting/exposition_formats/
- Prometheus, naming best practices: https://prometheus.io/docs/practices/naming/
- Google SRE Book, chương Monitoring Distributed Systems: https://sre.google/sre-book/monitoring-distributed-systems/
- Sách: Joe Reis & Matt Housley, *Fundamentals of Data Engineering* (O'Reilly, 2022), chương về undercurrents (DataOps).
- Sách: Kief Morris, *Infrastructure as Code* (O'Reilly, 2nd ed., 2020).
