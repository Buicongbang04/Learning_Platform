# Bàn giao: track DevOps (tổng kết sau Phase 3)

Ngày: 2026-11-11. Track DevOps đã đủ nội dung theo spec, không còn phase nào sau. Tài liệu này dành cho người bảo trì track
(sửa bài, nâng phiên bản, chạy lại kiểm chứng). Đọc hết trước khi sửa phần dùng chung.

## 1. Track có gì

- **17 module (00–16), 134 bài** (spec mục 3 nhắm khoảng 120). Mỗi module có lý thuyết 5–8 phần với ít nhất 2 mermaid và bảng so
  sánh công cụ, `interview.md` ít nhất 12 câu, 7–9 bài (ít nhất 3 Basic, 2 Advanced). Từ module 04 mỗi module có ít nhất một bài sự
  cố cố ý (đề chỉ tả triệu chứng, nguyên nhân trong `solutions/`); từ module 12 mỗi module có ít nhất một bài Advanced là postmortem
  hoặc runbook chấm rubric.
- **Capstone 9 milestone (m01–m09)** đưa Olist Shop (`tracks/devops/sample-app/`) lên "production" trên máy local: script vận hành,
  Nginx, container, CI/CD bằng act, OpenTofu + Ansible, Helm trên kind, GitOps + SOPS, observability, rồi m09 là đánh giá độc lập
  (SLO, burn-rate alert, runbook, game day với lỗi bơm theo seed, postmortem chấm rubric).
- **Ba đợt:**
  - Phase 1 (PR #10): module 00–05, m01–m02, hạ tầng nền (`run_sandboxed`, `GitRepo`, `DockerLab`).
  - Phase 2: module 06–11, m03–m06; `act_run`, `TofuLab`, `AnsibleLab`, `KubeLab`; cluster `devops-lab`, Gateway API + Traefik,
    metrics-server; registry và `localstack-devops`.
  - Phase 3 (nhánh `devops-phase3`): module 12–16, m07–m09; SOPS/age, Vault dev, ArgoCD + git server trong cluster, `ObsStack`
    (OTel Collector, Jaeger, Loki, Prometheus, Alertmanager, Grafana), `promtool`/`amtool`, `LambdaLab`, Linkerd, `FaultInjector`,
    `k6_run`; Olist Shop xuất trace và log OTLP khi có `OTEL_EXPORTER_OTLP_ENDPOINT`.
- **Validator** `tests/test_devops_track.py`: đủ 17 module và 9 milestone (kèm `capstone/project/tests/test_mNN.py`), quy mô từng
  module, frontmatter và heading của bài, lời giải trùng tên starter, tổng số bài khớp con số trong README gốc và README track, công
  cụ chỉ gọi qua helper (cấm `docker`, `kind`, `act`, `kubectl`, `helm`, `tofu`, `sops`, `age`, `vault`, `argocd`, `linkerd`,
  `promtool`, `amtool`, `aws`, `awslocal`, `tc`, `k6` trần), marker `kube_nodes`, không `curl | sudo sh`.

## 2. Tài liệu gốc

- Spec: `docs/superpowers/specs/2026-11-01-devops-track-design.md`
- Plan: `docs/superpowers/plans/2026-11-01-devops-phase1.md`, `2026-11-01-devops-phase2.md`, `2026-11-10-devops-phase3.md`
- Quy ước (bắt buộc đọc trước khi sửa): mục "Track DevOps" trong `CONTENT_SPEC.md` (bảng helper, ranh giới Kubernetes, ArgoCD,
  Linkerd, observability, LambdaLab, FaultInjector)
- Cài công cụ và thành phần admin: `setup/DEVOPS-TOOLS.md`. Không có script cài: mỗi module có `## 0. Cài đặt` từng bước, theo quyết
  định của người dùng.

## 3. Quyết định quan trọng

Mỗi dòng ghi giá phải trả nếu sai. Quyết định của Phase 1 nằm trong `CONTENT_SPEC.md`.

### Phase 2

1. **Validator cấm gọi công cụ trần** trong test module và capstone; chỉ qua helper. Sai thì phải nới danh sách.
2. **Cài công cụ trước module:** helper cần công cụ trước khi module dạy cài thì builder cài bản ghim vào `~/.local/bin`; `## 0. Cài
   đặt` dùng đúng bản đó.
3. **Compose của người học** kiểm theo allowlist khoá; volume/network có `name:` phải bắt đầu bằng `devops-ex-<id>`.
4. **`act_run`:** đổi tên workflow thành `devops-ex-<id>-…`; bước build/push thật có `if: ${{ !env.ACT }}`, harness tự build/push
   bằng `DockerLab`; luôn có `GITHUB_TOKEN` giả và shim `gh` đầu PATH (act 0.2.94 gọi `gh auth token` và từng làm lộ token thật).
5. **Runner act** `devops-track/act-runner:1.0-<hash>` build một lần, giữ lại có chủ đích.
6. **OpenTofu 1.13.2**, `hashicorp/aws` 6.12.0 (giới hạn của LocalStack 4.4.0), provider chỉ từ mirror, egress qua proxy chết.
7. **Ansible** chỉ chạy trong sandbox (`AnsibleLab`), target là container sshd.
8. **Kubernetes:** kind `devops-lab`, `kindest/node:v1.34.0` ghim digest, 1 control plane + 2 worker; kubeconfig admin chỉ ở
   `~/.kube/devops-lab.yaml`; người học dùng token ServiceAccount với Role riêng; Pod Security baseline/restricted.
9. **Việc admin trên đầu vào của người học** chỉ qua `admin_local_pv` và `node_action` (khoá flock, tệp trạng thái, tự hoàn tác sau
   SIGKILL). Restore etcd và nâng cấp kubeadm là lab tay chấm rubric.
10. **Thành phần admin cài một lần từ `setup/kind/`**, test chỉ gọi `require_*()` và skip kèm đúng lệnh.

### Phase 3

11. **`DockerLab.close()` xoá cả volume ẩn danh** (`rm -f -v` rồi `volume rm`): Phase 2 đã để lại 14 volume. Đổi hành vi
    `DockerLab` nên test helper MLOps và FDE được chạy lại lúc đó.
12. **SOPS + age:** `sops_env`/`age_keypair` dựng env từ đầu, khoá luôn nằm ngoài project của người học. age không có tệp checksum
    chính thức, nên module 12 ghim hash lấy từ digest asset trên GitHub. Sandbox che thêm `~/.gnupg`, `~/.config/sops`,
    `~/.vault-token` (ảnh hưởng mọi track dùng `run_sandboxed`; test MLOps/FDE vẫn xanh).
13. **Vault dev** là service compose `vault-devops` (image ghim digest, token cố định cho lab, không bí mật); `vault_env` không mang
    `VAULT_*` của máy, `HOME` không phải thư mục project (tránh ghi `.vault-token` vào đó).
14. **ArgoCD v3.5.6 bản core** (không API server, UI, Dex), Application trong namespace của lab, sync bằng impersonation với
    `devops-ex-learner` của lab (RBAC, VAP, Pod Security của lab vẫn áp). AppProject riêng mỗi lab; `default` khoá trống.
    - SOPS bằng sidecar CMP `sops-kustomize`, không ksops (ksops cần `--enable-exec`, repo nào cũng chạy được chương trình cạnh khoá).
    - Git server là `git daemon` chỉ đọc dùng lại image ArgoCD; testkit đẩy repo bằng quyền admin (bundle).
    - Repo-server không ra ngoài cluster (NetworkPolicy egress + proxy chết + tắt giao thức git ở sidecar).
    - ArgoCD 3.5.6 không đối chiếu `operation.sync.source` với project (đã tái hiện thật), nên VAP `-argocd` của lab là rào duy
      nhất: từ chối `operation.sync.*` và mọi lần ghi `status`.
    - Capstone m07 dùng Application multi-source (`ref: values` + chart) vì sidecar không có Helm có chủ đích.
15. **Observability bằng compose, không trong cluster:** `ObsStack` dựng stack riêng mỗi lần chạy qua `DockerLab.compose`, ghim digest,
    `OBS_MEMORY` 512m mỗi container. Collector đặt `spanmetrics.metrics_flush_interval: 5s` để Prometheus thấy kịp. `promtool`/`amtool`
    chạy trong image Prometheus/Alertmanager. Olist Shop giữ tag `1.0` khi thêm OTel (tag `1.1` đã mang nghĩa "bản mới" trong bài).
16. **Lambda local bằng RIE** (`LambdaLab`): container `--read-only`, không socket Docker, credential giả, endpoint ép về
    `localstack-devops` qua bộ chuyển tiếp TCP trong tiến trình pytest, proxy chết cho mọi thứ khác; chỉ thư viện có sẵn trong image.
    LocalStack 4.4.0 không chạy Lambda (không socket), API Gateway chỉ REST v1. Network lab `--internal` mặc định.
17. **Linkerd edge-26.10.1** render bằng `helm template` (không Secret trong repo), linkerd-cni thay `linkerd-init` (Pod Security
    baseline), không viz (`mesh_status` đọc cổng admin 4191 qua API server), chứng chỉ do admin sinh bằng `certs.sh` và khoá trust
    anchor bị xoá ngay. VAP `-mesh` chặn mọi tham chiếu ra ngoài namespace của lab.
18. **`FaultInjector`** chỉ bơm lỗi vào container hay pod có tên và nhãn của lab (kiểm lại bằng `docker inspect` trước mỗi lệnh);
    `tc` chạy trong container phụ `devops-track/netem:1.0` với `--network container:<id>`, không bao giờ thêm NET_ADMIN cho container
    của bài; trên Kube chỉ dùng token của lab, không `net-delay`. Chọn lỗi bằng `random.Random(seed)` trên danh sách cố định.
19. **m09** chấm phần chấm được (SLO, burn-rate rule qua `promtool` với kịch bản ẩn sinh theo budget của người học, runbook, game day
    theo seed) và để postmortem cho rubric. Mã lỗi chỉ in sau khi mọi assert đã pass.
20. **Mọi module từ 12** có ít nhất một bài Advanced là postmortem hoặc runbook chấm rubric; giá cloud trong bài là ước tính tháng
    11/2026, có chữ "khoảng" và nhắc kiểm lại.

## 4. Kiểm chứng cuối cùng (Task 12, 2026-11-11)

Chi tiết từng đợt ở `.superpowers/sdd/2026-11-10-devops-phase3/task-12-report.md`.

- `uv run pytest tests -q` (toàn repo, ghim CPU): 2069 passed, 72 skipped khi chưa bật dịch vụ và cluster; 2108 passed, 33 skipped
  khi đã bật `devops-lab` đủ thành phần và các service profile `devops`. 33 skip còn lại đều ngoài track DevOps (BI, FDE cần KVM, MLOps
  cần cluster `mlops` hay stack riêng, bộ nyc-tlc) trừ ba proof opt-in (`DEVOPS_ACT_OFFLINE_PROOF`, `DEVOPS_TOFU_FETCH_PROOF`,
  `DEVOPS_KIND_STOP_PROOF`).
- `SOLUTION=1 uv run pytest tracks/devops -q -rs` theo từng đợt, `devops-lab` tạo mới theo `setup/DEVOPS-TOOLS.md` (image gồm
  `olist-shop:1.1`, Gateway API + Traefik, metrics-server, ArgoCD + khoá age, Linkerd): **1424 passed, 47 skipped, 0 failed** sau một
  lần sửa test chập chờn ở module 12 Intermediate 02 (`2895055c`). 47 skip đều đúng thiết kế: 46 bài Advanced chỉ có `SOLUTION.md`
  chấm rubric, 1 test tích hợp tuỳ chọn của m01 (`DEVOPS_CAPSTONE_INTEGRATION=1`).
- Starter (không `SOLUTION`): 1104 failed, 366 passed, 1 skipped, **0 error**. Test pass trên starter là test tự kiểm bộ chấm trên
  fixture, ca đối chứng hay hồi quy cố ý.
- `test_act_run_cleans_containers`, `test_act_run_concurrent_runs_of_same_workflow` (từng fail khi máy chạy capstone song song) và
  `test_fault_injector_kube_real` pass hai lần liền trên máy rảnh, cluster bật.
- App: `pnpm test` 35 pass, `pnpm typecheck` sạch, `pnpm build` thành công.

## 5. Giới hạn đã biết và phần chưa kiểm

- **Chưa kiểm trên máy:**
  - Module 11: lab kubeadm (`devops-ts`, Multipass) và cài chart `podinfo` 6.7.1.
  - Action `aquasecurity/trivy-action` trong workflow tham chiếu m04 (bị bỏ qua khi chạy dưới act).
  - kind 0.33 (bản MLOps cài) với `devops-lab`; track kiểm trên kind 0.30.0.
  - Hai ghi chú **chưa kiểm lại** trong `setup/DEVOPS-TOOLS.md` mục Linkerd: áp lại `setup/kind/linkerd` sau `certs.sh` (conflict
    `caBundle`) và kiểm chain CNI sau khi gỡ Linkerd.
  - Phần của Phase 1: gitleaks, `dig`, OpenSSL 1.1.1, OpenSSH 8.x.
  - Lab AWS thật (module 08, 14, m09 tuỳ chọn): chỉ có hướng dẫn, chi phí ước tính, budget alarm, lệnh dọn.
- **Giới hạn thiết kế:**
  - Manifest ArgoCD render (kể cả Secret đã giải mã, base64) nằm trong redis của namespace `argocd`.
  - Git server lưu repo trong `emptyDir`: pod git chạy lại là repo của lab đang chạy mất.
  - Mọi lab dùng chung một khoá age; ranh giới giữa các lab là AppProject.
  - Cổng admin 4191 của proxy Linkerd đọc được từ lab khác (không có token).
  - LocalStack 4.4.0: `iam:SimulatePrincipalPolicy` sai, nên module 14 Basic 01 dùng parser tĩnh.
  - Game day (module 16, m09) có ngưỡng thời gian 90–120 giây; máy rất tải có thể chậm hơn.
  - Người học đặt `M09_SEED` rồi đọc testkit thì biết lỗi: tự giác, ghi rõ trong luật chơi.

## 6. Binary dùng chung với track MLOps

| Binary | DevOps | MLOps |
| --- | --- | --- |
| act | 0.2.94 | 0.2.94 |
| kind | 0.30.0 | 0.33.0 |
| kubectl | 1.34.13 | 1.35.8 |

Ghi trong `setup/DEVOPS-TOOLS.md`. Không hạ bản mà track kia cần.

## 7. Công cụ và tài nguyên để lại trên máy

- **`~/.local/bin`:** shellcheck, act 0.2.94, actionlint, trivy 0.76.1, tofu 1.13.2, ansible-core 2.21.5 (symlink tới venv), kind,
  kubectl, helm 3.22.1, sops 3.13.3, age 1.3.2, vault 2.2.1, argocd 3.5.6, linkerd edge-26.10.1, logcli 3.7.9, AWS CLI 2.38.6.
- **`~/.cache/devops-track/`:** mirror provider tofu, venv ansible, DB trivy, cache act, khoá và tệp trạng thái node.
- **Image Docker** (giữ để chạy lại không cần mạng): `devops-track/act-runner:1.0-a5037b3b`, `devops-track/olist-shop:1.0` và
  `:1.1`, `devops-track/netem:1.0`, image ghim của ArgoCD, Linkerd, Traefik, metrics-server, stack observability, Lambda, k6,
  Vault, LocalStack, registry, Mailpit, `kindest/node`.
- **Volume:** `devops-track-localstack-data`, `act-toolcache` (dùng chung, không xoá).
- **Không còn chạy gì:** không có cluster kind, không có `~/.kube`, các service profile `devops` đã dừng và xoá container (giữ
  volume có tên), không còn container, network hay volume `devops-ex`. Mạng Docker `kind` (dùng chung với MLOps) để nguyên.

## 8. Việc có thể làm tiếp

- Kiểm các mục "chưa kiểm" ở mục 5 khi có máy phù hợp (kubeadm trên VM, kind 0.33, podinfo, trivy-action).
- Nâng phiên bản định kỳ (ArgoCD 3.6, Linkerd edge mới, LocalStack) theo quy tắc "phát hành ít nhất 2 tuần", cập nhật bảng trong
  module và `setup/DEVOPS-TOOLS.md`, chạy lại `SOLUTION=1` của phần liên quan.
- Có thể thêm `VAULT_CLI_MIN_VERSION` vào testkit (hiện là hằng cục bộ trong test module 12) và `tcp_open_total` vào
  `mesh_status["clients"]` nếu bài sau cần chấm kết nối TCP opaque.
- `test_m07` import helper từ `test_m06`; sửa các hàm đó ở m06 phải chạy lại cả m07.
