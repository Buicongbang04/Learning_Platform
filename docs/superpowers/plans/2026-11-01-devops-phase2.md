# DevOps track Phase 2: hạ tầng dùng chung + module 06–11 + capstone m03–m06 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm các helper an toàn mà Kubernetes, CI, IaC và container cần, rồi viết module 06–11 và milestone m03–m06 đúng spec.

**Architecture:** Mỗi helper an toàn mới nằm trong `testkit.py`, có unit test chứng minh tính chất an toàn, được ghi vào bảng "Track DevOps" của `CONTENT_SPEC.md` và được validator bắt buộc dùng. Mỗi module dùng helper, không tự chế. Helper được viết ngay trước module đầu tiên cần nó.

**Tech Stack:** Python 3.12, uv, pytest; bubblewrap; Docker + BuildKit; kind, kubectl, Helm, Kustomize; `act`; OpenTofu + LocalStack; Ansible (qua uv); trivy; registry:2.

**Spec:** `docs/superpowers/specs/2026-11-01-devops-track-design.md` (mục 4 hàng 06–11, mục 5, 6, 7 hàng m03–m06). Bối cảnh và các quyết định Phase 1: `docs/superpowers/handoff-devops.md`. Quy ước bắt buộc: mục "Track DevOps" trong `CONTENT_SPEC.md`. Checklist K8s/IaC: `docs/superpowers/research/2026-11-01-k8s-terraform-topic-checklists.md`.

## Global Constraints

- Làm trong worktree `/home/bangbc/Documents/Learning_Platform-devops`, nhánh `devops-phase2` (tách từ `origin/main` 8dd6649). Không đụng `/home/bangbc/Documents/Learning_Platform`.
- Mọi quy tắc của Phase 1 vẫn giữ: mục "Track DevOps" trong `CONTENT_SPEC.md`, global constraints của plan Phase 1, quy ước nội dung trong `CONTENT_SPEC.md`.
- Code người học chạy trên host → `run_sandboxed`/`sandbox_command`. Container do test khởi chạy → `DockerLab`. Cluster → `KubeLab` (Task 9). Workflow → `act_run` (Task 4). Không gọi `docker`, `kind`, `act`, `kubectl`, `helm` trực tiếp trong test module/capstone; validator cấm.
- Test không bao giờ dùng `~/.kube/config`, current-context, `~/.aws`, `~/.docker/config.json` hay biến môi trường cloud của người học.
- Việc nặng (cluster, build image, `act`, LocalStack) của builder: `nice -n 15 taskset -c 12-35`, `DEVOPS_CPUSET=12-35`, mỗi lúc một job nặng, tắt cluster/stack sau mỗi đợt kiểm. Không đụng container `de-learning-*`, `portainer` và service `localstack` của track DE.
- Builder cài công cụ vào `~/.local/bin` theo đúng phần `## 0. Cài đặt` của module (kiểm checksum, phiên bản cố định), không sudo. kind v0.30.0 đã cài.
- Module: 5–8 phần `## ` (không tính `## 0. Cài đặt`), ≥2 mermaid, phần cuối là tài liệu tham khảo, interview ≥12 câu, 5–9 bài (≥3 basic, ≥2 advanced; module 08 khoảng 8 bài), ≥1 bài sự cố cố ý (module 05 trở đi), bảng so sánh công cụ, không chép bài của track DE (nhất là DE 08 và DE 11).
- Module 08, 10, 11 phủ checklist research (CKA v1.37 cộng các mục CKAD đáng thêm; Terraform Associate 004 cộng roadmap.sh, ghi rõ chỗ OpenTofu khác Terraform).
- Starter fail hoặc skip, không error. `SOLUTION=1` pass, không skip vì thiếu công cụ, khi công cụ đã cài. Test skip không tính là pass.
- Không comment trong code, docstring chỉ khi thật cần. Tiếng Việt, giữ thuật ngữ tiếng Anh. Commit không có dòng Co-Authored-By.
- Track DE, DS, DA giữ nguyên kết quả `SOLUTION=1` (chạy riêng từng track); `cd app && pnpm test && pnpm typecheck` pass.

## Review Focus

1. Máy người học có `~/.kube/config` trỏ cluster thật làm current-context → không test nào được apply vào đó. Test trong Task 9 (KubeLab dùng kubeconfig tạm, có test chứng minh `KUBECONFIG` và `~/.kube` của người học không được đọc).
2. Cluster `devops-lab` có trong `kind get clusters` nhưng node đã dừng (sau reboot) → skip kèm lời nhắc khởi động lại, không treo kubectl tới timeout. Test trong Task 9.
3. Máy người học có `~/.actrc`, `GITHUB_TOKEN`, hay workflow pull image mới → `act_run` dùng env sạch, image ghim, `--pull=false`. Test trong Task 4.
4. `tofu apply` bị ngắt giữa chừng → tài nguyên trên LocalStack riêng của DevOps vẫn bị dọn (prefix theo test, `destroy` trong `finally`), không đụng `localstack` của DE. Test trong Task 6.
5. Image người học build bằng Dockerfile chạy root hoặc lấy tài nguyên lớn → `DockerLab.build` gắn nhãn, giới hạn CPU/memory, xoá image khi đóng; container chạy với `no-new-privileges`. Test trong Task 1 và Task 2.

---

### Task 1: Hạ tầng dùng chung, đợt 1

**Files:**
- Modify: `testkit.py`, `tests/test_testkit_devops.py`, `tests/test_devops_track.py`, `CONTENT_SPEC.md` (bảng Track DevOps)
- Modify: 5 tệp test của `tracks/devops/modules/03-git-vcs-hosting` (thay bản chép bằng helper)

**Interfaces:**
- Produces: `SAFE_GIT_CONFIG: tuple[str, ...]` (`-c core.hooksPath=/dev/null -c core.fsmonitor=false -c commit.gpgsign=false -c init.defaultBranch=main`), `git_env(home: Path, *, date: str | None = None) -> dict[str, str]` (env dựng từ đầu như module 03 đang làm, kèm `GIT_CEILING_DIRECTORIES`), `class GitRepo(path: Path, home: Path)` với `.git(*args) -> CompletedProcess` chạy trực tiếp kèm `SAFE_GIT_CONFIG` khi chưa `taint()`, chạy qua `run_sandboxed` sau `taint()`.
- Produces: so phiên bản đệm số 0 (`(1, 27) == (1, 27, 0)`); thông báo riêng khi không đọc được phiên bản; `import pwd` trong hàm, `KeyError` → coi như không có home thật; `sandbox_ready()` có cache; `run_sandboxed` che thêm `~/.kube`, `~/.aws`, `~/.ssh`, `~/.config/gcloud`, `~/.azure` khi tồn tại.
- Produces: `DockerLab` mặc định `--security-opt no-new-privileges`; `run_once(..., memory=, pids_limit=)`; khi container detached chết hoặc `wait_*` hết giờ, thông báo lỗi kèm 40 dòng `docker logs` cuối (lấy trước khi `--rm` xoá container: chạy detached không `--rm`, xoá trong `close()`).
- Produces: validator thay `DIRECT_DOCKER` bằng danh sách cấm cho test dưới `modules/` và `capstone/`: argv bắt đầu bằng `docker`, `kind`, `act`, `kubectl`, `helm`, `tofu`(chỉ khi không qua `run_sandboxed`), hoặc `_docker(`; không bắt `require_tool(...)`, `require_image(...)`, `shutil.which(...)`; có fixture âm và dương cho từng luật.

- [ ] **Step 1: Viết test thất bại** cho từng hành vi trên trong `tests/test_testkit_devops.py` và `tests/test_devops_track.py` (`test_version_padding`, `test_unreadable_version_message`, `test_real_homes_without_passwd`, `test_sandbox_hides_cloud_credentials`, `test_docker_lab_no_new_privileges`, `test_docker_lab_logs_on_failure`, `test_git_repo_taint_switches_to_sandbox`, `test_validator_tool_denylist`, `test_validator_allows_require_tool_with_version`).
- [ ] **Step 2:** `uv run pytest tests/test_testkit_devops.py tests/test_devops_track.py -q` → FAIL.
- [ ] **Step 3: Cài đặt** trong `testkit.py`, sửa validator.
- [ ] **Step 4: Chuyển module 03** sang `GitRepo`/`git_env`/`SAFE_GIT_CONFIG`; xoá bản chép. `SOLUTION=1 uv run pytest tracks/devops/modules/03-git-vcs-hosting -q` và starter cho cùng kết quả như trước.
- [ ] **Step 5:** `uv run pytest tests -q` → PASS; `SOLUTION=1` cho `tracks/devops` → không kém Phase 1.
- [ ] **Step 6: Cập nhật bảng helper** trong `CONTENT_SPEC.md`.
- [ ] **Step 7: Commit** — `git commit -m "testkit: helper git dùng chung, sandbox che thông tin cloud, DockerLab giữ log khi lỗi, validator cấm gọi công cụ trực tiếp"`

### Task 2: Build image, compose và sửa Olist Shop

**Files:**
- Modify: `testkit.py`, `tests/test_testkit_devops.py`, `CONTENT_SPEC.md`
- Modify: `tracks/devops/sample-app/olist_shop/main.py`, `olist_shop/db.py`, `tracks/devops/sample-app/tests/`

**Interfaces:**
- Produces: `DockerLab.build(context: Path, alias: str, *, dockerfile: str = "Dockerfile", build_args: dict | None = None) -> str` trả tag `devops-ex-<id>/<alias>:test`, gắn nhãn, giới hạn CPU và memory cho bước build, `rmi` trong `close()`; `DockerLab.image_inspect(tag) -> dict`, `DockerLab.history(tag) -> list[dict]`.
- Produces: `DockerLab.compose(file: Path, *, env: dict | None = None) -> ComposeProject` chạy với `-p devops-ex-<id>` cộng một tệp override sinh ra (cpuset, `mem_limit`, `pids_limit`, nhãn, cổng remap về `127.0.0.1:<cổng trống>`), `down -v --remove-orphans` trong `close()`; `ComposeProject.port(service, container_port) -> int`.
- Builder kiểm BuildKit có tôn trọng giới hạn CPU không; nếu không, `build` dùng một builder `docker-container` riêng tên `devops-ex-builder` tạo bằng `--driver-opt cpuset-cpus=...,memory=...`, ghi kết quả kiểm vào `CONTENT_SPEC.md`.
- Produces (Olist Shop): response 500 có `X-Request-ID`; `POST /jobs/recompute` trả 503 `{"error":"redis unavailable"}` khi Redis lỗi; engine Postgres có `connect_args={"connect_timeout": 3}`.

- [ ] **Step 1: Test thất bại**: `test_docker_lab_build_tags_labels_and_removes`, `test_docker_lab_compose_override_pins_and_loopback`, `test_docker_lab_compose_cleanup_on_error`; sample-app: `test_500_has_request_id`, `test_recompute_503_when_redis_down`, `test_engine_connect_timeout`.
- [ ] **Step 2:** chạy → FAIL.
- [ ] **Step 3: Cài đặt**, kiểm BuildKit thật (ghim CPU).
- [ ] **Step 4:** `uv run pytest tests tracks/devops/sample-app -q` → PASS; không còn image/container/network `devops-ex-*`.
- [ ] **Step 5: Commit** — `git commit -m "testkit: DockerLab.build và compose; Olist Shop trả request id khi 500, 503 khi Redis lỗi"`

### Task 3: Module 06-containers

Trọng tâm (spec mục 4 hàng 06): Docker chuyên sâu (layer, cache, multi-stage, image nhỏ, non-root, `no-new-privileges`, read-only rootfs, healthcheck, signal và PID 1, rootless, registry, tag vs digest), quét lỗ hổng bằng trivy (`## 0. Cài đặt` cho trivy và hướng dẫn kiểm Docker/BuildKit), LXC/LXD (khái niệm, so sánh với Docker và VM), so sánh Docker/Podman/containerd/nerdctl/Buildah/Kaniko.

Bài bắt buộc: viết lại Dockerfile Olist Shop thành multi-stage non-root (kiểm bằng `DockerLab.build` + `image_inspect` + chạy thật `/healthz`, không chép bài DE 08 basic/01); bài quét trivy và xử lý CVE theo chính sách (chạy trivy trên image đã build, cache DB trivy dùng chung, skip khi không có DB và không có mạng); ≥1 bài sự cố (vd. container thoát mã 137 do OOM, PID 1 không chuyển SIGTERM khiến `docker stop` mất 10 giây, ghi vào rootfs read-only); Advanced: chính sách image cho tổ chức (rubric).

Chấm: `DockerLab.build`, `DockerLab.start`, `require_tool("trivy")`, `require_image`.

- [ ] Step 1–5 giống quy trình module của Phase 1 (test trước → starter, lời giải, đề → kiểm chứng ghim CPU → lý thuyết, interview → commit `DevOps: module 06-containers`). Sau kiểm: không còn image/container `devops-ex-*`.

### Task 4: Hạ tầng cho CI: act và registry

**Files:** Modify `testkit.py`, `tests/test_testkit_devops.py`, `setup/docker-compose.yml` (service `registry`, profile `devops`), `setup/.env.example`, `setup/DEVOPS-TOOLS.md`, `CONTENT_SPEC.md`.

**Interfaces:**
- Produces: `act_run(workflow_dir: Path, *, event: str = "push", job: str | None = None, env: dict | None = None, secrets: dict | None = None, timeout: float = 600) -> CompletedProcess`: env dựng từ đầu (`HOME=tmp`, không `GITHUB_TOKEN` thừa kế, không đọc `~/.actrc`), `-P ubuntu-latest=<image ghim>` kiểm bằng `require_image`, `--pull=false`, `--container-options "<cpuset> --memory 1g --pids-limit 512 --label devops-ex=1"`, `--container-daemon-socket -`, dọn container có nhãn của lần chạy đó khi kết thúc. Skip khi thiếu `act` hoặc image runner.
- Produces: service compose `registry` (`registry:2` ghim tag, `127.0.0.1:${DEVOPS_REGISTRY_PORT:-15000}:5000`, cpuset, profile `devops`), `SERVICES["registry"]`, `require_registry()`.

- [ ] Test thất bại (`test_act_run_clean_env`, `test_act_run_pins_image_and_limits`, `test_act_run_cleans_containers`, `test_registry_service_loopback`) → cài đặt → kiểm thật một workflow tối giản bằng `act` → commit `testkit: act_run và registry local cho CI`.

### Task 5: Module 07-cicd-artifacts

Trọng tâm: thiết kế pipeline (stage, cache, matrix, artifact, environment và approval, secret, OIDC khái niệm), chiến lược deploy (rolling, blue/green, canary, feature flag, rollback), artifact management (registry local, tag bất biến, digest, SBOM, ký image khái niệm), so sánh GitHub Actions/GitLab CI/Jenkins/CircleCI/TeamCity/Octopus và Artifactory/Nexus/Cloudsmith; `## 0. Cài đặt` cho `act` và image runner.

Bài bắt buộc: workflow test + build + push lên registry local cho Olist Shop (chạy bằng `act_run`, kiểm image có trong registry theo digest); bài pipeline lỗi cố ý (cache sai key, secret lộ ra log, job chạy sai thứ tự); quiz chọn chiến lược deploy; Advanced: thiết kế pipeline nhiều môi trường có rollback (rubric). Không viết sẵn deliverable m04.

- [ ] Quy trình module → commit `DevOps: module 07-cicd-artifacts`.

### Task 6: Hạ tầng cho IaC: LocalStack riêng và tofu

**Files:** Modify `setup/docker-compose.yml` (service `localstack-devops`, profile `devops`, image LocalStack ghim, cổng `127.0.0.1:${LOCALSTACK_DEVOPS_PORT:-14566}`), `setup/.env.example`, `testkit.py`, `tests/test_testkit_devops.py`, `CONTENT_SPEC.md`.

**Interfaces:**
- Produces: `SERVICES["localstack-devops"]`; `tofu_env(home: Path, *, prefix: str) -> dict[str, str]` (`AWS_ACCESS_KEY_ID=test`, `AWS_SECRET_ACCESS_KEY=test`, `AWS_REGION=us-east-1`, `AWS_CONFIG_FILE=/dev/null`, `AWS_SHARED_CREDENTIALS_FILE=/dev/null`, `AWS_EC2_METADATA_DISABLED=true`, `TF_PLUGIN_CACHE_DIR` dùng chung ở `~/.cache/devops-track/tofu-plugins`, `TF_IN_AUTOMATION=1`, `TF_VAR_prefix=<prefix>`, endpoint LocalStack riêng); `class TofuLab` (context manager: thư mục làm việc trong tmp, `init/plan/apply/output/state` qua `run_sandboxed` với cache plugin là thư mục ghi được, `destroy -auto-approve` trong `close()` kể cả khi lỗi).
- Service `localstack` của DE không đổi.

- [ ] Test thất bại (`test_tofu_env_isolated`, `test_tofu_lab_destroys_on_error`, `test_localstack_devops_separate_from_de`) → cài đặt (cài `tofu` theo hướng dẫn sẽ viết ở module 08) → kiểm thật apply/destroy một bucket → commit `testkit: LocalStack riêng cho DevOps và TofuLab`.

### Task 7: Module 08-iac-provisioning (khoảng 8 bài)

Trọng tâm: **dạy đầy đủ** theo checklist Terraform Associate 004 và roadmap.sh/terraform trong tệp research: HCL, provider và lock file, resource/data, meta-arguments (`count`, `for_each`, `depends_on`, `lifecycle`, `provider`), variables/locals/outputs, custom conditions (validation, precondition, postcondition, `check`), functions và expressions, state (local, remote backend S3 trên LocalStack, locking, `import` block, `moved`/`removed`, `state mv/rm`, drift và `-refresh-only`), module (nguồn, version, viết module), workspaces vs tách thư mục, `tofu test`, lint/policy (tflint, checkov hoặc tương đương: nêu rõ cái nào chạy được offline), secret trong state; ghi rõ mọi chỗ OpenTofu khác Terraform (state encryption, `.tofu`, early evaluation, `-exclude`, provider `for_each`…) để người học vẫn thi được Associate 004; HCP Terraform chỉ khái niệm; so sánh CDK/CloudFormation/Pulumi.

Bài bắt buộc: module S3 + IAM cho Olist Shop với `for_each` và validation; bài state (import tài nguyên có sẵn, refactor bằng `moved`, phát hiện drift); bài remote state có locking trên LocalStack; ≥1 bài sự cố (state lock kẹt, drift sau khi ai đó sửa tay, `count` → `for_each` làm tài nguyên bị tạo lại); Advanced: thiết kế cấu trúc repo IaC nhiều môi trường (rubric); bài AWS thật tuỳ chọn có hướng dẫn chi phí, budget alarm, `tofu destroy`, và bài local tương đương. Phần LocalStack bản miễn phí không làm được thì dạy khái niệm + hướng dẫn AWS thật (spec mục 9).

- [ ] Quy trình module (dùng `TofuLab`) → commit `DevOps: module 08-iac-provisioning`.

### Task 8: Module 09-config-management

Trọng tâm: Ansible (inventory tĩnh/động, ad-hoc, playbook, module vs shell, idempotency và `changed_when`, handler, role, template Jinja2, variable precedence, vault, tag, `--check --diff`, molecule hoặc test tương đương), push vs pull, mutable vs immutable infrastructure, so sánh Ansible/Chef/Puppet/Salt; `## 0. Cài đặt` cho Ansible qua `uv` (dependency nhóm riêng hoặc `uv tool`, builder chọn và ghi lý do; không làm vỡ lock của track khác).

Chấm: target là container do `DockerLab` khởi chạy (image có SSH hoặc dùng connection `docker` qua helper, không dùng connection tới host thật); playbook người học chạy qua `run_sandboxed` hoặc helper tương đương; không bao giờ chạy playbook vào `localhost` của người học.

Bài bắt buộc: role cài và cấu hình Olist Shop worker (systemd unit từ module 01) idempotent (chạy hai lần, lần hai `changed=0`); bài vault; ≥1 bài sự cố (task không idempotent, handler không chạy, biến bị ghi đè sai precedence); Advanced: chọn Ansible vs image bất biến cho một tình huống (rubric).

- [ ] Quy trình module → commit `DevOps: module 09-config-management`.

### Task 9: Hạ tầng cho Kubernetes: KubeLab

**Files:** Modify `testkit.py`, `tests/test_testkit_devops.py`, `tests/test_devops_track.py`, `CONTENT_SPEC.md`, `setup/DEVOPS-TOOLS.md`; Create `setup/kind/devops-lab.yaml` (cấu hình cluster: 1 control plane + 2 worker, ingress-ready, cổng chỉ trên 127.0.0.1).

**Interfaces:**
- Produces: `require_cluster(name="devops-lab")` kiểm `docker` chạy, cluster có trong danh sách, node container đang chạy và `get --raw /readyz` qua kubeconfig tạm trong 5 giây; ba thông báo skip khác nhau.
- Produces: `class KubeLab(name: str = "devops-lab")` (context manager): kubeconfig tạm từ `kind get kubeconfig --name`, namespace `devops-ex-<id>` có nhãn, `kubectl(*args)` và `helm(*args)` chạy qua `run_sandboxed` với `KUBECONFIG` tạm và `HOME` tạm, `apply_learner(path)` chỉ cho phép object namespaced trong namespace của lab hoặc object cluster-scoped có nhãn `devops-ex=<id>`, dọn namespace và object có nhãn trong `close()`. Không bao giờ đọc `KUBECONFIG`/`~/.kube` của người học.
- Produces: `kind_node_exec(node: str, *cmd) -> CompletedProcess` và `kind_node_cp(...)`, chỉ cho container tên `devops-lab-*`.
- Hướng dẫn tạo cluster ghim CPU: `kind create cluster --config setup/kind/devops-lab.yaml` rồi `docker update --cpuset-cpus "$DEVOPS_CPUSET"` cho mỗi node khi biến có giá trị; lệnh tắt và bật lại cluster.

- [ ] Test thất bại (`test_kube_lab_never_reads_user_kubeconfig`, `test_kube_lab_rejects_foreign_namespace`, `test_kube_lab_cleans_namespace`, `test_require_cluster_stopped_nodes`, `test_kind_node_exec_only_devops_lab`) → cài đặt (cài kubectl, helm theo hướng dẫn sẽ viết ở module 10/11) → tạo `devops-lab` thật, kiểm, tắt → commit `testkit: KubeLab, require_cluster kiểm cluster chạy thật, kind_node_exec`.

### Task 10: Module 10-kubernetes-core

Trọng tâm: phủ checklist CKA v1.37 và CKAD phần core: kiến trúc (API server, etcd, scheduler, controller manager, kubelet, kube-proxy, CRI/CNI/CSI), Pod và multi-container (sidecar, init), Deployment và rollout/rollback, ReplicaSet, StatefulSet, DaemonSet, Job/CronJob, Service (ClusterIP, NodePort, LoadBalancer, headless), Ingress và Gateway API, CoreDNS, ConfigMap/Secret, probes, PV/PVC/StorageClass, etcd backup/restore trên kind (`kind_node_exec`); lab kubeadm tuỳ chọn (1 control plane + 2 worker trên Multipass hoặc LXD, builder chọn; nếu không cài được không cần sudo thì chỉ có hướng dẫn và đánh dấu chưa kiểm chứng); `## 0. Cài đặt` cho kubectl, kind, cách tạo `devops-lab`.

Bài bắt buộc: triển khai Olist Shop (API + worker + Postgres StatefulSet + Redis) với probes và Service, kiểm `/readyz` qua port-forward hoặc Ingress; bài rollout và rollback; etcd backup/restore; ≥1 bài sự cố (CrashLoopBackOff do probe sai, Service không có endpoint do selector sai, ImagePullBackOff, Pending do PVC); Advanced: chọn workload type cho một hệ thống (rubric).

- [ ] Quy trình module (dùng `KubeLab`; cluster bật lúc kiểm, tắt sau) → commit `DevOps: module 10-kubernetes-core`.

### Task 11: Module 11-kubernetes-production

Trọng tâm: RBAC, ServiceAccount, SecurityContext, Pod Security Admission, NetworkPolicy (kind cần CNI hỗ trợ: cấu hình `devops-lab` dùng Calico hoặc ghi rõ cách bật; builder kiểm), scheduling (affinity, taint/toleration, topology spread, priority/preemption), ResourceQuota/LimitRange, HPA (metrics-server trên kind), VPA và cluster autoscaler khái niệm, PDB, Helm chart tự viết (template, values, helper, test, lint), Kustomize (base/overlay), CRD và Operator, troubleshooting có hệ thống, upgrade cluster, API deprecation; so sánh EKS/GKE/AKS, ECS/Fargate, Swarm; `## 0. Cài đặt` cho helm, kustomize (kubectl tích hợp), metrics-server.

Bài bắt buộc: Helm chart cho Olist Shop (lint, template, cài vào namespace của lab, `helm test`); RBAC least privilege cho CI (kiểm bằng `kubectl auth can-i`); NetworkPolicy chỉ cho API nói chuyện với Postgres/Redis; HPA theo CPU; ≥1 bài sự cố (Forbidden do RBAC, Pod bị PSA chặn, NetworkPolicy chặn DNS); Advanced: kế hoạch upgrade cluster không downtime (rubric). Không viết sẵn deliverable m06.

- [ ] Quy trình module → commit `DevOps: module 11-kubernetes-production`.

### Task 12: Capstone m03–m06

**Files:** Create `tracks/devops/capstone/milestones/` theo đúng tên tệp đã khai báo trong `tracks/devops/track.json` cho m03–m06; `capstone/project/tests/test_m03.py`…`test_m06.py`; lời giải tham chiếu trong `capstone/solutions/project/`.

**Interfaces:**
- Consumes: `DockerLab.build/compose` (m03), `act_run` + registry (m04), `TofuLab` + Ansible qua container (m05), `KubeLab` (m06); cơ chế `SOLUTION=1` và `-k mNN` của capstone.
- Produces: m03 Dockerfile multi-stage cho api và worker, compose production; m04 workflow `act` test → build → push registry → deploy staging (compose); m05 OpenTofu trên LocalStack + role Ansible; m06 Helm chart + HPA + NetworkPolicy + RBAC trên `devops-lab`. Hợp đồng chấm ghi đủ trong tệp milestone.

- [ ] Viết test m03–m06 trước (khung fail/skip, không error) → milestone docs + lời giải → `SOLUTION=1` pass (công cụ đủ, cluster bật khi kiểm m06) → validator xanh → commit `DevOps: capstone m03–m06`.

### Task 13: Kiểm toàn nhánh và PR

- [ ] `uv run pytest tests -q`; `SOLUTION=1` cho DA, DE, DS chạy riêng từng track → giống `main`.
- [ ] `SOLUTION=1 nice -n 15 taskset -c 12-35 uv run pytest tracks/devops -q -rs` (bật Mailpit, registry, localstack-devops, `devops-lab` khi cần) → chỉ còn skip đúng thiết kế; liệt kê trong PR.
- [ ] `cd app && pnpm test && pnpm typecheck && pnpm build`.
- [ ] Dọn: không còn container, image, network `devops-ex-*`; tắt cluster và stack; không đụng container của người học.
- [ ] Cập nhật `docs/superpowers/handoff-devops.md` cho Phase 3; push nhánh, đưa người học link PR và nội dung PR.
