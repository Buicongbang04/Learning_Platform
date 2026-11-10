# DevOps track Phase 3: module 12–16 + capstone m07–m09 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thành track DevOps.
- Viết module 12–16 và milestone m07–m09 đúng spec.
- Thêm các helper an toàn mà GitOps, observability, serverless và service mesh cần.
- Cập nhật README gốc của repo.

**Architecture:** Giữ nguyên cách làm của Phase 2.
- Mỗi helper mới nằm trong `testkit.py` và có unit test chứng minh tính chất an toàn. Helper được ghi vào bảng "Track DevOps" của `CONTENT_SPEC.md` và validator bắt buộc dùng nó.
- Thành phần cluster-scoped (ArgoCD, Linkerd) do admin cài một lần từ `setup/kind/<tên>/`, ghim digest, giống Gateway và metrics-server. Lab chỉ tạo object trong namespace của mình.
- Stack nhiều service (observability, Vault) chạy bằng `DockerLab.compose` hoặc profile `devops` của `setup/docker-compose.yml`.

**Tech Stack:** Python 3.12, uv, pytest; bubblewrap; Docker; kind + kubectl + Helm; ArgoCD; SOPS + age; Vault (dev mode); Prometheus, Grafana, Loki, OpenTelemetry Collector, Jaeger; LocalStack 4.4.0 + OpenTofu; image Lambda Python có Runtime Interface Emulator; Linkerd.

**Spec:** `docs/superpowers/specs/2026-11-01-devops-track-design.md`. Liên quan tới phase này:
- mục 4, hàng 12–16;
- mục 5, 6, 9;
- mục 7, hàng m07–m09.

Đọc kèm:
- Bàn giao Phase 2: `docs/superpowers/handoff-devops.md`.
- Quy ước bắt buộc: mục "Track DevOps" trong `CONTENT_SPEC.md`.
- Checklist: `docs/superpowers/research/2026-11-01-k8s-terraform-topic-checklists.md` (GitOps, observability, traces).

## Global Constraints

### Nơi làm việc
- Làm trong worktree `/home/bangbc/Documents/Learning_Platform-devops`, nhánh `devops-phase3` (tách từ `origin/main` 0e48c258, sau PR #19). Không đụng `/home/bangbc/Documents/Learning_Platform`.
- Không sửa track khác. Phần dùng chung (`testkit.py`, `setup/`, `pyproject.toml`) sửa tối thiểu và có test.

### Quy tắc đã có
- Mọi quy tắc của Phase 1 và Phase 2 vẫn giữ: mục "Track DevOps" trong `CONTENT_SPEC.md`, global constraints của plan Phase 2, các quyết định trong `handoff-devops.md`.

### Chạy code người học
- Code người học → `run_sandboxed`. Container → `DockerLab`. Cluster → `KubeLab`. Workflow → `act_run`. IaC → `TofuLab`.
- Không gọi `docker`, `kind`, `act`, `kubectl`, `helm`, `tofu` trực tiếp trong test module hay capstone. Công cụ mới của phase này (`argocd`, `sops`, `age`, `vault`, `linkerd`, `promtool`, `amtool`) cũng thêm vào danh sách cấm của validator khi chúng có helper riêng.
- Test không bao giờ dùng `~/.kube/config`, current-context, `~/.aws`, `~/.docker/config.json`, `~/.config/sops`, `VAULT_*`, `SOPS_*` hay biến môi trường cloud của người học.

### Tài nguyên máy
- Việc nặng của builder:
  - chạy với `nice -n 15 taskset -c 12-35`, `DEVOPS_CPUSET=12-35`;
  - mỗi lúc một job nặng;
  - tắt cluster hoặc stack sau mỗi đợt kiểm.
- Không đụng container hay volume của người dùng: `de-learning-*`, `fnb-*`, `neo4j-fnb`, `portainer`, cùng các service và tài nguyên `mlops`, `fde-ex-*`.
- Không xoá volume chung `act-toolcache`.
- Builder cài công cụ vào `~/.local/bin` theo đúng `## 0. Cài đặt` của module: kiểm checksum, phiên bản cố định, không sudo.
- Phiên bản: bản ổn định phát hành ít nhất 2 tuần trước ngày cài. Ghi bản đã kiểm và bản tối thiểu vào bảng của module và `setup/DEVOPS-TOOLS.md`.
- Công cụ trùng với track MLOps (act, kind, kubectl, Prometheus, k6…) phải ghi vào mục "Binary dùng chung với track MLOps", và không hạ bản mà track kia cần.

### Module
- Quy mô:
  - 5–8 phần `## `, không tính `## 0. Cài đặt`; ≥2 mermaid; phần cuối là tài liệu tham khảo;
  - `interview.md` ≥12 câu;
  - 5–9 bài (≥3 basic, ≥2 advanced), ≥1 bài sự cố cố ý.
- Nội dung bắt buộc:
  - bảng so sánh công cụ;
  - phần nhắc lại kiến thức trùng track DE chỉ một phần `## `, kèm link tới module DE;
  - không chép bài của track DE (nhất là DE 08, DE 11, DE 12).
- Bài sự cố: đề chỉ tả triệu chứng, nguyên nhân nằm trong `solutions/`.
- Advanced có rubric trong `SOLUTION.md`. Từ phase này, ít nhất một bài Advanced mỗi module là postmortem hoặc runbook chấm rubric (spec mục 5).
- Cloud thật luôn tuỳ chọn: chi phí ước tính, budget alarm, lệnh dọn, và bài local tương đương. Test không bao giờ cần cloud.

### Chấm và kiểm chứng
- Starter fail hoặc skip, không error.
- Khi công cụ đã cài, `SOLUTION=1` pass mà không skip vì thiếu công cụ. Test skip không tính là pass.
- Theo yêu cầu người dùng: không chạy lại `SOLUTION=1` của track khác. Chỉ chạy `uv run pytest tests -q` ở Task 12, và chạy test helper MLOps hay FDE khi đổi hành vi của helper chúng dùng (`DockerLab`, `run_sandboxed`).

### Văn phong và commit
- Không comment trong code; docstring chỉ khi thật cần.
- Tiếng Việt, giữ thuật ngữ tiếng Anh.
- Commit message tiếng Việt, không có dòng Co-Authored-By.

## Review Focus

1. **Application của ArgoCD trỏ sai chỗ.** Người học viết `Application` trỏ namespace khác, cluster khác, repo của lab khác, hoặc dùng `AppProject` `default`. Phải bị từ chối, và ArgoCD không bao giờ sync ra ngoài namespace của lab. Test: Task 2 (`test_argocd_project_restricts_destination_and_source`), cộng một probe trong review Task 3.
2. **Secret lộ dạng rõ.** Secret dạng rõ bị commit vào repo git của lab, hiện trong output test, log của ArgoCD hay `kubectl describe`; hoặc private key age nằm trong repo. Test phải fail kèm thông báo không in giá trị. Test: Task 1 (`test_sops_env_isolated_and_key_outside_repo`) và Task 3 (bài SOPS).
3. **Stack observability chạy đi chạy lại.** Dashboard, Prometheus hay Loki tạo volume ẩn danh, hoặc container giữ cổng cố định. Sau `close()` không được còn container, network hay volume nào của lab, kể cả volume ẩn danh. Lỗi này đã gặp ở Phase 2: `docker rm -f` không có `-v`. Test: Task 1 (`test_docker_lab_close_removes_anonymous_volumes`).
4. **Code serverless của người học với tới máy hay AWS thật.** Code đó gọi endpoint AWS thật, đọc credential của máy, hoặc cần socket Docker. Lambda chạy trong container RIE của `DockerLab`, không có socket, endpoint ép về `localstack-devops`, credential giả. Test: Task 6 (`test_lambda_lab_no_socket_and_dummy_credentials`).
5. **Bơm lỗi (chaos, game day m09) chạm tài nguyên ngoài lab.** Lỗi chỉ được bơm vào container hoặc pod có nhãn của lab. Không bao giờ chạm node của `devops-lab` ngoài `node_action`, container của người dùng hay cluster `mlops`. Test: Task 10 (`test_fault_injector_only_touches_lab_resources`).

---

### Task 1: Hạ tầng dùng chung, đợt 1 (dọn volume, SOPS, Vault)

**Files:**
- Modify: `testkit.py`, `tests/test_testkit_devops.py`, `tests/test_devops_track.py`, `CONTENT_SPEC.md`, `setup/docker-compose.yml`, `setup/.env.example`, `setup/DEVOPS-TOOLS.md`

**Interfaces:**
- **Sửa `DockerLab.close()`:** dùng `docker rm -f -v`, và `docker volume rm` volume ẩn danh của container lab. Hiện nay image `postgres`/`redis` có `VOLUME`, nên mỗi lần chạy để lại volume ẩn danh; Phase 2 đã dọn 14 cái.
- **Produces `sops_env(home: Path, key_file: Path) -> dict[str, str]`:**
  - đặt `SOPS_AGE_KEY_FILE=<key_file>`, `HOME=<home>`, `XDG_CONFIG_HOME=<home>/.config`;
  - không mang `SOPS_*`, `AGE_*`, `GNUPGHOME` của máy.
- **Produces `age_keypair(dir: Path) -> tuple[Path, str]`:** chạy `age-keygen -o` trong sandbox; trả về đường dẫn key và public key. Key nằm ngoài thư mục project của người học.
- **Produces `SOPS_VERSION`, `AGE_VERSION`** (bản đã kiểm) và mức tối thiểu tương ứng.
- **Produces service compose `vault-devops`** (profile `devops`):
  - `hashicorp/vault` ghim, dev mode;
  - `127.0.0.1:${DEVOPS_VAULT_PORT:-18200}:8200`, cpuset;
  - token root dev đọc từ `setup/.env` (mặc định là chuỗi cố định cho lab, không bí mật).
- **Produces `SERVICES["vault-devops"]` và `vault_env(token: str) -> dict`:** `VAULT_ADDR` của lab và `VAULT_TOKEN` truyền vào; không mang `VAULT_*` của máy.

- [ ] **Step 1:** Viết test thất bại:
  - `test_docker_lab_close_removes_anonymous_volumes`: chạy container của image có `VOLUME`; sau `close()`, `docker volume ls -f dangling=true` không có volume nào gắn với container đó.
  - `test_sops_env_isolated_and_key_outside_repo`
  - `test_age_keypair_in_sandbox`
  - `test_vault_service_loopback_profile_devops`
  - `test_vault_env_drops_host_vars`
- [ ] **Step 2:** `uv run pytest tests/test_testkit_devops.py -q -k "volume or sops or age or vault"` → FAIL.
- [ ] **Step 3:** Cài đặt. Cài `sops` và `age` vào `~/.local/bin` (release chính thức, có checksum); ghi URL và hash cho Task 3.
- [ ] **Step 4:** Chạy lại → PASS.
  - Chạy cả `tests/test_mlopskit.py` và `tests/test_fdekit.py`, vì đổi `DockerLab.close`.
  - Kiểm thật: bật `vault-devops` rồi tắt.
- [ ] **Step 5:** Commit `testkit: DockerLab xoá cả volume ẩn danh, helper SOPS/age, Vault dev cho DevOps`.

### Task 2: Hạ tầng cho GitOps: ArgoCD và git server trong cluster

**Files:**
- Create: `setup/kind/argocd/`
  - `kustomization.yaml`, kèm manifest release ArgoCD ghim chép nguyên;
  - git server nhỏ trong cluster (image ghim; builder chọn `git http-backend` sau nginx hoặc tương đương, ghi lý do);
  - CMP sidecar cho SOPS (ksops hoặc plugin `sops` + `kustomize`, builder chọn và ghi lý do).
- Modify: `testkit.py`, `tests/test_testkit_devops.py`, `tests/test_devops_track.py`, `CONTENT_SPEC.md`, `setup/DEVOPS-TOOLS.md`

**Interfaces:**
- **Cài đặt do admin làm một lần:**
  - ArgoCD trong namespace `argocd` với `application.namespaces: devops-ex-*` (Applications in any namespace);
  - repo-server có CMP SOPS đọc age key từ Secret `argocd/devops-sops-age` do admin tạo;
  - git server trong namespace `devops-git`.
  - Test không cài gì; `ex.require_argocd()` skip kèm đúng lệnh.
- **Produces `KubeLab.gitops_repo(path: Path) -> str`:**
  - đẩy bản chép của `path` (repo git mới, `SAFE_GIT_CONFIG`) lên repo riêng `devops-ex-<id>` của git server;
  - trả URL nội bộ để dùng trong `Application`;
  - `close()` xoá repo đó.
- **Produces `KubeLab.argocd_project() -> str`:**
  - admin tạo `AppProject` `devops-ex-<id>`: `sourceRepos` chỉ repo của lab, `destinations` chỉ namespace của lab trên `https://kubernetes.default.svc`, `sourceNamespaces` chỉ namespace của lab;
  - không có cluster-scoped whitelist;
  - xoá trong `close()`.
- **Quyền lab:** ghi `applications.argoproj.io` trong namespace của lab; không ghi `appprojects`. VAP mới `devops-ex-<id>-argocd` buộc `spec.project` = project của lab.
- **Produces `KubeLab.argocd_wait(app: str, *, health: str = "Healthy", sync: str = "Synced", timeout: float = 180) -> dict`:** đọc trạng thái `Application` bằng token của lab.
- **Produces `KubeLab.age_public_key` và `KubeLab.sops_age_recipient`:** public key của age key dùng chung do admin tạo, để người học mã hoá. Private key không bao giờ vào sandbox của người học.

- [ ] **Step 1:** Viết test thất bại:
  - `test_argocd_project_restricts_destination_and_source`: fake admin; argv của `AppProject` sinh ra đúng giới hạn.
  - `test_gitops_repo_isolated_per_lab`
  - `test_application_with_foreign_project_refused` (tĩnh và VAP)
  - `test_require_argocd_messages`
  - `test_age_private_key_never_in_sandbox`
- [ ] **Step 2:** Chạy → FAIL.
- [ ] **Step 3:** Cài đặt và kiểm thật trên `devops-lab`, ghim CPU:
  - một `Application` trỏ repo lab sync vào namespace lab;
  - một `Application` trỏ namespace khác bị chặn;
  - một Secret SOPS được giải mã khi sync.
  - Ghi thời gian sync và RAM của ArgoCD vào `CONTENT_SPEC.md`.
- [ ] **Step 4:** Tắt cluster. Commit `testkit: ArgoCD và git server trong devops-lab, AppProject riêng mỗi lab, CMP SOPS`.

### Task 3: Module 12-gitops-secrets

**Trọng tâm** (spec mục 4, hàng 12):
- Nguyên tắc GitOps: declarative, versioned, pull, reconcile.
- ArgoCD: Application, AppProject, sync policy (auto, prune, self-heal), sync wave và hook, health, ApplicationSet ở mức khái niệm, app-of-apps. So sánh với FluxCD.
- Quản lý secret: SOPS + age (mã hoá theo trường, `.sops.yaml`, xoay khoá), Vault dev (KV v2, dynamic secret ở mức khái niệm, policy, token TTL). Sealed Secrets và External Secrets Operator để so sánh. Secret manager của cloud (AWS Secrets Manager/SSM, GCP, Azure) trong bảng so sánh.
- `## 0. Cài đặt` cho `argocd` CLI, `sops`, `age`, `vault` CLI, và các bước admin cài `setup/kind/argocd/`.

**Bài bắt buộc:**
- Application đầu tiên: Kustomize của Olist Shop, sync tự động vào namespace lab. Kiểm Healthy/Synced, rồi sửa repo và kiểm reconcile.
- Bài SOPS:
  - mã hoá Secret bằng `.sops.yaml` với recipient của lab;
  - test kiểm không có giá trị rõ trong repo;
  - ArgoCD giải mã và pod đọc được giá trị.
- Bài Vault dev: policy chỉ đọc một path, token TTL ngắn. Kiểm bằng `vault_env`.
- ≥1 bài sự cố. Ví dụ:
  - drift do ai đó `kubectl edit` khi self-heal tắt;
  - sync kẹt vì hook lỗi;
  - Secret không giải mã được do sai recipient.
- Advanced:
  - thiết kế cấu trúc repo GitOps nhiều môi trường và quy trình promote (rubric);
  - postmortem một lần lộ secret (rubric).
- Không viết sẵn deliverable m07.

**Chấm bằng:** `KubeLab.gitops_repo`, `argocd_project`, `argocd_wait`, `sops_env`, `vault_env`.

- [ ] Quy trình module như Phase 2:
  1. test trước → starter → lời giải → đề;
  2. kiểm chứng ghim CPU;
  3. lý thuyết và interview;
  4. commit `DevOps: module 12-gitops-secrets`;
  5. tắt cluster.

### Task 4: Hạ tầng cho observability

**Files:**
- Modify: `tracks/devops/sample-app/olist_shop/` (trace OpenTelemetry), `tracks/devops/sample-app/requirements.txt`, `tracks/devops/sample-app/tests/`, `setup/kind/olist-shop.Dockerfile` (nếu requirements đổi, tag image lên `devops-track/olist-shop:1.1` và cập nhật mọi chỗ dùng tag)
- Modify: `testkit.py`, `tests/test_testkit_devops.py`, `CONTENT_SPEC.md`, `setup/DEVOPS-TOOLS.md`
- Create: `setup/observability/` (cấu hình mặc định ghim cho Prometheus, Grafana, Loki, OTel Collector, Jaeger; compose dùng qua `DockerLab.compose`)

**Interfaces:**
- **Produces (Olist Shop):**
  - Khi có biến `OTEL_EXPORTER_OTLP_ENDPOINT`, API và worker xuất trace OTLP (span cho request HTTP, query Postgres, job Redis). `trace_id` có trong log JSON, cạnh `request_id`.
  - Không có biến thì không xuất gì và không lỗi.
  - Dependency OTel ghim trong `requirements.txt` của sample-app. Không thêm vào `pyproject.toml` nếu không cần.
- **Produces `OBS_IMAGES: dict[str, str]`:** image ghim theo digest (prometheus, alertmanager, grafana, loki, otel-collector, jaeger).
- **Produces `ObsStack(lab: DockerLab, *, project: Path | None = None)`**, dựng bằng `DockerLab.compose`:
  - `.prom_query(expr) -> list`
  - `.loki_query(logql) -> list`
  - `.jaeger_traces(service) -> list`
  - `.grafana_dashboards() -> list`
  - `.alerts() -> list`
- **Produces `promtool(*args, cwd: Path)` và `amtool(*args, cwd: Path)`:** chạy qua `DockerLab.run_once` với image ghim, mount chỉ đọc.

- [ ] **Step 1:** Viết test thất bại:
  - sample-app: `test_trace_exported_when_endpoint_set`, `test_no_export_without_endpoint`, `test_log_has_trace_id`;
  - testkit: `test_obs_stack_loopback_and_cleanup`, `test_promtool_readonly_mount`.
- [ ] **Step 2:** Chạy → FAIL.
- [ ] **Step 3:** Cài đặt, rồi kiểm thật cả stack ghim CPU: một request có trace trong Jaeger, log trong Loki, metric trong Prometheus. Ghi RAM tổng.
- [ ] **Step 4:** Không còn tài nguyên `devops-ex-*`, kể cả volume. Commit `Olist Shop xuất trace OpenTelemetry; testkit: ObsStack, promtool, amtool`.

### Task 5: Module 13-observability

**Trọng tâm:**
- Ba trụ cột metrics, logs, traces, cộng profiles ở mức khái niệm.
- RED/USE, Four Golden Signals; infra monitoring và app monitoring.
- PromQL (rate, histogram_quantile, recording rule).
- Alerting: rule, `for`, Alertmanager route và inhibition, alert theo triệu chứng thay vì nguyên nhân.
- Grafana dashboard as code (provisioning).
- Loki/LogQL.
- OpenTelemetry: SDK, Collector, sampling.
- Jaeger.
- Log management: retention, chi phí, PII.
- Bảng so sánh ELK/OpenSearch, Graylog, Splunk, Papertrail, Datadog, New Relic, Zabbix.
- `## 0. Cài đặt`: image ghim, `promtool`/`amtool` qua container, `logcli` tuỳ chọn.

**Bài bắt buộc:**
- Recording và alerting rule cho Olist Shop, có unit test bằng `promtool test rules`. Test chạy `promtool` trên tệp của người học, và kiểm cả bằng dữ liệu thật trong `ObsStack`.
- Dashboard JSON được provision, kiểm panel và query trả dữ liệu.
- Pipeline OTel Collector: nhận OTLP, gắn attribute, xuất tới Jaeger và Prometheus. Kiểm trace có span DB.
- Truy một request từ log tới trace bằng `request_id`/`trace_id` (LogQL).
- ≥1 bài sự cố. Ví dụ:
  - alert không bao giờ bắn vì `rate` trên gauge hoặc sai label;
  - cardinality bùng nổ do label `user_id`;
  - trace đứt vì không truyền context qua Redis.
- Advanced:
  - thiết kế chiến lược alert và on-call cho Olist Shop (rubric);
  - postmortem một sự cố "alert im lặng" (rubric).
- Không chép bài MLOps module 09 (dashboard của MLOps). Không viết sẵn deliverable m08.

- [ ] Quy trình module → commit `DevOps: module 13-observability`.

### Task 6: Hạ tầng cho serverless: Lambda local và LocalStack mở rộng

**Files:**
- Modify: `testkit.py`, `tests/test_testkit_devops.py`, `CONTENT_SPEC.md`, `setup/docker-compose.yml` (`SERVICES` của `localstack-devops` thêm `sqs,dynamodb,events,apigateway,secretsmanager` khi cần; không mount socket Docker), `setup/DEVOPS-TOOLS.md`

**Interfaces:**
- **Produces `LambdaLab(lab: DockerLab, handler_dir: Path, handler: str, *, env: dict | None = None, memory: str = "256m")`:**
  - container từ image Lambda Python 3.12 ghim (`public.ecr.aws/lambda/python:3.12` theo digest, có RIE);
  - mount code chỉ đọc;
  - `.invoke(event: dict) -> dict` qua HTTP RIE trên `127.0.0.1`;
  - env ép:
    - `AWS_ENDPOINT_URL` = localstack-devops;
    - credential giả `test`/`test`;
    - `AWS_CONFIG_FILE=/dev/null`, `AWS_SHARED_CREDENTIALS_FILE=/dev/null`, `AWS_EC2_METADATA_DISABLED=true`;
  - không có socket Docker; network là network của lab, nối được localstack-devops.
- **Quyết định đã chốt:** không bật Lambda bên trong LocalStack, vì LocalStack cần socket Docker để chạy Lambda, tức là quyền root trên máy. Hạ tầng Lambda (function, IAM role, event source mapping) chỉ kiểm bằng `tofu plan` và trạng thái tài nguyên trên LocalStack. Code chạy trong `LambdaLab`.
- **Produces `localstack_client(service)`**, mở rộng cho các service mới.

- [ ] **Step 1:** Viết test thất bại:
  - `test_lambda_lab_no_socket_and_dummy_credentials`
  - `test_lambda_lab_endpoint_forced_to_localstack`
  - `test_lambda_lab_invoke_roundtrip`
  - `test_localstack_devops_no_docker_socket`
- [ ] **Step 2:** Cài đặt, kiểm thật một handler đọc SQS.
- [ ] **Step 3:** Commit `testkit: LambdaLab chạy handler bằng RIE, LocalStack DevOps thêm SQS, DynamoDB, EventBridge`.

### Task 7: Module 14-cloud-serverless

**Trọng tâm:**
- AWS core:
  - IAM: policy, role, trust, least privilege, permission boundary ở mức khái niệm;
  - VPC: subnet, route, NAT, SG và NACL;
  - EC2, S3, RDS.
  - Phần LocalStack bản miễn phí chỉ mock (RDS, EC2/VPC) thì dạy khái niệm, kèm bài AWS thật tuỳ chọn và bài local thay thế (Postgres container thay RDS).
- Lambda: cold start, concurrency, timeout, idempotency, DLQ.
- Event-driven với SQS, EventBridge.
- API Gateway.
- Shared responsibility model.
- Tối ưu chi phí cơ bản.
- Bảng so sánh Cloudflare Workers, Vercel/Netlify Functions, Azure/GCP Functions, và các nhà cung cấp AWS, Azure, GCP, DigitalOcean, Alibaba, Hetzner, Contabo, Heroku.
- `## 0. Cài đặt`: `awscli` qua `uv tool` hoặc dùng `localstack_client`, image Lambda.
- Lab AWS thật có hướng dẫn chi phí, budget alarm, lệnh dọn.

**Bài bắt buộc:**
- Policy IAM least privilege cho worker Olist Shop: tofu trên LocalStack, kiểm bằng IAM policy simulator của LocalStack nếu có. Nếu không có, kiểm tĩnh bằng parser policy viết trong test, và ghi rõ giới hạn.
- Lambda xử lý event SQS idempotent, có DLQ: code chạy trong `LambdaLab`, hạ tầng bằng tofu.
- Thiết kế VPC ba tầng bằng tofu: `plan` kiểm subnet, route, SG; không cần apply thật.
- ≥1 bài sự cố. Ví dụ:
  - Lambda timeout vì gọi tuần tự;
  - message xử lý hai lần do visibility timeout;
  - AccessDenied do trust policy.
- Advanced:
  - chọn nhà cung cấp và kiến trúc cho Olist Shop với ngân sách cho trước (rubric);
  - bài AWS thật tuỳ chọn.

- [ ] Quy trình module (dùng `TofuLab`, `LambdaLab`) → commit `DevOps: module 14-cloud-serverless`.

### Task 8: Hạ tầng cho service mesh: Linkerd

**Files:**
- Create: `setup/kind/linkerd/`: CRD và control plane ghim (bản edge có số hoặc stable của nhà phân phối mở, builder chọn và ghi rõ vì sao); script sinh trust anchor bằng `step` hoặc `openssl`, chạy tay theo hướng dẫn và ghi trong README module.
- Modify: `testkit.py`, `tests/test_testkit_devops.py`, `tests/test_devops_track.py`, `CONTENT_SPEC.md`, `setup/DEVOPS-TOOLS.md`

**Interfaces:**
- Admin cài một lần. `ex.require_linkerd()` skip kèm lệnh.
- **Produces `KubeLab(..., mesh: bool = False)`:** khi `True`, namespace có annotation `linkerd.io/inject: enabled`.
- **Quyền lab:** thêm ghi `httproutes.policy.linkerd.io`, `servers`, `authorizationpolicies`, `meshtlsauthentications` trong namespace lab. VAP buộc các object này chỉ tham chiếu namespace lab.
- **Produces `KubeLab.mesh_status(workload: str) -> dict`:** proxy injected, mTLS identity, số request thành công/thất bại. Đọc qua lệnh cố định của testkit bằng kubeconfig admin.

- [ ] **Step 1:** Viết test thất bại:
  - `test_kube_lab_mesh_annotation`
  - `test_linkerd_policy_foreign_namespace_refused`
  - `test_require_linkerd_messages`
- [ ] **Step 2:** Cài đặt, kiểm thật trên `devops-lab` ghim CPU: hai pod nói chuyện qua mTLS, `AuthorizationPolicy` chặn pod thứ ba. Ghi RAM thêm.
- [ ] **Step 3:** Tắt cluster. Commit `testkit: Linkerd trong devops-lab, KubeLab mesh, quyền policy Linkerd trong namespace lab`.

### Task 9: Module 15-service-mesh-patterns

**Trọng tâm:**
- Service mesh: data plane và control plane, sidecar và ambient (khái niệm), mTLS và identity, traffic split, retry, timeout, observability của mesh.
- Khi nào không cần mesh.
- Bảng so sánh Linkerd, Istio, Consul, Envoy/Cilium.
- Cloud design pattern theo bốn nhóm (spec): Availability, Data Management, Design & Implementation, Management & Monitoring. Mỗi pattern nêu dùng khi nào, đánh đổi, lỗi hay gặp, và ví dụ trên Olist Shop.
- `## 0. Cài đặt`: `linkerd` CLI và các bước admin.

**Bài bắt buộc:**
- Mesh hoá Olist Shop trong namespace lab: proxy injected, mTLS giữa API và worker, `AuthorizationPolicy` chỉ cho API gọi Redis.
- Retry và timeout bằng `HTTPRoute` của Linkerd, với backend lỗi ngẫu nhiên có seed. Kiểm tỉ lệ thành công.
- Pattern bằng code Python trong sandbox, không cần cluster:
  - circuit breaker và retry có backoff + jitter, cho client gọi API Olist Shop;
  - test bằng server giả bơm lỗi.
- ≥1 bài sự cố. Ví dụ:
  - retry storm làm sập backend;
  - pod không vào mesh vì thiếu annotation;
  - mTLS hỏng do lệch giờ hay trust anchor sai.
- Advanced:
  - chọn mesh hay không cho một tổ chức (rubric);
  - review kiến trúc theo pattern (rubric).

- [ ] Quy trình module → commit `DevOps: module 15-service-mesh-patterns`.

### Task 10: Module 16-sre-operations ★ (kèm helper bơm lỗi)

**Files:** module, cộng `testkit.py` và `tests/test_testkit_devops.py` cho helper bơm lỗi.

**Interfaces:**
- **Produces `FaultInjector(target: DockerLab | KubeLab, *, seed: int)`:**
  - chọn lỗi ngẫu nhiên theo seed từ tập cố định: kill container hay pod, thêm độ trễ mạng bằng `tc` trong container của lab có `NET_ADMIN` riêng cho container đó, đầy đĩa trong tmpfs của container, dừng Redis, sai config qua ConfigMap của lab;
  - chỉ chạm tài nguyên có nhãn của lab;
  - `.inject() -> str` trả mã lỗi, không trả mô tả;
  - `.revert()` gọi trong `close()`.

**Trọng tâm:**
- SLI/SLO/SLA, error budget và chính sách error budget, burn rate nhiều cửa sổ.
- On-call bền vững, incident command, postmortem blameless.
- Chaos engineering: giả thuyết, blast radius.
- Capacity planning: Little's law, load test bằng k6 qua `DockerLab`.
- FinOps: unit economics, rightsizing, cost allocation.
- Bảo mật pipeline cơ bản: SBOM, quét secret, ký image ở mức khái niệm, least privilege cho CI.
- Toil và tự động hoá.
- Chuẩn bị phỏng vấn DevOps/SRE: câu hỏi hệ thống, câu sự cố, câu hành vi.

**Bài bắt buộc:**
- SLO và burn-rate alert cho Olist Shop: tệp SLO, rule sinh ra kiểm bằng `promtool`, tính error budget từ dữ liệu cho sẵn.
- Load test bằng k6 tìm điểm gãy, rồi đề xuất capacity. Kiểm số liệu báo cáo khớp kết quả k6.
- Bài FinOps tính chi phí và rightsizing từ dữ liệu usage cho sẵn.
- Bài game day nhỏ:
  - `FaultInjector` bơm một lỗi;
  - người học chẩn đoán bằng `ObsStack` và khôi phục;
  - test kiểm hệ thống khôi phục và runbook có đủ mục;
  - postmortem chấm rubric.
- Advanced:
  - chính sách error budget và quy trình on-call (rubric);
  - quiz phỏng vấn.

- [ ] **Step 1:** Viết test thất bại cho helper bơm lỗi, gồm `test_fault_injector_only_touches_lab_resources`, `test_fault_injector_seed_deterministic`, `test_fault_injector_reverts_on_close`. Cài đặt helper.
- [ ] **Step 2:** Quy trình module → commit `DevOps: module 16-sre-operations`.

### Task 11: Capstone m07–m09

**Files:**
- Create: `tracks/devops/capstone/milestones/` theo đúng tên tệp đã khai báo trong `track.json` cho m07–m09
- Create: `capstone/project/tests/test_m07.py`, `test_m08.py`, `test_m09.py`
- Create: lời giải trong `capstone/solutions/project/`
- Modify: `SOLUTION.md`, capstone README

**Interfaces:**
- **m07:**
  - repo GitOps của Olist Shop dùng chart m06, ArgoCD sync vào namespace lab;
  - Secret DB mã hoá bằng SOPS, không có giá trị rõ trong repo;
  - đổi version trong git thì ArgoCD rollout; `git revert` thì quay lại.
  - Chấm bằng `KubeLab.gitops_repo`, `argocd_wait`.
- **m08:**
  - stack m03 cộng observability;
  - metric RED của API và worker, log có `trace_id` vào Loki, trace có span DB trong Jaeger;
  - dashboard provision;
  - alert rule kèm `promtool test`;
  - một alert bắn thật khi dừng worker.
  - Chấm bằng `DockerLab.compose`, `ObsStack`, `promtool`.
- **m09** (đánh giá độc lập, spec mục 9):
  - test chỉ kiểm phần chấm được: tệp SLO và burn-rate rule pass `promtool`, runbook đủ mục, và hệ thống khôi phục sau `FaultInjector` với seed do người học không biết trước (seed lấy từ thời gian chạy, in ra sau khi xong);
  - game day và postmortem tự đánh giá theo rubric trong milestone;
  - tuỳ chọn deploy lên AWS thật kèm hướng dẫn chi phí.

- [ ] Viết test m07–m09 trước (fail hoặc skip, không error).
- [ ] Viết milestone docs và lời giải.
- [ ] `SOLUTION=1` pass (cluster và stack bật khi kiểm, tắt sau).
- [ ] Validator xanh.
- [ ] Commit `DevOps: capstone m07–m09`.

### Task 12: Hoàn thiện track, kiểm toàn nhánh và PR

- [ ] **README:**
  - README gốc: bảng track ghi DevOps đủ 17 module và 9 milestone, bỏ trạng thái dở dang nếu có.
  - `tracks/devops/README.md`: sơ đồ và bảng module, milestone đủ.
  - `setup/DEVOPS-TOOLS.md`: mục lục đủ 17 module.
- [ ] **Validator:**
  - `tests/test_devops_track.py` kiểm đủ 17 module và 9 milestone theo quy mô ở Global Constraints;
  - tổng số bài khoảng 120 (spec mục 3), báo con số thật.
- [ ] **Chạy kiểm:**
  - `uv run pytest tests -q`;
  - `SOLUTION=1 nice -n 15 taskset -c 12-35 uv run pytest tracks/devops -q -rs`, bật đủ dịch vụ và cluster khi cần → chỉ còn skip đúng thiết kế; liệt kê trong PR.
- [ ] **Dọn:**
  - không còn container, image tạm, network hay volume `devops-ex-*`, kể cả volume ẩn danh;
  - tắt cluster và stack;
  - không đụng tài nguyên của người dùng hay track khác.
- [ ] **Review và bàn giao:**
  - review toàn nhánh bằng model mạnh nhất, rồi một đợt sửa;
  - cập nhật `docs/superpowers/handoff-devops.md` thành tổng kết track (không còn phase sau);
  - push nhánh, mở PR, đưa người dùng link.
