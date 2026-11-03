# MLOps track Phase 4: module 14–18 + capstone m14–m18 (tầng senior) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn tất track MLOps: tầng senior gồm K8s cho ML production, distributed training, streaming/real-time ML, nền tảng nhiều đội và bảo mật model, system design và dẫn dắt vận hành; capstone m14–m18.

**Architecture:** Giữ kiến trúc Giai đoạn 1–3. Cluster kind `mlops` dùng chung được **mở rộng** bằng add-on senior (metrics-server, KEDA, Kueue) cài qua `setup/mlops/kind/up.sh --senior` (idempotent, không bắt buộc cho module 13). Kafka thêm vào `setup/mlops/compose.yaml` dưới profile `streaming`. Distributed training thực hành bằng nhiều tiến trình CPU (torchrun gloo, Ray local nhiều worker). Bảo mật model chạy offline hoàn toàn (ký bằng khoá sinh trong test, không cần Sigstore mạng).

**Tech Stack:** Python 3.12, uv, pytest; torch 2.14.1 CPU (đã có); **mới (builder kiểm phiên bản ≥2 tuần tuổi, tức phát hành ≤ 2026-10-21, và import được dưới pin hiện tại trước khi thêm):** KEDA, Kueue, metrics-server (manifest ghim sha256 trong `versions.env`), Kafka (image `apache/kafka`, KRaft 1 node, ghim digest), client Kafka Python, `ray[train,tune]`, `river`, `copier`, `modelscan`, `model-signing`, công cụ SBOM (vd. `cyclonedx-bom`); Triton Inference Server (xem Ruling 1).

**Spec:** `docs/superpowers/specs/2026-11-03-mlops-track-design.md` (mục 1 tầng senior, mục 3, 4.1 hàng 14–18, mục 5, mục 7 m14–m18, mục 9 điểm 11–12). Plan trước: `…-phase1.md`, `…-phase2.md`, `…-phase3.md` — **mọi Global Constraints của ba plan đó vẫn áp dụng**.

## Global Constraints

- Toàn bộ Global Constraints của plan Giai đoạn 1, 2, 3.
- **Bài học Giai đoạn 1–3 (bắt buộc trong mọi brief):** quote `text` trong quiz YAML; mọi luật test ép phải nói trong README/milestone doc; bài sự cố: README chỉ triệu chứng **và tên hàm/tham số/cột/nhãn trong starter không gợi ý nguyên nhân**; không docker/kubectl trần trong test (chỉ qua `mlopskit`); `leftovers(needle)` có needle riêng; không bao giờ dọn tài nguyên theo nhãn chung; ngưỡng thời gian dư 2× khi máy tải nặng; chấm bằng tool thật, không mô phỏng; kiểm dependency mới import được dưới pin hiện tại; khi nới test cho công bằng thì giữ kiểm độc lập và mutation-test bộ chấm; review cả diff của vòng sửa; test không để lộ đáp án qua tên nhãn/thông báo lỗi.
- **Review sau mỗi phần việc (người học yêu cầu):** reviewer task + `/code-review` trên diff task + security reviewer (subagent, vì skill `security-review` chỉ chạy trên cwd) khi diff chạm script/RBAC/secret/container/mạng/ký khoá; cuối nhánh `mattpocock-skills:code-review` (Standards + Spec).
- **Tài nguyên cluster-scoped** (ClusterQueue, ResourceFlavor, PriorityClass, WorkloadPriorityClass, ScaledObject là namespaced nhưng TriggerAuthentication cluster…): test tạo thì tên có hậu tố `<uuid8>` của run, nhãn `mlops-ex-run=<uuid8>`, xoá trong `finally` qua helper; `leftovers()` liệt kê cả loại này. Không test nào sửa node dùng chung trừ extended resource giả có tên riêng theo run và được gỡ trong `finally`.
- **Tầng senior nói thẳng:** README track và module 14–18 ghi rõ kiến thức senior không thay kinh nghiệm production; multi-GPU, MIG, nhiều node thật chỉ ở mức khái niệm/đo/mô phỏng.
- **Ngân sách:** mỗi bài ≤5 phút CPU trên laptop (không kể kéo image/tải dữ liệu lần đầu); add-on senior cộng thêm ≤1,5 GB RAM cho cluster khi rảnh (đo và ghi vào `setup/mlops/kind/README.md`).
- **Phần ôn** (Kafka từ DE 07, RBAC/NetworkPolicy/Helm từ DevOps 10–12, OTel/LLM từ AE 20): tối đa một `## ` mỗi phần, có link về module gốc.

## Rulings (đã quyết trước khi chạy)

1. **Triton:** image NGC `tritonserver` rất nặng (nhiều GB). Builder Task 1 đo kích thước image CPU nhỏ nhất ghim được. Nếu kéo + `kind load` ≤ 6 GB đĩa và ≤5 phút sau lần đầu → bài Triton dưới tải là bài thường có test, gate `require_image_cached`; nếu không → bài Triton có test gate thêm `MLOPS_TRITON=1` (mặc định skip, lý do ghi rõ) và bài load test bắt buộc chạy trên KServe custom predictor. Ghi quyết định vào `CONTENT_SPEC.md` mục Track MLOps.
2. **Autoscale:** thực hành bằng **KEDA** (ScaledObject trên custom metric, scale-to-zero và cold start với Deployment). HPA custom metric qua prometheus-adapter và KServe Serverless (Knative) chỉ ở mức khái niệm vì cluster chạy RawDeployment.
3. **GPU scheduling** thực hành bằng extended resource giả trên node kind (tên riêng theo run) để thấy scheduler/Kueue xử lý `nvidia.com/gpu`-like quota; device plugin, time-slicing, MIG ở mức khái niệm.
4. **Phụ thuộc Python:** thứ tự như spec mục 3 — vào môi trường mặc định nếu tương thích; nếu không thì container trong stack `setup/mlops` gọi qua helper (như Feast/Evidently); không hạ pin.
5. **Ký model:** `model-signing` với cặp khoá sinh trong test (không Sigstore OIDC/mạng); Sigstore keyless chỉ là hướng dẫn tuỳ chọn.

## Review Focus

1. **Add-on senior chưa cài** (cluster có nhưng thiếu KEDA/Kueue) → test skip với lệnh `bash setup/mlops/kind/up.sh --senior`, không ERROR. Test: Task 1 `test_require_senior_addons_skips`.
2. **Tài nguyên cluster-scoped sót** (ClusterQueue, PriorityClass, extended resource trên node) sau test lỗi → helper xoá trong `finally`; `leftovers` thấy được. Test: Task 1 `test_cluster_scoped_removed_on_error`.
3. **Worker distributed chết/treo** → bài torchrun/Ray có timeout cứng, dọn tiến trình con (không để process mồ côi giữ cổng gloo); test kill worker giữa chừng rồi resume từ checkpoint. Test ở Task 3 và Task 7.
4. **Stream đến trễ/không theo thứ tự, trùng lặp** → bài window feature xử lý event-time + watermark, test có sự kiện trễ và trùng; freshness đo theo event time chứ không phải lúc xử lý. Test ở Task 4 và Task 8.
5. **Model độc hại/bị sửa sau khi ký** → cổng deploy chặn pickle có payload (modelscan thấy) và chặn file sửa sau khi ký (verify fail); test dùng pickle độc hại vô hại hoá (gọi hàm ghi file đánh dấu trong `tmp_path`, không bao giờ chạy lệnh hệ thống). Test ở Task 5 và Task 8.

---

### Task 1: Hạ tầng Giai đoạn 4 (add-on senior cho kind, Kafka, dependency, helper)

**Files:**
- Modify: `setup/mlops/kind/{up.sh,versions.env,README.md}` (thêm cờ `--senior`, manifest add-on ghim sha256), `setup/mlops/compose.yaml` (service `kafka` profile `streaming`, cổng 2xxxx bind `127.0.0.1`, healthcheck), `setup/.env.example` (thêm dòng cuối), `pyproject.toml` + `uv.lock` (dependency mới qua group trong `default-groups` nếu tương thích), `mlopskit.py`, `tests/test_mlopskit.py`, `tests/test_mlops_setup.py`, `CONTENT_SPEC.md` (chỉ mục `## Track MLOps`).

**Interfaces:**
- `up.sh --senior`: như hiện tại rồi cài metrics-server, KEDA, Kueue (ghim bản + sha256 + ngày trong `versions.env`), chờ Ready; không đổi current-context; idempotent. Ghi thời gian chạy và RAM tăng thêm.
- `mlopskit.require_senior_addons() -> None` (gọi `require_kind`; skip nếu thiếu CRD `scaledobjects.keda.sh` hoặc `clusterqueues.kueue.x-k8s.io`, message chứa `up.sh --senior`).
- `mlopskit.cluster_scoped(manifest: str) -> ContextManager[list[str]]` (apply manifest cluster-scoped, ép nhãn `mlops-ex-run=<uuid8>`, xoá trong `finally`); `mlopskit.fake_extended_resource(name_suffix: str, quantity: int) -> ContextManager[str]` (patch capacity node bằng tên `mlops.example/gpu-<uuid8>`, gỡ trong `finally`, trả tên resource).
- `mlopskit.require_kafka() -> str` (skip nếu profile `streaming` chưa bật, trả bootstrap `127.0.0.1:<port>`); `mlopskit.kafka_topic() -> ContextManager[str]` (topic `mlops-ex-<uuid8>`, xoá trong `finally`).
- Nếu Ray/River/modelscan/copier không vào được env mặc định: helper chạy trong container tương ứng (`ray_python`, …) theo mẫu `evidently_python`; ghi kết quả kiểm vào `CONTENT_SPEC.md`.
- `leftovers()` liệt kê thêm: cluster-scoped có nhãn `mlops-ex-run`, extended resource `mlops.example/*` trên node, topic `mlops-ex-*`.

- [ ] **Step 1: Test thất bại**: `test_require_senior_addons_skips`, `test_cluster_scoped_removed_on_error`, `test_fake_extended_resource_removed_on_error`, `test_kafka_roundtrip` (stack thật: tạo topic → produce → consume → xoá), `test_senior_addons_installed` (CRD KEDA + Kueue, metrics-server trả `kubectl top node`), `test_versions_env_dates` (mọi ngày ≤ 2026-10-21), `test_new_deps_import` (mỗi dependency mới import được trong env mặc định hoặc helper container chạy được).
- [ ] **Step 2:** chạy → FAIL.
- [ ] **Step 3:** viết setup + helper; chạy `up.sh --senior` và `docker compose --profile streaming up -d --wait` thật; đo Triton theo Ruling 1.
- [ ] **Step 4:** test → PASS; `uv run pytest tests -q` tăng đúng số test mới; DE/DS/DA/AE không đổi; nếu đổi `uv.lock` gốc thì chạy lại các track bị ảnh hưởng.
- [ ] **Step 5: Commit** — `MLOps: hạ tầng Giai đoạn 4 (add-on senior kind, Kafka, dependency, helper)`

### Task 2–6: Module 14–18

Quy trình giống các module Giai đoạn 1–3 (5–8 `## `, ≥2 mermaid, `interview.md` ≥12 câu có câu sự cố/chọn công cụ/system design, quiz, khoảng 7 bài: 3 Basic, 2–3 Intermediate, 2 Advanced chỉ `SOLUTION.md`; ≥1 bài sự cố; `## 0. Cài đặt` nếu dùng công cụ lần đầu; phần đầu module nhắc tầng senior là kiến thức, không thay kinh nghiệm).

| Task | Module | Trọng tâm lý thuyết | Bài bắt buộc (ngoài bài builder tự chọn) | Chấm bằng |
| --- | --- | --- | --- | --- |
| 2 | `14-kubernetes-ml-production` | Autoscaling inference (HPA resource vs custom metric, KEDA, scale-to-zero, cold start và cách giảm); Triton trên K8s (model repository, dynamic batching, instance group) dưới tải; GPU scheduling (device plugin, extended resource, time-slicing, MIG khái niệm); hàng đợi batch job bằng **Kueue** (ResourceFlavor, ClusterQueue, LocalQueue, admission, borrowing); multi-tenant (namespace, ResourceQuota, LimitRange, PriorityClass, preemption); **một** phần ôn RBAC/NetworkPolicy/Helm trỏ DevOps 10–12 | ScaledObject KEDA trên custom metric của service (test: tạo tải → replica tăng, hết tải → giảm/về 0; đo cold start); Kueue: 2 LocalQueue chia quota, job vượt quota bị giữ `Pending` rồi được admit khi chỗ trống (test trạng thái Workload thật); PriorityClass + preemption (job ưu tiên cao đẩy job thấp); ResourceQuota tách serving/training; Triton (theo Ruling 1) hoặc KServe dưới tải với k6 — báo p95/throughput theo số replica; **bài sự cố**: job huấn luyện "kẹt mãi" không chạy dù cluster rảnh (nguyên nhân chỉ ở solutions, vd. request vượt flavor/quota) — đề chỉ tả triệu chứng; Advanced: thiết kế multi-tenant cho 3 đội có GPU chung (rubric), kế hoạch giảm cold start (rubric) | `require_senior_addons`, `k8s_namespace`, `cluster_scoped`, `fake_extended_resource`, `wait_for`, `port_forward`, `k6_run` |
| 3 | `15-distributed-training` | Data parallel vs model parallel vs pipeline; DDP (all-reduce, gradient bucket), FSDP, ZeRO ở mức hiểu và **đo** (bộ nhớ/tham số theo rank); torchrun (rendezvous, `LOCAL_RANK`, gloo trên CPU, elastic); **Ray** (task/actor, Ray Train, Ray Tune, scheduler ASHA); checkpoint và resume khi bị preempt (spot), idempotent; throughput data loading (num_workers, prefetch, bottleneck); ước tính chi phí GPU (giờ GPU, spot vs on-demand, hiệu suất scale); Horovod/DeepSpeed so sánh | Script DDP chạy `torchrun --nproc_per_node=2` trên CPU gloo: test loss giảm và tham số các rank trùng nhau sau mỗi bước; đo bộ nhớ/tham số DDP vs FSDP (CPU) — test kiểm FSDP chia tham số theo rank; checkpoint/resume: kill tiến trình giữa chừng → chạy lại tiếp từ checkpoint, kết quả bằng chạy liền (seed cố định); Ray Tune nhiều trial song song với early stopping, test số trial dừng sớm > 0 và best config hợp lệ; data loading benchmark tìm điểm nghẽn; ước tính chi phí từ bảng giá YAML (test số); **bài sự cố**: training nhiều tiến trình treo vô hạn ở bước đầu (nguyên nhân chỉ ở solutions, vd. rank không đồng bộ/ một rank bỏ qua collective) — đề chỉ tả triệu chứng; có timeout cứng; Advanced: kế hoạch scale training lên 8 GPU spot (rubric), so sánh DDP/FSDP/DeepSpeed cho model 7B (rubric) | `ex.module`, subprocess có timeout + dọn process group, Ray local |
| 4 | `16-streaming-realtime-ml` | **Một** phần ôn Kafka (link DE 07); event time vs processing time, cửa sổ (tumbling/sliding/session), watermark, dữ liệu trễ/trùng; feature real-time → **Feast push** vào online store; freshness và độ trễ end-to-end (đo đúng chỗ); online learning bằng **River** và khi nào không nên; feedback loop và thiên lệch do model tự gây; Flink/Spark Structured Streaming/Bytewax so sánh | Consumer tính feature cửa sổ 15 phút theo event time từ topic thật (`kafka_topic`), test có sự kiện trễ trong/ngoài watermark và trùng lặp; đẩy feature qua Feast push (container) và đọc online, test giá trị khớp tính batch trên cùng dữ liệu (không skew); đo freshness (event time → online store) theo p50/p95; River online model so với batch trên luồng có drift, test cả hai ca (online thắng khi drift, thua/ngang khi ổn định); mô phỏng feedback loop (model ảnh hưởng dữ liệu quan sát), test phát hiện thiên lệch; **bài sự cố**: feature online "đứng yên" dù topic vẫn có dữ liệu (nguyên nhân chỉ ở solutions, vd. watermark/timezone) — đề chỉ tả triệu chứng; Advanced: thiết kế pipeline fraud realtime <100 ms (rubric), runbook khi consumer lag tăng (rubric) | `require_kafka`, `kafka_topic`, `feast_python`, `ex.module` |
| 5 | `17-ml-platform-security` | Nền tảng cho nhiều đội: golden path, template dự án (**Copier**), self-service đăng ký/deploy model, chuẩn hoá registry (quy ước tên, tag bắt buộc); **FinOps cho ML** (cost attribution theo đội/model, showback/chargeback, chi phí idle); build vs buy (Databricks, SageMaker, Vertex vs open source); **supply chain của model**: rủi ro pickle, safetensors, quét model (**modelscan**), ký model (**model-signing**/model-transparency, Sigstore khái niệm), SBOM cho image/model, phân quyền registry | Template Copier sinh dự án model mới (test: `copier copy` với câu trả lời → dự án pass test của chính nó, có tag bắt buộc); cổng đăng ký kiểm quy ước (tag owner/team/cost-center, model card) — test bảng ca; quét: pickle độc hại vô hại hoá bị modelscan chặn, safetensors qua; ký + verify: file sửa sau ký → verify fail; cổng deploy gộp scan + verify; SBOM sinh cho môi trường serving, test có package ghim; cost attribution từ log sử dụng (YAML/CSV sinh trong test) theo đội/model, test số; **bài sự cố**: model "đã ký" vẫn bị thay mà cổng không chặn (nguyên nhân chỉ ở solutions, vd. verify sai đối tượng/bỏ qua lỗi) — đề chỉ tả triệu chứng; Advanced: thiết kế nền tảng cho 5 đội (rubric), đánh giá build vs buy (rubric) | `ex.module`, `mlflow_local`, `run_sandboxed` cho copier, tool thật |
| 6 | `18-senior-system-design` | SLO/SLI cho ML (latency, availability, **chất lượng**, **freshness**), error budget và burn rate nhiều cửa sổ; incident command (vai trò IC/comms/ops), dẫn postmortem không đổ lỗi; design review và design doc (mẫu, câu hỏi review); đánh đổi chi phí/độ trễ/chất lượng ở quy mô lớn (cache, distillation, batch vs realtime); khung trả lời ML system design; **bộ đề senior** (recommendation, fraud realtime, ETA, search ranking, LLM platform) có rubric | Tính SLI/error budget từ log sự kiện (sinh trong test), test số; alert burn rate nhiều cửa sổ viết bằng rule Prometheus, chấm bằng `promtool test rules` (ca bắn/không bắn); tính đánh đổi chi phí/độ trễ cho phương án cache/batch (test số); mô phỏng sự cố dựng sẵn (log + metric + timeline) → người học nộp `incident.yaml` (mốc thời gian, tác động, quyết định), test kiểm phần đo được; postmortem theo mẫu, test cấu trúc; **bài sự cố**: SLO "xanh" nhưng người dùng phàn nàn (nguyên nhân chỉ ở solutions, vd. SLI đo sai chỗ) — đề chỉ tả triệu chứng; Advanced: 5 đề system design có rubric chi tiết (≥2 bài Advanced, gộp đề hợp lý) | `ex.module`, `mlopskit.promtool` |

### Task 7: Capstone m14 và m15

**Files:** `tracks/mlops/capstone/milestones/m14-k8s-load.md`, `m15-ray-retrain.md`; `project/tests/test_m14.py`, `test_m15.py`; starter + lời giải trong `solutions/project/`; cập nhật `solutions/SOLUTION.md`.

**Interfaces:**
- m14: `project/k8s/` mở rộng m12: ScaledObject KEDA cho API ETA theo custom metric (giải thích chọn metric trong milestone doc), hai namespace serving/training có ResourceQuota, job retrain qua Kueue LocalQueue với PriorityClass thấp hơn serving. Test `test_m14_*`: tải bằng k6 → replica tăng và p95 trong ngưỡng ghi ở doc; job retrain vượt quota bị giữ rồi admit; quota serving không bị training ăn. Mỗi test trong namespace riêng.
- m15: `src/eta/distributed.py` (tên builder chốt): retrain ETA bằng Ray nhiều worker CPU (Ray Train hoặc Tune, builder chọn và ghi lý do vì GBDT), checkpoint định kỳ, `FailureConfig` để chịu worker bị kill. Test `test_m15_*`: chạy ≥2 worker ra model có metric ≥ ngưỡng baseline m04; kill một worker giữa chừng → vẫn hoàn tất và không train lại từ đầu (đếm epoch/iteration từ checkpoint); kết quả đăng ký MLflow có tag lineage như m04.

- [ ] Test trước → milestone docs → starter/lời giải → `SOLUTION=1` pass, starter fail không ERROR → commit `MLOps: capstone ETA m14 (K8s chịu tải) và m15 (Ray retrain)`.

### Task 8: Capstone m16 và m17

**Interfaces:**
- m16: `src/eta/streaming/`: replay trip 2019 (tháng mẫu từ `real_month`) vào topic Kafka theo đồng hồ mô phỏng (tăng tốc), consumer tính tốc độ trung bình theo zone 15 phút gần nhất (event time), push vào Feast online, API ETA đọc feature này. Test `test_m16_*`: feature online khớp tính batch trên cùng cửa sổ; freshness p95 ≤ ngưỡng ghi ở doc; sự kiện trễ quá watermark bị loại và đếm.
- m17: template Copier của nền tảng (`platform/template/`) onboard model thứ hai **dự đoán tip** trong ≤5 lệnh ghi ở doc; cổng deploy: scan (modelscan) + verify chữ ký + tag bắt buộc; báo cáo chi phí theo model (`reports/cost.md` + số trong YAML). Test `test_m17_*`: dự án sinh ra pass test của nó; model chưa ký hoặc bị sửa bị chặn; báo cáo chi phí tính lại khớp.

- [ ] Test trước → milestone docs → starter/lời giải → `SOLUTION=1` pass, starter fail không ERROR → commit `MLOps: capstone ETA m16 (feature streaming) và m17 (onboarding, ký, quét, chi phí)`.

### Task 9: Capstone m18 và validator

**Interfaces:**
- m18 (đánh giá độc lập senior): `docs/senior/design-doc.md` (nền tảng ETA nhiều thành phố), `reports/senior/slo.yaml` (SLI, mục tiêu, error budget, alert burn rate có `promtool test`), sự cố dựng sẵn (script sinh trong `solutions/`, starter nhận đầu ra qua `etakit`, milestone nói "đừng mở solutions") → `reports/senior/incident.yaml` + `docs/senior/postmortem.md`. Test `test_m18_*`: cấu trúc và phần đo được (số liệu tác động tính lại khớp, rule burn rate bắn đúng ca, mỗi mục bắt buộc của design doc có mặt), **chỉ báo số lượng** khi thiếu (không lộ đáp án); rubric trong `SOLUTION.md` cho phần lập luận.
- Validator: `test_phase4_present` (module 14–18, milestone m14–m18) trong `tests/test_mlops_track.py`.

- [ ] Test trước → milestone doc → starter/lời giải → `SOLUTION=1` pass → commit `MLOps: capstone ETA m18 (đánh giá senior) và validator Giai đoạn 4`.

### Task 10: Hoàn tất track, kiểm toàn nhánh và PR

- [ ] README track và capstone README cập nhật trạng thái đủ 19 module, 18 milestone; bảng đối chiếu roadmap còn đúng; `track.json` mô tả còn đúng.
- [ ] Như Task 7 Giai đoạn 3: regression từng track (DE/DS/DA/AE giống `main`); `SOLUTION=1` toàn track MLOps với stack + profile (`monitoring`, `feast`, `streaming`) + cluster kind có `--senior`; app test/typecheck/build; `mattpocock-skills:code-review` toàn nhánh từ `main`; dọn (`leftovers()` rỗng, tắt profile, dừng node kind); merge `origin/main`; push; PR mới.

## Thứ tự và song song

- Task 6 (module 18) không cần hạ tầng mới → chạy ngay, song song Task 1.
- Task 1 trước Task 2, 3, 4, 5 (phần dependency/cluster/Kafka). Sau Task 1: Task 2, 3, 4, 5 song song (worktree riêng mỗi task).
- Task 7 sau Task 2 và 3; Task 8 sau Task 4 và 5; Task 9 sau Task 6. Task 10 cuối.
