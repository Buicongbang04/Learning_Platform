# Checklist chủ đề Kubernetes và Terraform/OpenTofu từ nguồn gốc

Ngày tra cứu: 2026-11-01. Mục đích: đối chiếu track DevOps tiếng Việt, để không bỏ sót chủ đề Kubernetes (mức CKA trở lên) và Terraform/OpenTofu (mức senior).

Quy ước:
- Nguồn nào không truy cập được thì ghi rõ. Nội dung lấy từ trí nhớ thì gắn nhãn "(chưa kiểm nguồn)".
- Nhãn nguồn dùng trong phần Gộp: `[CKA]`, `[CKAD]`, `[RM-K8s]` (roadmap.sh/kubernetes), `[TA004]` (Terraform Associate 004), `[RM-TF]` (roadmap.sh/terraform), `[OTF]` (tài liệu và blog OpenTofu).

---

## 1. CKA: Certified Kubernetes Administrator, curriculum v1.37

- Repo: https://github.com/cncf/curriculum. README ghi: "This is the latest version of the curriculum…". Major.minor của tài liệu trùng với phiên bản Kubernetes.
- File: https://github.com/cncf/curriculum/blob/master/CKA_Curriculum_v1.37.pdf (commit "Add CKA_Curriculum_v1.37.pdf and cleanup", ngày 2026-10-15). Nội dung trích bằng `pdftotext` từ bản PDF đã tải về.
- Trong repo còn có `CKAD_Curriculum_v1.37.pdf` và `CKS_Curriculum v1.34.pdf`. Các bản cũ nằm trong thư mục `old-versions/`.

### 25% Cluster Architecture, Installation and Configuration
- [ ] Manage role based access control (RBAC)
- [ ] Prepare underlying infrastructure for installing a Kubernetes cluster
- [ ] Create and manage Kubernetes clusters using kubeadm
- [ ] Manage the lifecycle of Kubernetes clusters
- [ ] Implement and configure a highly-available control plane
- [ ] Use Helm and Kustomize to install cluster components
- [ ] Understand extension interfaces (CNI, CSI, CRI, etc.)
- [ ] Understand CRDs, install and configure operators

### 15% Workloads and Scheduling
- [ ] Understand application deployments and how to perform rolling update and rollbacks
- [ ] Use ConfigMaps and Secrets to configure applications
- [ ] Configure workload autoscaling
- [ ] Understand the primitives used to create robust, self-healing, application deployments
- [ ] Configure Pod admission and scheduling (limits, node affinity, etc.)

### 20% Servicing and Networking (PDF ghi đúng chữ "Servicing")
- [ ] Understand connectivity between Pods
- [ ] Define and enforce Network Policies
- [ ] Use ClusterIP, NodePort, LoadBalancer service types and endpoints
- [ ] Use the Gateway API to manage Ingress traffic
- [ ] Know how to use Ingress controllers and Ingress resources
- [ ] Understand and use CoreDNS

### 10% Storage
- [ ] Implement storage classes and dynamic volume provisioning
- [ ] Configure volume types, access modes and reclaim policies
- [ ] Manage persistent volumes and persistent volume claims

### 30% Troubleshooting
- [ ] Troubleshoot clusters and nodes
- [ ] Troubleshoot cluster components
- [ ] Monitor cluster and application resource usage
- [ ] Manage and evaluate container output streams
- [ ] Troubleshoot services and networking

Nhận xét: so với các bản cũ, các mục Gateway API, Helm/Kustomize, CRD/operators, HA control plane và workload autoscaling là phần mới thêm. Những mục này trùng với bản đã sửa đổi năm 2025 (chưa kiểm nguồn về mốc thời gian, vì chưa đối chiếu với `old-versions/`).

## 2. CKAD v1.37: các mục nên bổ sung cho track

- File: https://github.com/cncf/curriculum/blob/master/CKAD_Curriculum_v1.37.pdf (commit "Update CKAD to v1.37 + Add CKNE", ngày 2026-10-01).

Danh sách đầy đủ, mục nào không có trong CKA thì gắn ★:

**20% Application Design and Build**
- [ ] ★ Define, build and modify container images
- [ ] Choose and use the right workload resource (Deployment, DaemonSet, CronJob, etc.)
- [ ] ★ Understand multi-container Pod design patterns (e.g. sidecar, init and others)
- [ ] ★ Utilize persistent and ephemeral volumes (phần ephemeral volumes)

**20% Application Deployment**
- [ ] ★ Use Kubernetes primitives to implement common deployment strategies (e.g. blue/green or canary)
- [ ] Understand Deployments and how to perform rolling updates
- [ ] Use the Helm package manager to deploy existing packages
- [ ] Kustomize

**15% Application Observability and Maintenance**
- [ ] ★ Understand API deprecations (PDF viết sai thành "depreciations")
- [ ] ★ Implement probes and health checks
- [ ] Use built-in CLI tools to monitor Kubernetes applications
- [ ] Utilize container logs
- [ ] Debugging in Kubernetes

**25% Application Environment, Configuration and Security**
- [ ] Discover and use resources that extend Kubernetes (CRD, Operators)
- [ ] ★ Understand authentication, authorization and admission control
- [ ] ★ Understand requests, limits, quotas (ResourceQuota, LimitRange)
- [ ] Define resource requirements
- [ ] Understand ConfigMaps
- [ ] Create & consume Secrets
- [ ] ★ Understand ServiceAccounts
- [ ] ★ Understand Application Security (SecurityContexts, Capabilities, etc.)

**20% Services and Networking**
- [ ] Demonstrate basic understanding of NetworkPolicies
- [ ] Provide and troubleshoot access to applications via services
- [ ] Use Ingress rules to expose applications

## 3. roadmap.sh/kubernetes

- Trang: https://roadmap.sh/kubernetes. Trang HTML không có danh sách chủ đề vì nội dung được render bằng JS.
- Dữ liệu gốc lấy từ JSON chính thức của roadmap.sh: https://roadmap.sh/api/v1-official-roadmap/kubernetes (`updatedAt` 2026-10-27).
- Repo `kamranahmedse/developer-roadmap` đã đổi tên thành **`nilbuild/developer-roadmap`**: GitHub API redirect repository id 85077558 sang tên mới. Nội dung nằm ở `roadmaps/kubernetes/content/` (commit gần nhất 2026-10-02): https://github.com/nilbuild/developer-roadmap/tree/master/roadmaps/kubernetes/content. Đường dẫn cũ `src/data/roadmaps/...` trả về 404.
- Cách nhóm: lấy theo cạnh (edges) trong JSON. Với các node không có cạnh, nhóm theo vị trí trên sơ đồ. Đây là suy luận từ bố cục, nhưng khớp rõ ràng với cách trang vẽ.

**Introduction**
- [ ] Overview of Kubernetes
- [ ] Why use Kubernetes?
- [ ] Key Concepts and Terminologies
- [ ] Kubernetes Alternatives

**Containers** (topic không có subtopic)
- [ ] Containers

**Setting up Kubernetes**
- [ ] Deploying your First Application
- [ ] Choosing a Managed Provider
- [ ] Installing a Local Cluster

**Running Applications**
- [ ] Pods
- [ ] ReplicaSets
- [ ] Deployments
- [ ] StatefulSets
- [ ] Jobs

**Configuration Management**
- [ ] Injecting Pod Config with ConfigMaps
- [ ] Using Secrets for Sensitive Data

**Services and Networking**
- [ ] Gateway API
- [ ] External Access to Services
- [ ] Load Balancing
- [ ] Networking & Pod-to-Pod Communication

**Security**
- [ ] Role Based Access Control (RBAC)
- [ ] Network Security
- [ ] Container and Pod Security

**Resource Management**
- [ ] Setting Resource Requests and Limits
- [ ] Assigning Quotas to Namespaces
- [ ] Monitoring & Optimizing Resource Usage

**Monitoring and Logging**
- [ ] Logs
- [ ] Metrics
- [ ] Traces
- [ ] Resource Health
- [ ] Observability Engines

**Storage and Volumes**
- [ ] CSI Drivers
- [ ] Stateful Applications

**Scheduling**
- [ ] Basics
- [ ] Taints and Tolerations
- [ ] Topology Spread Constraints
- [ ] Pod Priorities
- [ ] Evictions

**Autoscaling**
- [ ] Horizontal Pod Autoscaler (HPA)
- [ ] Vertical Pod Autoscaler (VPA)
- [ ] Cluster Autoscaling

**Deployment Patterns**
- [ ] CI / CD Integration
- [ ] GitOps
- [ ] Helm Charts
- [ ] Canary Deployments
- [ ] Blue-Green Deployments
- [ ] Rolling Updates / Rollbacks

**Cluster Operations**
- [ ] Should you manage your own Cluster?
- [ ] Installing the Control Plane
- [ ] Adding and Managing Worker Nodes
- [ ] Multi-Cluster Management

**Advanced Topics**
- [ ] Creating Custom Controllers
- [ ] Custom Schedulers and Extenders
- [ ] Custom Resource Definitions (CRDs)
- [ ] Kubernetes Extensions and APIs

---

## 4. HashiCorp Terraform Associate (004)

- Phiên bản hiện hành: **004**. Trang ôn tập ghi "Tests on Terraform version 1.12": https://developer.hashicorp.com/terraform/tutorials/certification-004/associate-review-004. Trang chứng chỉ ghi "Product version tested: Terraform 1.12", định dạng thi multiple-choice trong 1 giờ: https://developer.hashicorp.com/certifications/infrastructure-automation
- Bản 003 đã nghỉ hưu. Ngày 8/1/2026 là ngày đầu tiên thi được 004, còn 7/1/2026 là ngày cuối thi được 003. Mốc này lấy từ snippet tìm kiếm trỏ tới trang certifications của HashiCorp. Bản trang hiện tại không còn hiện các mốc đó, nên chỉ kiểm được gián tiếp.
- Theo trang review, 004 thêm 4 objective so với 003: 4f, 4g, 4h và 8c.

**1. Infrastructure as Code (IaC) with Terraform**
- [ ] 1a Explain what IaC is
- [ ] 1b Describe the advantages of IaC patterns
- [ ] 1c Explain how Terraform manages multi-cloud, hybrid cloud, and service-agnostic workflows

**2. Terraform fundamentals**
- [ ] 2a Install and version Terraform providers
- [ ] 2b Describe how Terraform uses providers
- [ ] 2c Write Terraform configuration using multiple providers
- [ ] 2d Explain how Terraform uses and manages state

**3. Core Terraform workflow**
- [ ] 3a Describe the Terraform workflow
- [ ] 3b Initialize a Terraform working directory
- [ ] 3c Validate a Terraform configuration
- [ ] 3d Generate and review an execution plan for Terraform
- [ ] 3e Apply changes to infrastructure with Terraform
- [ ] 3f Destroy Terraform-managed infrastructure
- [ ] 3g Apply formatting and style adjustments to a configuration

**4. Terraform configuration**
- [ ] 4a Use and differentiate `resource` and `data` blocks
- [ ] 4b Refer to resource attributes and create cross-resource references
- [ ] 4c Use variables and outputs
- [ ] 4d Understand and use complex types
- [ ] 4e Write dynamic configuration using expressions and functions
- [ ] 4f Define resource dependencies in configuration (mới ở 004)
- [ ] 4g Validate configuration using custom conditions (mới ở 004)
- [ ] 4h Understand best practices for managing sensitive data, including secrets management with Vault (mới ở 004)

**5. Terraform modules**
- [ ] 5a Explain how Terraform sources modules
- [ ] 5b Describe variable scope within modules
- [ ] 5c Use modules in configuration
- [ ] 5d Manage module versions

**6. Terraform state management**
- [ ] 6a Describe the local backend
- [ ] 6b Describe state locking
- [ ] 6c Configure remote state using the backend block
- [ ] 6d Manage resource drift and Terraform state

**7. Maintain infrastructure with Terraform**
- [ ] 7a Import existing infrastructure into your Terraform workspace
- [ ] 7b Use the CLI to inspect state
- [ ] 7c Describe when and how to use verbose logging

**8. HCP Terraform**
- [ ] 8a Use HCP Terraform to create infrastructure
- [ ] 8b Describe HCP Terraform collaboration and governance features
- [ ] 8c Describe how to organize and use HCP Terraform workspaces and projects (mới ở 004)
- [ ] 8d Configure and use HCP Terraform integration

Trang review không công bố trọng số theo domain.

## 5. roadmap.sh/terraform

- Trang: https://roadmap.sh/terraform. JSON chính thức: https://roadmap.sh/api/v1-official-roadmap/terraform (`updatedAt` 2026-10-27). Nội dung trong repo: https://github.com/nilbuild/developer-roadmap/tree/master/roadmaps/terraform/content (commit 2026-10-02).
- Cách nhóm giống roadmap K8s: theo edges, cộng với vị trí trên sơ đồ cho các node không có cạnh. Riêng cụm "State" và "Best Practices for State" khá sát nhau trên sơ đồ nên khó tách rạch ròi. Ở đây gom chung vào một cụm.

**Introduction**
- [ ] What is Infrastructure as Code?
- [ ] What is Terraform?
- [ ] Usecases and Benefits
- [ ] CaC vs IaC
- [ ] Installing Terraform

**Hashicorp Config. Language (HCL)**
- [ ] What is HCL?
- [ ] Basic Syntax

**Providers**
- [ ] Terraform Registry
- [ ] Configuring Providers
- [ ] Versions

**Project Initialization** (topic đơn)

**Resources**
- [ ] Resource Behavior
- [ ] Resource Lifecycle
- [ ] Meta Arguments: `depends_on`, `count`, `for_each`, `provider`, `lifecycle`

**Variables**
- [ ] Input Variables
- [ ] Type Constraints
- [ ] Variable Definition File
- [ ] Environment Variables
- [ ] Validation Rules
- [ ] Local Values

**Outputs**
- [ ] Output Syntax
- [ ] Sensitive Outputs
- [ ] Preconditions

**Format & Validate**
- [ ] terraform fmt
- [ ] terraform validate
- [ ] TFLint

**State / Best Practices for State**
- [ ] State
- [ ] Remote State
- [ ] State Locking
- [ ] Import Existing Resources
- [ ] Splitting State Files
- [ ] Versioning
- [ ] Sensitive Data
- [ ] Best Practices for State

**Deployment / Clean Up**
- [ ] terraform plan
- [ ] terraform apply
- [ ] terraform destroy

**Inspect / Modify State: Basic / Advanced Commands**
- [ ] graph
- [ ] show
- [ ] list
- [ ] output
- [ ] mv
- [ ] rm
- [ ] -replace option in apply
- [ ] state pull / push
- [ ] state replace-provider
- [ ] state force-unlock

**Modules**
- [ ] Root vs Child Modules
- [ ] Published Modules Usage
- [ ] Creating Local Modules
- [ ] Inputs / Outputs
- [ ] Modules Best Practices

**Provisioners**
- [ ] When to Use?
- [ ] Creation / Destroy Time
- [ ] file provisioner
- [ ] local-exec provisioner
- [ ] remote-exec provisioner
- [ ] Custom Provisioners

**Data Sources** (topic đơn)

**Template Files** (topic đơn)

**Workspaces** (topic đơn, workspace của CLI)

**CI / CD Integration**
- [ ] GitHub Actions
- [ ] Circle CI
- [ ] GitLab CI
- [ ] Jenkins

**Testing**
- [ ] Unit Testing
- [ ] Contract Testing
- [ ] Integration Testing
- [ ] End to End Testing
- [ ] Testing Modules

**Scaling Terraform**
- [ ] Splitting Large State
- [ ] Parallelism
- [ ] Deployment Workflow
- [ ] Version Management
- [ ] Terragrunt
- [ ] Infracost

**Security**
- [ ] Secret Management
- [ ] Compliance / Sentinel
- [ ] Terrascan
- [ ] Checkov
- [ ] Trivy
- [ ] KICS

**HCP**
- [ ] What and when to use HCP?
- [ ] Enterprise Features
- [ ] Authentication
- [ ] Workspaces (HCP)
- [ ] VCS Integration
- [ ] Run Tasks

## 6. OpenTofu: tính năng khác Terraform

- Docs hiện hành là OpenTofu **1.13.x** (https://opentofu.org/docs/). Bản 1.13.0 phát hành ngày 29/9/2026. Theo https://github.com/opentofu/opentofu/releases, bản phát hành gần đây nhất được gắn nhãn "Latest" là v1.13.2 (21/10/2026).
- Trang docs không có mục "What's new" hay "khác Terraform" (`/docs/intro/whats-new/` trả về 404). Vì vậy danh sách dưới đây lấy từ các bài blog phát hành chính thức trên opentofu.org.
- Lưu ý: một số tính năng sau đó Terraform cũng có, dù cú pháp hoặc chi tiết có thể khác. Đó là provider-defined functions, `removed` block, import `for_each`, ephemeral resources/write-only attributes và khóa state S3 native qua `use_lockfile`. Việc Terraform đã có các tính năng này là ghi chú (chưa kiểm nguồn), vì không nằm trong phạm vi tra cứu lần này.

**State & plan encryption** (từ 1.7, https://opentofu.org/docs/language/state/encryption/). Đây là điểm khác biệt lớn nhất so với Terraform.
- [ ] Mã hóa state và plan khi lưu, cả ở local lẫn backend. Áp dụng cho cả `terraform_remote_state`.
- [ ] Key providers: `pbkdf2`, `aws_kms`, `gcp_kms`, `azure_vault`, `openbao`, `external`. Ngoài ra có OVHcloud KMS (external, do OVHcloud duy trì).
- [ ] Methods: `aes_gcm`, `external`, `unencrypted` (dùng để migrate).
- [ ] Block `fallback` để migrate hoặc xoay khóa. Cấu hình `enforced = true`. Biến môi trường `TF_ENCRYPTION`. Thuộc tính `encrypted_metadata_alias`.
- [ ] `remote_state_data_sources` để mã hóa riêng cho từng remote state.

**1.7** (https://opentofu.org/blog/opentofu-1-7-0/, 30/4/2024)
- [ ] End-to-end state encryption
- [ ] Dynamic provider-defined functions
- [ ] The `removed` block
- [ ] Loopable import blocks (`for_each` trong `import`)

**1.8** (https://opentofu.org/blog/opentofu-1-8-0/, 29/7/2024)
- [ ] Early Evaluation: dùng variables/locals trong module source, backend config và state encryption
- [ ] Đuôi file `.tofu`, được ưu tiên hơn file `.tf` cùng tên
- [ ] Provider Mocking và Resource Overrides trong `tofu test`

**1.9** (https://opentofu.org/blog/opentofu-1-9-0/, 10/1/2025)
- [ ] Provider iteration (`for_each` trên provider block)
- [ ] Cờ `-exclude`

**1.10** (https://opentofu.org/blog/opentofu-1-10-0/, 23/6/2025)
- [ ] OCI Registry Support cho providers/modules, hữu ích với môi trường air-gapped
- [ ] Native S3 State Locking, không cần DynamoDB
- [ ] Deprecation Support cho variables/outputs
- [ ] Enhanced Planning: dùng file để chỉ định target/exclude
- [ ] Global Provider Cache Lock
- [ ] OpenTelemetry Tracing (chỉ local)
- [ ] External Key Providers cho encryption
- [ ] Enhanced `moved` và `removed` blocks

**1.11** (https://opentofu.org/blog/opentofu-1-11-0/, 9/12/2025)
- [ ] Ephemeral resources và write-only attributes
- [ ] Meta-argument `enabled` cho resource và module

**1.12** (https://opentofu.org/blog/opentofu-1-12-0/, 14/5/2026)
- [ ] `prevent_destroy` động, tham chiếu được input variable
- [ ] Ghi checksum provider đầy đủ hơn (`zh:`, `h1:`)
- [ ] `-json-into=FILENAME`
- [ ] Lifecycle `destroy = false`: gỡ khỏi state mà không xóa tài nguyên thật
- [ ] Cài provider song song

**1.13** (https://opentofu.org/blog/opentofu-1-13-0/, 29/9/2026)
- [ ] Hàm `convert` và họ hàm `assume...`, dùng làm gợi ý giá trị/kiểu khi plan
- [ ] Linting Experiment
- [ ] Symbol Libraries Experiment
- [ ] Hỗ trợ Windows ARM64

Trang liên quan cho track: Migrating to OpenTofu (https://opentofu.org/docs/intro/migration/), What are TACOS? (https://opentofu.org/docs/intro/tacos/), OpenTofu vs. Alternatives (https://opentofu.org/docs/intro/vs/).

---

## Gộp: checklist đề xuất

### Kubernetes (CKA + roadmap.sh, kèm CKAD bổ sung)

**Nền tảng**
- [ ] Kubernetes là gì, vì sao dùng, các lựa chọn thay thế `[RM-K8s]`
- [ ] Key concepts và kiến trúc: control plane, node components `[RM-K8s][CKA]`
- [ ] Containers và container images (build, sửa image) `[RM-K8s][CKAD]`
- [ ] Cài cluster local, chọn managed provider, deploy ứng dụng đầu tiên `[RM-K8s]`

**Cluster architecture, cài đặt, vận hành**
- [ ] Chuẩn bị hạ tầng để cài cluster `[CKA]`
- [ ] Tạo và quản lý cluster bằng kubeadm; cài control plane; thêm và quản lý worker nodes `[CKA][RM-K8s]`
- [ ] Vòng đời cluster: upgrade, backup/restore etcd `[CKA]` (phần etcd chưa kiểm nguồn: curriculum chỉ ghi "lifecycle")
- [ ] HA control plane `[CKA]`
- [ ] Self-managed hay managed cluster `[RM-K8s]`
- [ ] Multi-cluster management `[RM-K8s]`
- [ ] Extension interfaces CNI / CSI / CRI `[CKA][RM-K8s]` (CSI Drivers)
- [ ] CRDs, operators, custom controllers, extension APIs `[CKA][CKAD][RM-K8s]`
- [ ] Custom schedulers và extenders `[RM-K8s]`
- [ ] Helm (charts; cài component; deploy package) `[CKA][CKAD][RM-K8s]`
- [ ] Kustomize `[CKA][CKAD]`
- [ ] API deprecations `[CKAD]`

**Workloads**
- [ ] Pods, multi-container patterns (sidecar, init) `[RM-K8s][CKAD]`
- [ ] ReplicaSets, Deployments `[RM-K8s][CKA]`
- [ ] StatefulSets, stateful applications `[RM-K8s]`
- [ ] DaemonSet `[CKAD]`
- [ ] Jobs, CronJobs `[RM-K8s][CKAD]`
- [ ] Self-healing primitives `[CKA]`
- [ ] Probes / health checks `[CKAD][RM-K8s]` (Resource Health)
- [ ] ConfigMaps `[CKA][CKAD][RM-K8s]`
- [ ] Secrets `[CKA][CKAD][RM-K8s]`

**Deploy strategies & delivery**
- [ ] Rolling update và rollback `[CKA][CKAD][RM-K8s]`
- [ ] Blue/green, canary `[CKAD][RM-K8s]`
- [ ] CI/CD integration, GitOps `[RM-K8s]`

**Scheduling & resources**
- [ ] Pod admission và scheduling: node selector, node affinity `[CKA]`
- [ ] Taints và tolerations `[RM-K8s]` (thuộc "etc." trong mục scheduling của CKA)
- [ ] Topology spread constraints `[RM-K8s]`
- [ ] Pod priority, preemption, evictions `[RM-K8s]`
- [ ] Requests và limits, resource requirements `[CKA][CKAD][RM-K8s]`
- [ ] ResourceQuota, LimitRange theo namespace `[CKAD][RM-K8s]`
- [ ] Autoscaling: HPA, VPA, cluster autoscaling `[CKA][RM-K8s]`

**Networking**
- [ ] Pod-to-pod connectivity, network model `[CKA][RM-K8s]`
- [ ] Services: ClusterIP, NodePort, LoadBalancer, endpoints `[CKA][CKAD][RM-K8s]`
- [ ] Ingress controllers và Ingress resources `[CKA][CKAD][RM-K8s]`
- [ ] Gateway API `[CKA][RM-K8s]`
- [ ] CoreDNS `[CKA]`
- [ ] NetworkPolicies `[CKA][CKAD][RM-K8s]`

**Storage**
- [ ] StorageClass và dynamic provisioning `[CKA]`
- [ ] Volume types, access modes, reclaim policies `[CKA]`
- [ ] PV/PVC `[CKA][CKAD]`
- [ ] Ephemeral volumes `[CKAD]`
- [ ] CSI drivers `[RM-K8s][CKA]`

**Security**
- [ ] RBAC `[CKA][RM-K8s]`
- [ ] Authentication, authorization, admission control `[CKAD]`
- [ ] ServiceAccounts `[CKAD]`
- [ ] SecurityContext, capabilities, container/pod security `[CKAD][RM-K8s]`

**Observability & troubleshooting** (30% của CKA)
- [ ] Logs: container output streams `[CKA][CKAD][RM-K8s]`
- [ ] Metrics, theo dõi resource usage, tối ưu tài nguyên `[CKA][CKAD][RM-K8s]`
- [ ] Traces, observability engines `[RM-K8s]`
- [ ] Troubleshoot cluster, node, cluster components `[CKA]`
- [ ] Troubleshoot services và networking `[CKA][CKAD]`
- [ ] Debug ứng dụng (kubectl debug, events, describe) `[CKAD]`

### Terraform / OpenTofu (Associate 004 + roadmap.sh + OpenTofu)

**IaC & giới thiệu**
- [ ] IaC là gì, lợi ích, use cases `[TA004][RM-TF]`
- [ ] CaC vs IaC `[RM-TF]`
- [ ] Multi-cloud, hybrid, service-agnostic workflows `[TA004]`
- [ ] Cài Terraform/OpenTofu, quản lý phiên bản CLI `[RM-TF]` (Installing, Version Management)
- [ ] Migrate từ Terraform sang OpenTofu `[OTF]`

**HCL & cấu hình**
- [ ] HCL: cú pháp cơ bản `[RM-TF]`
- [ ] `resource` và `data` blocks; tham chiếu thuộc tính giữa các resource `[TA004][RM-TF]`
- [ ] Resource behavior và lifecycle `[RM-TF]`
- [ ] Meta-arguments: `depends_on`, `count`, `for_each`, `provider`, `lifecycle` `[TA004 4f][RM-TF]`
- [ ] Meta-argument `enabled`; lifecycle `destroy = false`; `prevent_destroy` động `[OTF]`
- [ ] Input variables, type constraints, complex types `[TA004][RM-TF]`
- [ ] tfvars, biến môi trường `TF_VAR_*` `[RM-TF]`
- [ ] Locals `[RM-TF]`
- [ ] Outputs, sensitive outputs `[TA004][RM-TF]`
- [ ] Custom conditions: validation rules, preconditions/postconditions `[TA004 4g][RM-TF]` (postconditions và `check` blocks: chưa kiểm nguồn, vì cả hai nguồn chỉ ghi chung "custom conditions" hoặc "Preconditions")
- [ ] Expressions và functions, dynamic configuration `[TA004]`
- [ ] Template files (`templatefile`) `[RM-TF]`
- [ ] Provider-defined functions `[OTF]`
- [ ] Hàm `convert` / `assume...` `[OTF]`
- [ ] Đuôi `.tofu`, early evaluation (biến trong backend và module source) `[OTF]`
- [ ] Deprecation cho variable/output `[OTF]`

**Providers**
- [ ] Cách Terraform dùng provider; cài provider và pin version (lock file) `[TA004][RM-TF]`
- [ ] Nhiều provider, alias `[TA004][RM-TF]`
- [ ] Terraform Registry `[RM-TF]`
- [ ] Provider `for_each` `[OTF]`
- [ ] OCI registry cho providers/modules `[OTF]`
- [ ] Global provider cache lock, checksums `[OTF]`

**Core workflow & CLI**
- [ ] Workflow write → plan → apply `[TA004]`
- [ ] `init` `[TA004][RM-TF]`
- [ ] `fmt`, `validate` `[TA004][RM-TF]`
- [ ] `plan`, `apply`, `destroy` `[TA004][RM-TF]`
- [ ] `-replace` `[RM-TF]`
- [ ] `graph`, `show`, `output` `[RM-TF][TA004 7b]`
- [ ] Cờ `-exclude` và target/exclude bằng file `[OTF]`
- [ ] Verbose logging (`TF_LOG`) `[TA004 7c]`
- [ ] OpenTelemetry tracing `[OTF]`
- [ ] Parallelism `[RM-TF]`

**State**
- [ ] State dùng để làm gì, Terraform quản lý state ra sao `[TA004][RM-TF]`
- [ ] Local backend `[TA004]`
- [ ] Remote state qua `backend` block `[TA004][RM-TF]`
- [ ] State locking; `force-unlock` `[TA004][RM-TF]`
- [ ] S3 native locking `[OTF]`
- [ ] Drift; `-refresh-only` `[TA004 6d]` (phần `-refresh-only` chưa kiểm nguồn)
- [ ] Lệnh state: `list`, `show`, `mv`, `rm`, `pull`/`push`, `replace-provider` `[RM-TF][TA004 7b]`
- [ ] Refactor bằng `moved` và `removed` blocks `[OTF]` (với Terraform: chưa kiểm nguồn)
- [ ] Import: lệnh và `import` block, import có `for_each` `[TA004 7a][RM-TF][OTF]`
- [ ] Best practices cho state: chia nhỏ state, versioning, dữ liệu nhạy cảm `[RM-TF]`
- [ ] **State & plan encryption**: key providers, methods, fallback, enforced `[OTF]`
- [ ] Workspaces CLI `[RM-TF]`

**Modules**
- [ ] Nguồn module (registry, git, local) `[TA004 5a][RM-TF]`
- [ ] Root và child modules; scope của biến; inputs/outputs `[TA004 5b][RM-TF]`
- [ ] Dùng module đã publish, tự viết local module `[TA004 5c][RM-TF]`
- [ ] Version module `[TA004 5d]`
- [ ] Best practices cho module `[RM-TF]`

**Provisioners**
- [ ] Khi nào dùng; creation-time và destroy-time; `file`, `local-exec`, `remote-exec`, custom `[RM-TF]`

**Bảo mật & dữ liệu nhạy cảm**
- [ ] Sensitive data, secret management, Vault `[TA004 4h][RM-TF]`
- [ ] Ephemeral resources, write-only attributes `[OTF]`
- [ ] Policy/compliance: Sentinel `[RM-TF][TA004 8b]`
- [ ] Scanners: Checkov, Trivy, KICS, Terrascan `[RM-TF]`
- [ ] TFLint `[RM-TF]`

**Testing**
- [ ] Unit, contract, integration, end-to-end testing; test module `[RM-TF]`
- [ ] `tofu test` với provider mocking và resource overrides `[OTF]`

**Scale & delivery**
- [ ] CI/CD: GitHub Actions, GitLab CI, CircleCI, Jenkins `[RM-TF]`
- [ ] Chia state lớn; deployment workflow `[RM-TF]`
- [ ] Terragrunt `[RM-TF]`
- [ ] Infracost `[RM-TF]`
- [ ] TACOS (nền tảng chạy IaC tự động) `[OTF]`

**HCP Terraform** (riêng Terraform, OpenTofu không có)
- [ ] Dùng HCP Terraform để tạo hạ tầng; khi nào nên dùng `[TA004 8a][RM-TF]`
- [ ] Collaboration và governance; enterprise features `[TA004 8b][RM-TF]`
- [ ] Workspaces và projects của HCP `[TA004 8c][RM-TF]`
- [ ] Integration: VCS, run tasks, authentication (`terraform login`) `[TA004 8d][RM-TF]`

---

## Nguồn không truy cập được hoặc lưu ý

- `https://github.com/kamranahmedse/developer-roadmap/tree/master/src/data/roadmaps/kubernetes/content` trả về 404. Repo đã đổi tên thành `nilbuild/developer-roadmap`, cấu trúc mới là `roadmaps/<name>/content/`. Danh sách chủ đề và cách nhóm lấy từ JSON API chính thức của roadmap.sh.
- Trang HTML roadmap.sh/kubernetes và roadmap.sh/terraform không có danh sách chủ đề trong text, do render bằng JS.
- `https://opentofu.org/docs/intro/whats-new/` trả về 404. Thay bằng các bài blog phát hành.
- Mốc ngày nghỉ hưu bản 003 chỉ thấy qua snippet tìm kiếm của trang certifications HashiCorp, không còn hiển thị trên bản trang hiện tại.
- Trang ôn tập Terraform Associate 004 không công bố trọng số domain.
