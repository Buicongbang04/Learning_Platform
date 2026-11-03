# MLOps track Phase 3: module 11–13 + capstone m11–m13 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn tất lõi junior của track: deploy model DL (SegFormer, ONNX, CPU/GPU), governance và cloud (lab tuỳ chọn), Kubernetes cho ML (kind, KServe, Argo Workflows) và capstone m11–m13.

**Architecture:** Giữ kiến trúc Giai đoạn 1–2. K8s chạy trên **một cluster kind dùng chung** tên `mlops`, dựng một lần bằng `setup/mlops/kind/up.sh` (giống stack Compose); test gate bằng `mlopskit.require_kind()` và mỗi test làm việc trong namespace riêng do `mlopskit.k8s_namespace()` tạo và xoá. KServe cài ở chế độ **RawDeployment** (không Knative/Istio) để nhẹ. Đường GPU chạy qua project `setup/gpu` có sẵn (thêm `onnxruntime-gpu`), skip khi không có CUDA; mọi bài có đường CPU.

**Tech Stack:** Python 3.12, uv, pytest; torch 2.14.1 CPU, transformers 5.22, onnx 1.23.2, onnxruntime 1.31.0 (đã có trong env); **mới:** `kind` (bản ≥2 tuần, vd. v0.33.0), `kubectl` khớp node image, cert-manager, KServe, Argo Workflows (bản ổn định ≥2 tuần tuổi, builder kiểm ngày); `onnxruntime-gpu` trong `setup/gpu`.

**Spec:** `docs/superpowers/specs/2026-11-03-mlops-track-design.md` (mục 3, 4.1 hàng 11–13, mục 5, mục 7 m11–m13 và đoạn SegFormer). Plan trước: `docs/superpowers/plans/2026-11-03-mlops-phase1.md`, `…-phase2.md` — **mọi Global Constraints của hai plan đó vẫn áp dụng**.

## Global Constraints

- Toàn bộ Global Constraints của plan Giai đoạn 1 và 2.
- **Bài học Giai đoạn 1–2 (bắt buộc trong mọi brief):** quote `text` trong quiz YAML; mọi luật test ép phải nói trong README/milestone doc; bài sự cố: README chỉ triệu chứng **và tên hàm/tham số/cột trong starter không gợi ý nguyên nhân**; không docker/kubectl trần trong test (chỉ qua `mlopskit`); `leftovers(needle)` có needle riêng; không bao giờ dọn tài nguyên theo nhãn chung (agent song song giết nhau); ngưỡng thời gian có dư 2× khi máy tải nặng; chấm bằng tool thật (kubectl, onnxruntime), không mô phỏng; kiểm dependency mới import được dưới pin hiện tại trước khi thêm.
- **K8s:** một cluster `mlops` duy nhất, context `kind-mlops`; test không tạo/xoá cluster. Namespace test tên `mlops-ex-<uuid8>`, nhãn `mlops-ex=1` và `mlops-ex-run=<uuid8>`, xoá trong `finally` (chỉ namespace của chính nó). Image tự build nạp vào cluster bằng `mlopskit.kind_load`. Cổng host từ cluster bind `127.0.0.1`, dải 2xxxx, override qua `setup/.env` (`MLOPS_KIND_HTTP_PORT=28081`, `MLOPS_KIND_HTTPS_PORT=28444`; builder kiểm `ss -ltn`).
- Module 13 có bảng "kế thừa từ track DevOps" (DevOps 10–12): phần K8s chung (RBAC, NetworkPolicy, Helm, vận hành cluster) **chỉ trỏ về**, không dạy lại.
- **GPU:** test GPU chạy trong `setup/gpu` qua helper, skip `"Không có CUDA"` khi không có GPU; bài nào cũng pass được bằng đường CPU. Bộ nhớ GPU giả định 4 GB (RTX 3050 Laptop). Docker trên máy **không** có NVIDIA runtime: không có bài bắt buộc GPU trong container.
- **SegFormer:** test dùng model tí hon sinh trong test (vài lớp conv, export ONNX); script fine-tune `segformer-b0` (checkpoint công khai HF, không gated) là **bước chuẩn bị** người học chạy một lần, không phải test. Không host artifact.
- **Cloud (module 12, m11):** không test nào cần tài khoản/khoá/mạng cloud. Lab cloud chỉ là hướng dẫn tuỳ chọn có free tier, budget alarm, lệnh dọn; phần chấm được là phần chạy local (plan/dry-run, script dọn kiểm bằng giả lập hoặc kiểm tĩnh có lý do ghi rõ).

## Review Focus

1. **Cluster chưa dựng / thiếu kind, kubectl** → test K8s skip với lệnh `bash setup/mlops/kind/up.sh` và trỏ mục `## 0` module 13; không ERROR. Test: Task 1 `test_require_kind_skips_without_cluster`.
2. **Namespace/tài nguyên sót sau test bị ngắt** → helper xoá đúng namespace của mình trong `finally`; `leftovers` thấy namespace `mlops-ex-*` còn sót. Test: Task 1 `test_k8s_namespace_removed_on_error`.
3. **Sai số sau export ONNX bị bỏ qua** → bài export phải so output PyTorch vs ONNX Runtime (mIoU/atol) và fail khi lệch; INT8 có ngưỡng giảm chất lượng ghi rõ. Test ở Task 2.
4. **OOM GPU 4 GB** → bài batch size/FP16 có đường CPU và đo bộ nhớ; bài sự cố OOM chỉ tả triệu chứng. Test ở Task 2 (GPU skip, CPU chạy).
5. **InferenceService “Ready” nhưng trả sai model/version** → test gọi HTTP thật vào service trong cluster và kiểm `model_version`, không chỉ kiểm trạng thái Ready. Test ở Task 4 và Task 6.

---

### Task 1: Hạ tầng Giai đoạn 3 (kind + KServe + Argo, helper K8s/GPU)

**Files:**
- Create: `setup/mlops/kind/{cluster.yaml,up.sh,down.sh,versions.env,README.md}`
- Modify: `mlopskit.py`, `tests/test_mlopskit.py`, `tests/test_mlops_setup.py`, `setup/.env.example` (thêm dòng cuối), `CONTENT_SPEC.md` (chỉ mục `## Track MLOps`), `setup/gpu/pyproject.toml` + `setup/gpu/uv.lock` (thêm `onnxruntime-gpu` khớp 1.31.x; kiểm torch/CUDA của env đó vẫn chạy, chạy `setup/gpu/check_gpu.py`)

**Interfaces:**
- `setup/mlops/kind/up.sh`: idempotent; kiểm checksum binary nếu tải (`kind`, `kubectl` vào `~/.local/bin`, giống cách cài `act`); tạo cluster `mlops` (1 node, node image ghim theo digest, `extraPortMappings` bind `127.0.0.1`); cài cert-manager, KServe (RawDeployment, ghim bản), Argo Workflows (namespace `argo`, ghim bản); chờ Ready. `down.sh` xoá cluster. `versions.env` ghi mọi phiên bản + ngày phát hành (≥2 tuần trước 2026-11-03).
- `mlopskit.KIND_CLUSTER = "mlops"`, `KUBE_CONTEXT = "kind-mlops"`; `require_kind() -> None` (skip nếu thiếu `kind`/`kubectl` hoặc cluster không có, message chứa `setup/mlops/kind/up.sh`); `kubectl(*args, namespace: str | None = None, input: str | None = None, timeout: int = 120) -> CompletedProcess` (luôn `--context kind-mlops`); `k8s_namespace() -> ContextManager[str]` (tạo `mlops-ex-<uuid8>` có nhãn, xoá `--wait=false` trong `finally`); `kind_load(tag: str) -> None`; `apply_manifest(path_or_text, namespace) -> CompletedProcess`; `wait_for(kind: str, name: str, condition: str, namespace: str, timeout: int) -> None` (`kubectl wait`, fail kèm `describe` + log khi quá hạn); `port_forward(namespace, target, port) -> ContextManager[int]` (cổng local tự do, dọn tiến trình); `leftovers()` liệt kê thêm namespace `mlops-ex-*`.
- `mlopskit.require_cuda() -> None` (skip `"Không có CUDA"`), `gpu_python(script: str, cwd: Path, timeout: int = 300) -> CompletedProcess` (chạy `uv run --project setup/gpu python -c script`, stdout JSON).

- [ ] **Step 1: Test thất bại**: `test_require_kind_skips_without_cluster` (giả lập thiếu binary/cluster → skip, message chứa `setup/mlops/kind/up.sh`), `test_k8s_namespace_removed_on_error`, `test_kubectl_uses_context` (giả lập subprocess, kiểm `--context kind-mlops`), `test_kind_roundtrip` (cluster thật: namespace → ConfigMap → get → xoá), `test_kserve_and_argo_installed` (CRD `inferenceservices.serving.kserve.io` và `workflows.argoproj.io` tồn tại), `test_gpu_python_skip_or_run` (có CUDA → `onnxruntime` thấy `CUDAExecutionProvider`; không → skip), `test_versions_env_dates` (mọi dòng có ngày ≤ 2026-10-20).
- [ ] **Step 2:** chạy → FAIL.
- [ ] **Step 3:** viết setup + helper, chạy `bash setup/mlops/kind/up.sh` thật trên máy (ghi thời gian, RAM cluster dùng), thêm `onnxruntime-gpu` vào `setup/gpu`.
- [ ] **Step 4:** test → PASS; `uv run pytest tests -q` tăng đúng số test mới; `uv.lock` gốc **không đổi**.
- [ ] **Step 5: Commit** — `MLOps: hạ tầng Giai đoạn 3 (kind + KServe + Argo, helper K8s/GPU)`

### Task 2–4: Module 11–13

Quy trình giống Task 5–9 Giai đoạn 1 / Task 2–7 Giai đoạn 2. Module 11 và 12 không cần Task 1 phần K8s (module 11 cần `require_cuda`/`gpu_python`; có thể bắt đầu song song với Task 1 nếu dùng đường CPU trước).

| Task | Module | Trọng tâm lý thuyết | Bài bắt buộc (ngoài bài builder tự chọn) | Chấm bằng |
| --- | --- | --- | --- | --- |
| 2 | `11-deep-learning-serving` | Khác biệt serving DL vs tabular (kích thước model, tiền xử lý ảnh, batch, GPU); **một** phần ôn ONNX (link AE/DS nơi đã dạy); export ONNX (opset, dynamic axes) và kiểm sai số; ONNX Runtime CPU vs CUDA (execution provider, đường fallback); dynamic batching (gom request theo thời gian/kích thước); benchmark throughput/latency đúng cách (warmup, p50/p95, batch); bộ nhớ GPU 4 GB (batch size, FP16, OOM, phân mảnh); quantization INT8 (dynamic/static, đánh đổi chất lượng); Triton/TensorRT so sánh; SAM 2 chỉ trong bảng (quá nặng); `## 0. Cài đặt` (`setup/gpu`, onnxruntime-gpu, script fine-tune `segformer-b0` chạy một lần trên Oxford Pets + trimap, đường CPU) | Export model seg tí hon (sinh trong test) ra ONNX với batch động, test so output PyTorch vs ORT (atol) và fail khi opset/axes sai; service FastAPI nhận ảnh trả mask (PNG) + `model_version`, validate kích thước ảnh; dynamic batcher (asyncio) gom ≤N request hoặc ≤T ms — test thông lượng tăng và mỗi request nhận đúng kết quả của mình; benchmark harness có warmup, báo p50/p95, throughput theo batch (test kiểm cấu trúc kết quả + warmup bị loại); INT8 dynamic quantization: kích thước giảm, IoU giảm ≤ ngưỡng ghi trong README; bài GPU (skip không CUDA) đo bộ nhớ theo batch size; **bài sự cố**: service DL chết sau vài request đồng thời trên GPU (OOM do batch không giới hạn) — có đường CPU tái hiện bằng giới hạn bộ nhớ giả lập/cấu hình, đề chỉ tả triệu chứng; notebook dữ liệu thật trên `oxford-pets` + `oxford-pets-trimaps` (bỏ tệp `._*.png`): phân phối kích thước ảnh/tỉ lệ lớp, quiz `data`; Advanced: service SegFormer portfolio có benchmark CPU/GPU (rubric) | `ex.module`, `mlopskit.gpu_python`/`require_cuda`, `ex.dataset`, `TestClient` |
| 3 | `12-ml-platform-governance` | Reproducibility audit (từ một model trong registry truy ngược code/data/env; checklist); model governance (approval, audit log, model card, quyền truy cập registry, tách quyền); chi phí ML (compute train vs serve, idle, ước tính); IaC cho ML ở mức đọc hiểu (**một** phần ôn, link DE `08-devops-for-data`); **Cloud ML services** SageMaker / Vertex AI / Azure ML so sánh (registry, endpoint, pipeline, giá); lab cloud tuỳ chọn (free tier, budget alarm, lệnh dọn, cảnh báo chi phí ẩn); data engineering cho ML ôn nhanh (Spark/Kafka/Flink trỏ về DE) | Reproducibility audit: cho một run MLflow (`mlflow_local`, sinh trong test) với tag thiếu/sai → hàm audit liệt kê thiếu gì (commit, data version, lockfile hash, seed) — test bảng ca; audit log append-only cho thao tác registry (ai, lúc nào, alias cũ→mới, lý do), test chống sửa log (hash chain) và truy vấn "ai đã promote v3"; ước tính chi phí từ bảng giá cho sẵn (YAML) cho kịch bản train/serve, test số; đọc IaC: cho Terraform mẫu, trả lời quiz `knowledge` (resource nào tốn tiền khi idle, lệnh dọn); **bài sự cố**: model trong production không tái lập được dù "đã log đủ" — đề chỉ tả triệu chứng (nguyên nhân chỉ trong solutions, vd. dependency không ghim); Advanced: thiết kế governance cho 3 đội (rubric), so sánh build vs cloud service cho một case (rubric) | `mlflow_local`, `ex.module`, quiz |
| 4 | `13-kubernetes-for-ml` | Bảng **kế thừa từ DevOps 10–12** (phần nào không dạy lại); kind cho dev local; chuyển service từ Compose sang K8s (Deployment, Service, ConfigMap/Secret, readiness/liveness/startup probe cho model nạp chậm, resources requests/limits cho ML); **KServe** InferenceService (predictor custom container vs runtime có sẵn, storageUri, RawDeployment vs Serverless, canary `canaryTrafficPercent`); **Argo Workflows** cho pipeline training (DAG, artifact, retry, parameters); Argo CD giới thiệu cho GitOps; GPU trên K8s ở mức khái niệm (device plugin, `nvidia.com/gpu`); `## 0. Cài đặt` (kind, kubectl, `setup/mlops/kind/up.sh`, gỡ) | Manifest Deployment + Service cho một service sklearn nhỏ (image `built_image` + `kind_load`): test apply, chờ Ready, `port_forward` gọi `/predict`; startupProbe đúng cho model nạp chậm (test: probe sai → pod restart; đúng → Ready); InferenceService custom predictor: Ready **và** HTTP trả đúng `model_version`; canary KServe 2 version (test tỉ lệ thô + rollback về 0%); Argo Workflow 3 bước (prepare → train → evaluate) với parameter và artifact, test workflow Succeeded và bước evaluate đọc đúng output; **bài sự cố**: pod model bị kill lặp lại ngay sau deploy (limits bộ nhớ thấp hơn lúc nạp model) — đề chỉ tả triệu chứng; Advanced: kế hoạch chuyển ETA từ Compose sang K8s (rubric), review manifest có lỗi (rubric) | `mlopskit.require_kind`, `k8s_namespace`, `kubectl`, `kind_load`, `wait_for`, `port_forward`, `built_image` |

### Task 5: Capstone m11 và m13

**Files:** `tracks/mlops/capstone/milestones/m11-cloud-optional.md`, `m13-junior-assessment.md` (tên theo `track.json`); `project/tests/test_m11.py`, `test_m13.py`; starter + lời giải; `solutions/SOLUTION.md`.

**Interfaces:**
- m11 (tuỳ chọn): `project/cloud/` gồm IaC đọc được (Terraform hoặc script CLI) đưa **một phần** (vd. artifact model lên object storage + endpoint nhỏ) lên free tier của **một** nhà cung cấp người học chọn; `project/cloud/teardown.sh` liệt kê và xoá đúng tài nguyên đã tạo (theo tag/prefix), có `--dry-run`; `project/cloud/budget.md` (ngưỡng, alarm). Test **không cần cloud**: kiểm `teardown.sh --dry-run` trên inventory giả (tệp JSON) in đúng danh sách theo tag và không xoá tài nguyên không có tag; kiểm mọi tài nguyên trong IaC có tag dự án; test cloud thật chỉ chạy khi `ETA_CLOUD_LIVE=1` (mặc định skip có lý do). Milestone ghi rõ là tuỳ chọn và cách bỏ qua không mất điểm phần lõi.
- m13 (đánh giá độc lập junior): bộ dữ liệu "tháng lạ" **sinh từ dữ liệu thật** bằng script cố định trong `solutions/` (vd. một tháng 2020 bị trộn lỗi thật: đổi đơn vị một cột, mất một zone, lệch múi giờ — builder chọn 2–3 lỗi, không ghi trong milestone doc) — người học chạy pipeline có sẵn (validate, replay, drift, quality), tự chẩn đoán và nộp `reports/assessment/diagnosis.yaml` (`findings: [{symptom, evidence, cause, action}]`, `decision`) + `docs/assessment.md`. Test: YAML hợp lệ, mỗi lỗi cài sẵn được phát hiện (khớp theo khoá `cause` trong tập nhãn cho phép, liệt kê trong doc mà không lộ đáp án), `evidence` khớp số tính lại; rubric trong `SOLUTION.md` cho phần lập luận. Script sinh tháng lạ nằm ở `solutions/` và starter chỉ nhận tệp đầu ra qua `etakit` (người học không đọc được cách sinh khi làm bài là điều không ép được — milestone nói rõ "đừng mở solutions").

- [ ] Test trước → milestone docs → starter/lời giải → `SOLUTION=1` pass, starter fail không ERROR → commit `MLOps: capstone ETA m11 (cloud tuỳ chọn) và m13 (đánh giá junior)`.

### Task 6: Capstone m12 (kind + KServe + Argo) và validator

Phụ thuộc Task 1 và nên sau Task 4 (dùng lại cách module 13 làm).

**Interfaces:**
- `project/k8s/`: manifest (hoặc kustomize) cho API ETA: Deployment/Service hoặc **InferenceService KServe custom predictor** dùng image `Dockerfile.serve` hiện có (nạp vào kind bằng `kind_load`), ConfigMap cấu hình, Secret `ETA_ADMIN_TOKEN`, probes (`/healthz` liveness, `/readyz` readiness), resources; model lấy từ MLflow của stack qua `host.docker.internal`/IP gateway hoặc model đóng gói sẵn — builder chọn, ghi lý do.
- `project/argo/train-workflow.yaml`: Workflow `validate → train → gate` dùng image `Dockerfile.train`, parameter tháng dữ liệu, artifact metric; `gate` exit 3 khi bị từ chối làm workflow Failed ở đúng bước.
- Test `test_m12_*`: InferenceService Ready + `/predict` trả `eta_s > 0` và `model_version` đúng; rollout version mới bằng canary rồi rollback; Workflow Succeeded với dữ liệu tí hon; gate từ chối → Failed ở bước `gate`.
- Validator: `test_phase3_present` (module 11–13, milestone m11–m13).

- [ ] Test trước → milestone doc `m12-kind-kserve.md` → starter/lời giải → `SOLUTION=1` pass (cluster đã dựng), starter fail không ERROR → commit `MLOps: capstone ETA m12 (kind, KServe, Argo Workflows)`.

### Task 7: Kiểm toàn nhánh và PR

- [ ] Như Task 10 Giai đoạn 2: regression từng track; `SOLUTION=1` toàn track MLOps với stack + profile + cluster kind bật; app test/typecheck/build; dọn (`leftovers()` rỗng, tắt profile; cluster kind giữ hay xoá thì ghi rõ trong báo cáo); rebase/merge `origin/main`; push; PR mới; rồi viết plan Giai đoạn 4.

## Thứ tự và song song

- Task 1 trước phần K8s. Task 2 (module 11) và Task 3 (module 12) không cần K8s → chạy song song với Task 1 ngay. Task 5 (m11, m13) không cần K8s → song song.
- Task 4 (module 13) và Task 6 (m12) sau Task 1; Task 6 sau Task 4 nếu được, hoặc song song nếu Task 4 đã chốt cách dùng helper.
