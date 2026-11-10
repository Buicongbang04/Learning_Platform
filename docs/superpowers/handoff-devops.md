# Bàn giao: track DevOps (sau Phase 2)

Ngày: 2026-11-10. Dành cho phiên Claude Code làm Phase 3 (module 12–16, milestone m07–m09, cập nhật bảng track trong README gốc).
Đọc hết trước khi làm.

## 1. Trạng thái

- Phase 1 (module 00–05, capstone m01–m02, hạ tầng nền) đã gộp vào `main` qua PR #10.
- Phase 2 trên nhánh `devops-phase2`, worktree `Learning_Platform-devops`:
  - module 06–11, capstone m03–m06;
  - testkit mở rộng: `DockerLab.build/compose/push`, `act_run`, `TofuLab`, `AnsibleLab`, `KubeLab`, `GitRepo`;
  - `setup/act-runner/`, `setup/kind/` (cluster `devops-lab`, Gateway API + Traefik, metrics-server);
  - dịch vụ compose profile `devops` (registry, localstack-devops).
- Mỗi task có implementer và reviewer độc lập, tối đa 5 vòng sửa. Cuối phase có review toàn nhánh và một đợt sửa (`a3bfee6e`). Review
  cuối không còn lỗi Critical.
- `main` (AI Engineer, MLOps, FDE) đã gộp vào nhánh. `tests/` toàn repo: 1788 passed, 63 skipped.
- Theo yêu cầu người dùng, không chạy lại `SOLUTION=1` của track khác sau khi gộp. Thay đổi chung có thể chạm track khác:
  - `DockerLab.run_args` thêm `--security-opt no-new-privileges` (FDE `_SiteLab` và MLOps dùng `DockerLab`);
  - `run_sandboxed` che thêm thư mục credential và đặt `PYTHONNOUSERSITE=1` (MLOps dùng).

## 2. Tài liệu gốc

- Spec: `docs/superpowers/specs/2026-11-01-devops-track-design.md` (Phase 3: dòng 160)
- Plan Phase 2: `docs/superpowers/plans/2026-11-01-devops-phase2.md`
- Checklist K8s/Terraform: `docs/superpowers/research/2026-11-01-k8s-terraform-topic-checklists.md`
- Quy ước (bắt buộc đọc): mục "Track DevOps" trong `CONTENT_SPEC.md`, bảng helper và mục Kubernetes
- Cài công cụ: `setup/DEVOPS-TOOLS.md`. Không có script cài: mỗi module có `## 0. Cài đặt` từng bước, theo quyết định của người
  dùng.

## 3. Quyết định đã đưa ra ở Phase 2

Mỗi dòng ghi giá phải trả nếu sai.

1. **Validator:** cấm gọi docker/kind/act/kubectl/helm/tofu trần trong test module và capstone; chỉ đi qua helper. Sai thì phải nới
   danh sách.
2. **Cài công cụ trước module:** helper cần công cụ trước khi module dạy cài thì builder cài bản ghim (release chính thức + checksum)
   vào `~/.local/bin`; `## 0. Cài đặt` của module dùng đúng bản đó.
3. **Compose:** compose của người học kiểm theo allowlist khoá service và top-level; volume/network có `name:` phải bắt đầu bằng
   `devops-ex-<id>`. Sai thì bài cần khoá lạ bị từ chối; khi đó nới allowlist kèm test.
4. **`act_run`:**
   - Đổi tên workflow thành `devops-ex-<id>-…`.
   - Bước build/push thật có `if: ${{ !env.ACT }}` và được kiểm tĩnh; harness tự build/push/deploy bằng `DockerLab`.
   - Luôn truyền `GITHUB_TOKEN` giả và đặt shim `gh` đầu PATH. Lý do: act 0.2.94 gọi `gh auth token` khi thiếu secret, và đã làm lộ
     token thật một lần trước khi sửa.
5. **Runner act:** image ghim `devops-track/act-runner:1.0-<hash>`, build một lần, giữ lại có chủ đích (khoảng 810 MB, không có
   nhãn `devops-ex`).
6. **OpenTofu:**
   - OpenTofu 1.13.2, `hashicorp/aws` 6.12.0 (giới hạn của LocalStack 4.4.0); capstone m05 cần tofu ≥ 1.11.
   - Provider chỉ lấy từ mirror `~/.cache/devops-track/tofu-plugins`; egress đi qua proxy chết.
   - Mọi cách ghi đè proxy trong HCL/JSON (kể cả `\u` escape) bị từ chối.
7. **Ansible:** chỉ chạy trong sandbox (`AnsibleLab`), target là container sshd của `DockerLab`; connection ghim bằng extra vars
   FQCN. Không bao giờ chạy ansible cục bộ ngoài sandbox (nó tạo `~/.ansible`).
8. **Kubernetes:**
   - Cluster `devops-lab` chạy bằng kind, `kindest/node:v1.34.0` ghim digest, 1 control plane + 2 worker.
   - Ingress ở `127.0.0.1:18180`/`18543`, đổi từ 18080/18443 để tránh trùng quillo của FDE.
   - Kubeconfig admin chỉ ở `~/.kube/devops-lab.yaml`.
   - Người học dùng token ServiceAccount với Role riêng; mỗi lab có bốn ValidatingAdmissionPolicy (chung, rbac, pv, routes) và Pod
     Security baseline/restricted.
9. **Việc admin trên đầu vào của người học:** chỉ qua `admin_local_pv` và `node_action`. PV local nằm trong container worker, vì bind
   từ host cho phép tạo tệp setuid trên host. Restore etcd và nâng cấp kubeadm là lab tay chấm bằng rubric.
10. **`node_action`:** giữ khoá flock và ghi tệp trạng thái. Lab bị SIGKILL thì `require_cluster` của bài sau tự hoàn tác phần còn
    trên cluster. `require_cluster` kiểm cả bản tối thiểu của kind (0.30) và kubectl (1.33).
11. **Thành phần admin cài một lần từ `setup/kind/`:** Gateway API v1.6.3 + Traefik v3.7.17 và metrics-server v0.9.1. Test chỉ gọi
    `require_gateway()`/`require_metrics()`.
12. **Image capstone m06:** dùng image chung `devops-track/olist-shop:1.0`, không dùng image m03 của người học, vì kind không kéo được
    từ registry lúc chấm.

## 4. Việc đầu tiên của Phase 3

- Đọc spec mục Phase 3 và checklist; viết plan Phase 3 (module 12–16, m07–m09) theo cùng quy trình.
- **Module 12, GitOps (ArgoCD) và secrets (SOPS):** cài ArgoCD vào `devops-lab` cần quyền cluster-scoped. Thiết kế giống Gateway:
  admin cài một lần từ `setup/kind/argocd/`, ghim digest; lab chỉ tạo `Application` trong project giới hạn theo namespace
  `devops-ex-<id>`; cần thêm quyền CR vào `KubeLab`, kèm test.
- **Module 13, Observability:** Prometheus/Grafana/Loki/Tempo hoặc OTel Collector. Ưu tiên compose qua `DockerLab.compose` hơn cài vào
  cluster. Olist Shop đã có `X-Request-ID` và log JSON.
- **Module 14, Cloud & serverless:** local-first trên localstack-devops (Lambda, API Gateway, SQS), kèm hướng dẫn AWS thật cho phần
  cần.
- **Module 15, service mesh:** cân nhắc tài nguyên trên kind (Linkerd nhẹ hơn Istio); một công cụ thực hành kèm bảng so sánh.
- **Module 16, SRE và m09:** đánh giá độc lập, game day, postmortem chấm rubric. Cần làm rõ: spec §5 nói phần Advanced có postmortem
  chấm rubric, còn Phase 2 chỉ có postmortem không chấm trong bài sự cố.
- Cập nhật bảng track trong README gốc khi xong.

## 5. Còn treo, cần người dùng quyết

- **MLOps `mlopskit.act_run`:** chạy act với env và HOME thật, không có `GITHUB_TOKEN` giả, nên có thể lộ token `gh` như lỗi DevOps
  đã sửa. Nằm ngoài track DevOps, đã báo người dùng.
- **Binary dùng chung với MLOps trong `~/.local/bin`:**

  | Binary | DevOps | MLOps |
  | --- | --- | --- |
  | act | 0.2.94 | 0.2.89 |
  | kind | 0.30.0 | 0.33.0 |
  | kubectl | 1.34.13 | 1.35.8 |

  Đã ghi trong `setup/DEVOPS-TOOLS.md`. Muốn hết xung đột thì nâng tài liệu MLOps lên act 0.2.94. kind 0.33 với `devops-lab` chưa
  kiểm.
- **Volume Docker ẩn danh** tạo 2026-11-01 lúc 06:52 và 14:04, không rõ nguồn, để nguyên.

## 6. Chưa kiểm chứng trên máy

- Module 11: lab kubeadm (`devops-ts`) và cài chart `podinfo` 6.7.1 (chart có trong index, chưa cài thử).
- Action `aquasecurity/trivy-action` trong workflow tham chiếu m04 (bị bỏ qua khi chạy dưới act).
- Phần chưa kiểm của Phase 1 vẫn như cũ: gitleaks, `dig`, OpenSSL 1.1.1, OpenSSH 8.x.

## 7. Công cụ và tài nguyên để lại trên máy

- **`~/.local/bin`:** shellcheck 0.11.0, act 0.2.94, actionlint, trivy 0.76.1, tofu 1.13.2, kind 0.30.0, kubectl 1.34.13, helm 3.22.1.
- **`~/.cache/devops-track/`:** mirror provider tofu, venv ansible-core 2.21.5, khoá và tệp trạng thái node.
- **Image và volume:** `devops-track/act-runner:1.0-9d5fff50`, `devops-track/olist-shop:1.0`, các image ghim của bài; volume
  `devops-track-localstack-data`.
- **Không còn chạy gì:** không có cluster kind, không có `~/.kube`, không có container `devops-ex`. Container của người dùng
  (`de-learning-*`, `fnb-*`, `neo4j-fnb`, `portainer`) không bị đụng.
