# Thiết kế: track DevOps

Ngày: 2026-11-01. Nguồn: [roadmap.sh/devops](https://roadmap.sh/devops) (bản PDF ở `roadmap/devops.pdf`).
Đối chiếu thêm: CKA curriculum v1.37, Terraform Associate 004, roadmap.sh/kubernetes và
roadmap.sh/terraform, OpenTofu 1.13. Checklist đầy đủ có trích nguồn ở
[research/2026-11-01-k8s-terraform-topic-checklists.md](../research/2026-11-01-k8s-terraform-topic-checklists.md).

## 1. Mục đích và lý do

Người học muốn **làm được việc của DevOps engineer ở mức senior** và đi phỏng vấn được ("thừa hơn
thiếu"), không dừng ở mức junior của roadmap.sh.

Người học đã xong track `data-engineer`. Module DE `08-devops-for-data` (Docker, K8s, CI/CD, Terraform,
monitoring) và `11-cloud` (IAM, VPC, LocalStack, FinOps) dạy ở mức "đủ dùng cho data". Vì vậy:

- **Phần trùng chỉ nhắc lại ngắn** rồi trỏ về module gốc, trừ **Kubernetes và IaC**: hai phần này
  DE dạy quá mỏng (K8s khoảng 90 dòng, Terraform khoảng 180 dòng), nên track này **dạy lại đầy đủ**,
  tới mức gần CKA và Terraform Associate 004.
- **Bài tập phải khác bài của track DE** dù kiến thức giống. Bài đặt trong bối cảnh công việc DevOps:
  vận hành dịch vụ, tự động hoá, deploy, xử lý sự cố.

Người học đọc tiếng Việt, giữ thuật ngữ tiếng Anh. Máy Linux, đã có Docker, uv, Node.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Lấp placeholder `tracks/devops` thành track `active` đúng `CONTENT_SPEC.md`.
- Phủ mọi mục trong PDF roadmap, cộng các phần một DevOps/SRE senior cần mà roadmap thiếu (★ ở mục 4).
- Kubernetes phủ checklist CKA v1.37 (kèm phần CKAD hữu ích). IaC phủ checklist Terraform Associate 004
  và roadmap.sh/terraform.
- Mỗi nhóm công cụ: **một công cụ để thực hành**, các công cụ còn lại trong **bảng so sánh** (dùng khi
  nào, mạnh gì, yếu gì, loại công ty hay dùng). Có bài "chọn công cụ" theo tình huống.
- Dạng bài **sự cố cố ý** (mục 5) xuyên suốt từ module 05 trở đi.

**Ngoài phạm vi**
- Linux chuyên sâu, DevSecOps chuyên sâu, MLOps: để cho track riêng sau này (đã có PDF trong `roadmap/`).
  Track này chỉ có phần bảo mật pipeline ở mức cơ bản.
- Windows/PowerShell, BSD, Go, Ruby, Rust, Node: chỉ giới thiệu và so sánh, không có bài bắt buộc.
- HCP Terraform / Terraform Cloud: chỉ dạy khái niệm.
- Script cài công cụ tự động: **không làm** (mục 6).

**Điều cấm (làm vậy là hỏng dù chạy được)**
- Bài tập chép lại hoặc đổi tên bài của track DE.
- Nội dung chỉ dừng ở định nghĩa, không có quyết định thực tế (khi nào dùng, đánh đổi, lỗi hay gặp).
- Test không kiểm được đúng/sai thật (chỉ grep chuỗi trong file mà không chạy công cụ khi chạy được),
  hoặc test phụ thuộc mạng, cloud thật, cluster đang chạy, công cụ chưa cài mà không tự skip.
- Bài nào **bắt buộc** cloud thật hay tốn tiền mới qua được.
- Hướng dẫn cài bằng `curl | sudo bash` hay bỏ qua kiểm checksum.
- Chạy việc nặng (cluster, VM, build image lớn) không có `nice` và không ghim core 12–35 (cores 0–11 để
  người dùng làm việc). Chạy lệnh phá huỷ trên cổng mặc định 5432/6379/9000/9001.
- Phá vỡ track DE, DS, DA hoặc app hiện có.

## 3. Ràng buộc

- Cấu trúc thư mục, frontmatter bài tập, interview, capstone, quiz: đúng `CONTENT_SPEC.md`. App đã nhận
  starter không phải `.py` (Dockerfile, YAML…) như DE module 08, nên **không dự kiến sửa app**.
- Mỗi module: 5–8 phần lý thuyết (`## `), ≥2 sơ đồ mermaid, phần cuối là tài liệu tham khảo (link trong
  PDF roadmap làm gốc, cộng docs chính thức). Phần nhắc lại kiến thức trùng track DE chỉ chiếm một phần
  `## `, có link tới module gốc.
- `interview.md` ≥12 câu, có câu tình huống sự cố, câu "vì sao chọn công cụ này", câu thiết kế hệ thống.
- Khoảng 7 bài mỗi module (3 Basic, 2–3 Intermediate, 2 Advanced); module 08 (IaC) khoảng 8 bài. Tổng
  khoảng **120 bài**. Starter chạy test phải fail hoặc skip, không lỗi cú pháp. `SOLUTION=1` pass với
  Basic và Intermediate. Advanced chỉ có `SOLUTION.md` (hướng làm + rubric).
- Python 3.12, `uv`. Bash là ngôn ngữ script chính. Dịch vụ Docker mới thêm vào `setup/docker-compose.yml`
  dưới profile riêng; cổng trùng thì remap qua `setup/.env`.
- Code không có comment inline (quy ước của người dùng); docstring đầu hàm chỉ khi thật cần.
- **Cloud**: ưu tiên local (LocalStack, MinIO, kind). Khi bài cần trải nghiệm thật, có **hướng dẫn dùng
  AWS free tier**: chi phí ước tính, bật budget alarm, lệnh dọn (`tofu destroy`), và bài tương đương chạy
  local. Test không bao giờ bắt buộc cloud.

## 4. Danh sách module (đã chốt)

| # | id | Module | Nội dung chính |
| --- | --- | --- | --- |
| 00 | `00-introduction` ★ | Giới thiệu DevOps & SRE | Văn hoá CALMS, DORA metrics, DevOps vs SRE vs Platform Engineering; vai trò; **bản đồ công cụ** toàn roadmap |
| 01 | `01-linux-terminal` | Linux & terminal | OS (Ubuntu/Debian, RHEL, SUSE; Unix/BSD, Windows giới thiệu); process monitoring, performance monitoring, networking tools, text manipulation; Vim/Nano/Emacs; systemd, quyền, package; **bài cài binary đúng cách** (Q25) |
| 02 | `02-scripting` | Scripting & lập trình | Bash (trọng tâm: strict mode, trap, idempotent, test bằng bats hoặc pytest), Python cho automation; Go/Node/Ruby/Rust/PowerShell so sánh |
| 03 | `03-git-vcs-hosting` | Git & VCS hosting | Nhắc lại từ DE; branching strategy, trunk-based, PR flow, hooks, monorepo; GitHub/GitLab/Bitbucket so sánh |
| 04 | `04-networking-protocols` | Networking & protocols | OSI, DNS, HTTP/HTTPS, SSL/TLS, SSH, FTP/SFTP; email: SMTP, IMAP, POP3S, SPF, DKIM, DMARC, white/grey listing (lab Mailpit + bài phân tích bản ghi offline) |
| 05 | `05-web-server-proxy` | Web server & proxy | Nginx; forward/reverse proxy, caching server, load balancer, firewall; Caddy/Apache/Tomcat/IIS so sánh |
| 06 | `06-containers` | Containers | Docker chuyên sâu (layer, multi-stage, hardening, rootless, registry, quét lỗ hổng), LXC/LXD |
| 07 | `07-cicd-artifacts` | CI/CD & artifact | GitHub Actions + `act`; thiết kế pipeline, chiến lược deploy, artifact management (registry local); Jenkins/GitLab CI/CircleCI/TeamCity/Octopus, Artifactory/Nexus/Cloudsmith so sánh |
| 08 | `08-iac-provisioning` | Provisioning (IaC) | OpenTofu + LocalStack, **dạy đầy đủ** theo checklist Terraform Associate 004: HCL, provider, meta-arguments, variables/outputs/conditions, state (remote, locking, import, moved, drift), module, workspaces, test, lint/policy; **ghi rõ mọi chỗ khác Terraform** (state encryption…); CDK/CloudFormation/Pulumi so sánh |
| 09 | `09-config-management` | Configuration management | Ansible (inventory, role, idempotency, vault, molecule); Chef/Puppet so sánh |
| 10 | `10-kubernetes-core` | Kubernetes core | Kiến trúc (control plane, etcd, kubelet, CRI/CNI/CSI); workload (Pod, multi-container, Deployment, StatefulSet, DaemonSet, Job); Service, Ingress, Gateway API, CoreDNS; ConfigMap/Secret, probes; storage (PV/PVC, StorageClass); etcd backup/restore trên kind; **lab kubeadm tuỳ chọn** (Q22) |
| 11 | `11-kubernetes-production` | Kubernetes production | RBAC, ServiceAccount, SecurityContext, Pod Security, NetworkPolicy; scheduling (affinity, taint, topology spread, priority); quota/LimitRange; HPA/VPA/cluster autoscaler, PDB; Helm chart tự viết, Kustomize; CRD/Operator; troubleshooting có hệ thống; upgrade; managed (EKS/GKE/AKS), ECS/Fargate, Swarm so sánh |
| 12 | `12-gitops-secrets` | GitOps & secrets | ArgoCD (FluxCD so sánh); SOPS, Vault dev, Sealed Secrets, công cụ secret của cloud |
| 13 | `13-observability` | Observability | Prometheus, Grafana, Loki, OpenTelemetry, Jaeger; alerting; infra vs app monitoring, logs management; ELK/Graylog/Splunk/Papertrail/Datadog/New Relic/Zabbix so sánh |
| 14 | `14-cloud-serverless` | Cloud & serverless | AWS core (IAM, VPC, EC2, S3, RDS) qua LocalStack + lab AWS thật có hướng dẫn; Lambda; Cloudflare/Vercel/Netlify/Azure/GCP Functions; so sánh nhà cung cấp (AWS, Azure, GCP, DO, Alibaba, Hetzner, Contabo, Heroku) |
| 15 | `15-service-mesh-patterns` | Service mesh & cloud design patterns | Linkerd lab nhẹ (Istio/Consul/Envoy so sánh); pattern Availability, Data Management, Design & Implementation, Management & Monitoring |
| 16 | `16-sre-operations` ★ | SRE & vận hành | SLO/SLI, error budget, on-call, incident và postmortem, chaos, capacity planning, FinOps, bảo mật pipeline cơ bản; chuẩn bị phỏng vấn |

Topic con và tên bài: builder quyết, miễn phủ đủ các mục trên và checklist research cho module 08, 10, 11.

## 5. Dạng bài và cách chấm (đã chốt)

`pytest` là bộ chấm duy nhất. Test **gọi công cụ thật** (docker, kind, kubectl, helm, tofu, ansible, act,
nginx trong container…) khi được, và **tự skip** khi máy thiếu công cụ hoặc thiếu cluster.

- **Bài file cấu hình / script**: starter là Dockerfile, YAML, `.tf`, playbook, `.sh`, `nginx.conf`… có TODO.
  Test chạy thật: build image, `tofu validate/plan/apply` trên LocalStack, `kubectl apply --dry-run=server`
  hoặc apply lên cluster, `ansible-playbook --check`, `act`, `nginx -t` rồi gọi HTTP.
- **Bài sự cố cố ý**: bài dựng môi trường hỏng (container crash, Nginx sai config, pod CrashLoopBackOff,
  cert hết hạn, DNS sai…). Người học chẩn đoán và sửa, test kiểm hệ thống chạy lại. Module 05 trở đi có
  ít nhất 1 bài. Bản Advanced thêm postmortem chấm bằng rubric.
- **Bài "cài và xác minh"** (1–2 bài, module 01): test kiểm công cụ có trong PATH, phiên bản ≥ mức tối
  thiểu, có tệp `.sha256` đã kiểm, không cài bằng `curl | sudo bash`.
- **Bài "chọn công cụ"**: quiz theo tình huống (`kind: knowledge`), giải thích trong `SOLUTION.md`.
- **Bài email offline**: phân tích bản ghi SPF/DKIM/DMARC và header thư từ dữ liệu cho sẵn, không cần mạng.
- **Advanced**: thiết kế, runbook, postmortem, review kiến trúc; rubric trong `SOLUTION.md`.

**Testkit**: thêm helper `ex.require_tool("<tên>", min_version=...)` (skip kèm lời nhắc trỏ tới phần cài
đặt) và `ex.require_cluster("devops-lab")` (skip nếu cluster kind chưa bật). Có test cho helper mới.

## 6. Công cụ và môi trường (đã chốt)

- **Không có script cài sẵn.** Người học tự cài từng bước. Mỗi module có phần `## 0. Cài đặt` cho công cụ
  dùng lần đầu ở module đó: bảng phiên bản đã kiểm, lệnh tải, kiểm checksum, cài vào `~/.local/bin` (không
  sudo nếu được), lệnh xác nhận, cách gỡ. `setup/DEVOPS-TOOLS.md` là mục lục trỏ tới các phần đó. Ansible
  cài qua `uv`.
- **Bộ công cụ thực hành**: Bash + Python; Nginx; Docker; GitHub Actions + `act`; registry local; OpenTofu
  + LocalStack; Ansible; kind + kubectl + Helm + Kustomize; ArgoCD; SOPS + Vault dev; Prometheus + Grafana
  + Loki + OpenTelemetry + Jaeger; Mailpit; Linkerd; trivy để quét image. Phiên bản cụ thể: builder chọn
  bản ổn định mới nhất và ghi vào bảng.
- **Cluster kind dùng chung `devops-lab`**: người học tạo theo hướng dẫn, chạy với `nice -n 15` và
  `taskset -c 12-35`. Hướng dẫn nhắc tắt cluster khi xong. Test cần cluster skip nếu chưa bật.
- **Lab kubeadm (tuỳ chọn, module 10)**: 1 control plane + 2 worker trên VM nhẹ (Multipass hoặc LXD),
  ghim core 12–35; phủ cài cluster, upgrade, HA control plane ở mức khái niệm/lab. Test tự skip.

## 7. Ứng dụng mẫu và capstone (đã chốt)

**Olist Shop** ở `tracks/devops/sample-app/`: viết một lần, nhỏ, có test. Gồm API (FastAPI) + worker +
Postgres + Redis, chạy trên dữ liệu Olist sẵn có (`data/download_olist.py`, dự phòng
`data/generate_olist.py`). Có `/healthz`, `/metrics` và log có cấu trúc để các module sau dùng. Bài tập và
capstone vận hành ứng dụng này; người học không phải viết code ứng dụng.

Capstone: đưa Olist Shop lên "production" local.

| M | Sau module | Nội dung |
| --- | --- | --- |
| m01 | 02 | Script vận hành: bootstrap, healthcheck, backup bằng Bash, có test |
| m02 | 05 | Nginx phía trước: reverse proxy, TLS tự ký, rate limit |
| m03 | 06 | Container hoá mọi service, image tối ưu và đã quét lỗ hổng |
| m04 | 07 | Pipeline CI/CD: test, build, push registry local, deploy staging |
| m05 | 09 | Hạ tầng bằng OpenTofu (LocalStack) + cấu hình bằng Ansible |
| m06 | 11 | Lên kind bằng Helm chart tự viết, HPA, NetworkPolicy, RBAC |
| m07 | 12 | GitOps bằng ArgoCD, secret bằng SOPS |
| m08 | 13 | Observability đủ metrics, logs, traces; dashboard và alert |
| m09 | 16 | **Đánh giá độc lập**: SLO, game day với sự cố bơm vào, khôi phục và postmortem; tuỳ chọn deploy lên AWS thật |

## 8. Cách giao (đã chốt)

Làm trong worktree `../Learning_Platform-devops`, nhánh `devops-track` (session DA giữ thư mục `main`).
Ba phase, mỗi phase một PR:

1. **Phase 1**: `track.json` (status `active`, `source` trỏ roadmap, giữ `order: 5`, icon `container`),
   `README.md` của track với sơ đồ mermaid, capstone README, `sample-app`, helper testkit, `setup/DEVOPS-TOOLS.md`,
   module 00–05, milestone m01–m02.
2. **Phase 2**: module 06–11, milestone m03–m06.
3. **Phase 3**: module 12–16, milestone m07–m09. Cập nhật README gốc của repo (bảng track).

- **Kiểm chứng khi xây (đã chốt)**: builder được cài công cụ vào `~/.local/bin` (user space, kiểm checksum,
  đúng các bước trong hướng dẫn của khoá, nhờ đó kiểm luôn hướng dẫn) và chạy việc nặng để chứng minh
  `SOLUTION=1` pass và starter fail. Việc nặng ghim core 12–35 + `nice`, mỗi lúc một job nặng, tắt
  cluster/stack sau mỗi đợt kiểm. Test skip không được tính là pass.

## 9. Quyết định của người viết spec (người học xem lại)

- **LocalStack**: không đụng service `localstack` dùng chung (DE phụ thuộc, pin `4.4.0`). DevOps chạy
  instance riêng dưới profile compose `devops`, cổng remap qua `setup/.env`, bật thêm service cần cho
  module 08 và 14. Thứ LocalStack bản miễn phí không làm thật được (RDS, EC2/VPC chỉ mock): dạy khái niệm,
  có hướng dẫn AWS thật, và bài local thay thế (vd. Postgres container thay RDS). Đúng tinh thần Q4.
- **Ghim CPU cho container**: `nice`/`taskset` trên lệnh không giới hạn được container trong dockerd. Mọi
  service compose mới có `cpuset: "12-35"`; node kind ghim bằng `docker update --cpuset-cpus 12-35` ngay
  sau khi tạo cluster (có trong hướng dẫn); `act` chạy với `--container-options "--cpuset-cpus=12-35"`;
  `docker build` dùng `--cpuset-cpus 12-35`.
- **Capstone chấm thế nào**: theo cách track DE: milestone là markdown có checklist, code ở
  `capstone/project/` kèm test pytest cho phần chấm được (m01–m08); m09 tự đánh giá theo rubric.
- **Sự cố ở m09 và bài sự cố cố ý**: script bơm lỗi chọn ngẫu nhiên từ một tập lỗi theo seed lúc chạy;
  người học không đọc script trước game day (tự giác, như DE m12). Bài sự cố trong module: nguyên nhân
  nằm trong `solutions/`, đề chỉ mô tả triệu chứng.
- **PR**: mỗi phase một PR từ `devops-track` vào `main`; người học merge. Phase sau làm tiếp trên nhánh
  sau khi phase trước merge (rebase lên `main` nếu cần). Phần dùng chung (`testkit.py`, `setup/`,
  `pyproject.toml`) sửa tối thiểu, có test, để không đụng session khác.

## 10. Để builder quyết

Tên và nội dung cụ thể từng bài; phiên bản cụ thể của công cụ; dùng bats hay pytest để test script Bash;
Multipass hay LXD cho lab kubeadm; cấu trúc nội bộ của sample-app; dịch vụ nào chạy bằng compose, dịch vụ
nào chạy trong kind; thứ tự soạn module trong mỗi phase.
