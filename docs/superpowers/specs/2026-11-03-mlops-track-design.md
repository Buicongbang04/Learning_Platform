# Thiết kế: track MLOps

Ngày: 2026-11-03. Nguồn: [roadmap.sh/mlops](https://roadmap.sh/mlops) (bản PDF ở `roadmap/mlops.pdf`).

## 1. Mục đích và lý do

Người học đã làm tốt phần **xây** model (track AI & Data Scientist, AI Engineer) nhưng thường dừng ở
notebook. Track này lấp phần **sau** đó.

**Đầu ra:** nhận một model đã train và tự đưa nó vào vận hành: đóng gói, deploy, kiểm thử, theo dõi,
quản lý version, xử lý sự cố. Chứng minh bằng **một dự án portfolio end-to-end**.

Track có hai tầng:
- **Lõi (module 00–13):** đủ ứng tuyển **Junior/Fresher MLOps** hoặc **AI Engineer thiên về deployment**.
- **Tầng senior (module 14–18):** phủ **kiến thức** một Senior MLOps cần: K8s cho ML production, distributed
  training, streaming/real-time ML, nền tảng ML nhiều đội và bảo mật model, system design và dẫn dắt vận hành.
  Track nói thẳng với người học: kiến thức senior không thay được kinh nghiệm production thật; tầng này giúp
  trả lời phỏng vấn và làm việc ở mức senior, chức danh vẫn cần kinh nghiệm bảo chứng.

Người học đọc tiếng Việt, giữ thuật ngữ tiếng Anh. Đã xong các track DE, DA, DS, AI Engineer.
Track DevOps **đang được làm trên máy khác**, nên MLOps **đứng độc lập**, không lấy DevOps làm điều kiện.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Lấp placeholder `tracks/mlops` (đang `status: soon`) thành track `active` đúng `CONTENT_SPEC.md`.
- Phủ mọi mục của PDF roadmap MLOps (bảng đối chiếu ở mục 4.2).
- Nền tảng chính chạy local: **Docker, Docker Compose, FastAPI, MLflow, DVC, GitHub Actions,
  Prometheus, Grafana**. Kubernetes chỉ bắt đầu ở **module 13** (cuối lõi) và đi sâu ở tầng senior (module 14), không phải rào cản đầu vào của lõi.
- Năm năng lực cốt lõi, mỗi năng lực có bài thực hành và milestone capstone:
  1. Serving (realtime và batch).
  2. Pipeline training tái lập được.
  3. Quản lý version (code, data, model) và **cổng promotion**.
  4. Monitoring (service + model + data).
  5. Xử lý sự cố: phát hiện → xác minh → đánh giá tác động → quyết định **retrain / rollback / giữ nguyên**.

**Nguyên tắc nội dung (người học đã chốt)**
- **CI/CD tách lớp.** CI/CD cho code (test, build, release) khác với lớp data/model (kiểm chất lượng data,
  versioning, tracking, điều kiện promotion). Track dạy rõ ranh giới và chỗ hai lớp nối nhau.
- **Drift ≠ chất lượng giảm.** Drift chỉ là tín hiệu. Phải xác minh nguyên nhân và đo tác động trước khi
  hành động. Có bài mà đáp án đúng là **giữ nguyên model**.
- **Phần trùng chỉ ôn nhanh, không dạy lại.** MLflow cơ bản, FastAPI, ONNX, PSI/KS (DS module
  `14-mlops-for-ds`), LLM serving/eval/OTel (AE module `20-evaluation-production`), Docker/CI/Terraform cơ
  bản (DE module `08-devops-for-data`), Airflow/Prefect (DE `05-batch-pipelines`). Mỗi phần ôn tối đa một
  heading `## `, có link về module gốc. Bài tập phải **khác** bài các track đó và tập trung vào tự động hoá,
  deploy, monitoring, rollback, tái lập.

- **Model nhẹ, việc thật (người học chốt khi duyệt).** Không chạy model nặng. Trọng tâm là thực hành được và
  hiểu đúng việc một MLOps phải làm trong môi trường thực tế. Ngân sách: mỗi bài chạy trên laptop trong vài
  phút (mục tiêu ≤5 phút CPU, không kể tải dữ liệu lần đầu); model ETA train trên mẫu dữ liệu; bài distributed,
  GPU, K8s dùng model nhỏ. Bài nào chỉ "chờ model chạy" mà không dạy việc vận hành thì cắt bớt.

**Ngoài phạm vi**
- K8s tổng quát (kiến trúc, RBAC, NetworkPolicy, Helm, vận hành cluster), IaC chuyên sâu, service mesh: thuộc
  track DevOps. Module 13–14 chỉ dạy phần K8s đặc thù ML và ghi rõ phần nào kế thừa từ DevOps.
- LLMOps đặc thù (serving LLM, eval bằng judge): đã có ở AE 20, chỉ nhắc và trỏ về.
- Cloud trả phí bắt buộc. Cloud chỉ là phần mở rộng tuỳ chọn.
- Huấn luyện model mới làm trọng tâm. Model chỉ cần "đủ tốt"; giá trị nằm ở quy trình quanh nó.

**Điều cấm (làm vậy là hỏng dù chạy được)**
- Bài tập chép lại hoặc đổi tên bài của DS 14, AE 20, DE 08.
- Dạy "thấy drift thì retrain" như phản xạ mặc định.
- Bài **bắt buộc** cloud, GPU, tài khoản GitHub hay mạng mới qua được. Bài GPU phải có đường CPU.
- Test chỉ grep chuỗi trong tệp cấu hình khi chạy được công cụ thật. Test phụ thuộc mạng, cloud hoặc dịch
  vụ chưa bật mà không tự skip.
- Sửa **file hạ tầng dùng chung** mà track DevOps đang sửa ở máy khác (mục 3) ngoài phần thêm tối thiểu
  được liệt kê.
- Phá vỡ track DE, DA, DS, AE hoặc app hiện có.

## 3. Ràng buộc

- Cấu trúc thư mục, frontmatter, interview, quiz, capstone: đúng `CONTENT_SPEC.md`. **Không dự kiến sửa
  app** (app đã nhận starter không phải `.py`: Dockerfile, YAML, `dvc.yaml`…).
- Mỗi module: 5–8 phần lý thuyết (`## `), ≥2 sơ đồ mermaid, phần cuối là tài liệu tham khảo (link trong PDF
  roadmap làm gốc, cộng docs chính thức). Module dùng công cụ lần đầu có `## 0. Cài đặt` (không tính vào
  5–8 phần) theo quy ước như track DevOps: bảng phiên bản đã kiểm, kiểm checksum trước khi cài, cách gỡ,
  không `curl | sudo bash`. Công cụ Python cài qua `uv`.
- `interview.md` ≥12 câu, có câu tình huống sự cố, câu "vì sao chọn công cụ này", câu thiết kế hệ thống ML.
- Khoảng 7 bài mỗi module (3 Basic, 2–3 Intermediate, 2 Advanced); module 00 và 13 có thể ít hơn. Starter
  chạy test phải fail hoặc skip, không lỗi cú pháp. `SOLUTION=1` pass với Basic và Intermediate. Advanced
  chỉ có `SOLUTION.md` (hướng làm + rubric).
- Python 3.12, `uv`. Code không có comment inline; docstring chỉ khi thật cần.
- **Máy:** laptop 16 core, 31 GB RAM, RTX 3050 Laptop 4 GB. Mọi bài chạy được trên laptop. PC RTX 3060
  12 GB là tuỳ chọn (chỉ để benchmark thêm), test không bao giờ cần PC.
- **Không đụng hạ tầng dùng chung DevOps đang sửa.** `testkit.py`, `CONTENT_SPEC.md` (mục DevOps),
  `setup/docker-compose.yml`, `setup/DEVOPS-TOOLS.md` đang được Phase 2 DevOps sửa song song. Vì vậy:
  - Stack MLOps ở **`setup/mlops/compose.yaml`** riêng (giống cách `setup/airflow/` làm), cổng riêng
    không trùng stack DE/DevOps/Airflow, remap được qua `setup/.env`.
  - Helper test riêng của MLOps ở **module mới** (vd. `mlopskit.py` ở gốc repo, có test riêng trong `tests/`),
    không thêm vào `testkit.py`. Được **dùng** helper sẵn có của `testkit.py` (`DockerLab`, `require_tool`,
    `run_sandboxed`, `dataset`…).
  - `CONTENT_SPEC.md`: chỉ **thêm** một mục mới "Track MLOps" ở cuối tệp, không sửa mục khác.
  - `data/download_dataset.py`, `data/README.md`: chỉ **thêm** entry mới, không sửa entry cũ.
  - **Môi trường Python:** nút "Run tests" của app chạy `uv run pytest` trên môi trường mặc định, nên
    dependency mà test cần (mlflow, dvc, pandera, evidently, prefect, feast…) phải nằm trong môi trường mặc
    định (thêm thẳng hoặc qua group có trong `default-groups`). Thứ tự xử lý khi xung đột với pin hiện có
    (`numpy`, `pyarrow`, `grpcio`…): (1) chọn phiên bản tương thích; (2) nếu không được, công cụ đó chạy
    **trong container** của stack `setup/mlops` và test gọi qua CLI/HTTP; (3) không bao giờ hạ pin làm hỏng
    track khác. Ghi kết quả kiểm vào mục "Track MLOps" của `CONTENT_SPEC.md`.
  - **Môi trường GPU:** môi trường chính giữ torch CPU và `onnxruntime` CPU. Đường GPU (onnxruntime-gpu, torch
    CUDA) thêm vào project `setup/gpu` sẵn có của track AI Engineer (track đó đã merge, không ai đang sửa).
    Test GPU chạy qua project đó và skip khi không có CUDA; mọi bài có đường CPU.
  - **Helper DevOps Phase 2 chưa có** (`act_run`, `KubeLab`, `DockerLab.build`, `DockerLab.compose`):
    `mlopskit.py` tự viết bản tối thiểu cần cho MLOps, **dựng trên `DockerLab`** và giữ cùng bảo đảm an toàn
    (không gọi `docker` trần trong test module, `--rm`, nhãn, giới hạn tài nguyên, cổng `127.0.0.1`, dọn khi
    lỗi; script người học chạy qua `run_sandboxed`). Đặt tên khác để không đè tên DevOps sẽ thêm. Khi cả hai
    nhánh đã vào `main`, nhánh merge sau làm một task hợp nhất: chuyển MLOps sang helper của `testkit.py`
    nếu tương đương. Không chờ DevOps.
  - Có validator `tests/test_mlops_track.py` kiểm các quy tắc của track (cấu trúc, frontmatter, cấm `docker`
    trần trong test module), theo mẫu `tests/test_devops_track.py`.
- Làm trong worktree `../DataScience-mlops`, nhánh `mlops-track`. Rebase lên `origin/main` trước khi mở PR.

## 4. Danh sách module

### 4.1 Module

| # | id | Module | Nội dung chính |
| --- | --- | --- | --- |
| 00 | `00-introduction` | Giới thiệu MLOps | Vòng đời ML trong production; MLOps maturity levels (Google, Microsoft); vai trò MLOps / ML engineer / DS / DE; **bản đồ phần đã học** ở DS 14, AE 20, DE (ôn nhanh có link); bản đồ công cụ cả roadmap; hidden technical debt in ML |
| 01 | `01-engineering-foundations` | Nền tảng kỹ thuật cho ML code | Từ notebook sang package (`uv`, `pyproject`, cấu trúc `src/`), config tách khỏi code, logging có cấu trúc, test cho code ML (unit, data test, model test, test có tính ngẫu nhiên), Makefile, Git flow cho dự án ML; Bash đủ dùng; Go chỉ giới thiệu |
| 02 | `02-containers-for-ml` | Container cho ML | Image cho ML: multi-stage, image nhỏ, ghim phiên bản, CUDA base image và NVIDIA Container Toolkit, cache layer cho dependency nặng; Compose cho stack nhiều dịch vụ (healthcheck, depends_on, volume, profile); quét image (trivy) mức cơ bản |
| 03 | `03-data-versioning-quality` | Data versioning & chất lượng dữ liệu | DVC (remote trên MinIO, `dvc.yaml` pipeline, `dvc repro`, cache); data validation (Pandera chính, Great Expectations so sánh); data contract; lineage cơ bản; lakeFS/Delta so sánh |
| 04 | `04-tracking-registry` | Experiment tracking & model registry | MLflow server thật (backend Postgres, artifact MinIO), ôn nhanh DS 14; lineage model ↔ commit ↔ data version; alias/stage; **cổng promotion** (tiêu chí so với model đang chạy, kiểm tra slice, kiểm tra độ trễ); model card; W&B/Neptune/Comet so sánh |
| 05 | `05-training-pipelines` | Training pipeline & orchestration | Pipeline tái lập (seed, ghim data version, ghim môi trường); **Prefect 3** cho flow training và batch (retry, cache, schedule, backfill); continuous training: trigger theo lịch, theo data mới, theo cảnh báo; Airflow (ôn từ DE), Kubeflow Pipelines, ZenML, Metaflow so sánh |
| 06 | `06-feature-stores` | Feature store & training-serving skew | Skew và point-in-time correctness; **Feast** local (offline store file, online store Redis/SQLite); materialize; parity giữa batch và online; Tecton/Hopsworks so sánh |
| 07 | `07-model-serving` | Model serving | FastAPI production (ôn nhanh DS 14): load model theo alias, health/readiness, warmup, timeout, validate input, version trong response; batch inference theo lịch; **shadow, canary, A/B** ở tầng ứng dụng; rollback; load test (Locust hoặc k6); BentoML, Triton, Ray Serve, TorchServe so sánh |
| 08 | `08-cicd-for-ml` | CI/CD cho ML | **GitHub Actions** chạy local bằng `act`: CI cho code (lint, test, build image); lớp data/model (data test, train trên mẫu, kiểm model, đăng ký, cổng promotion); CD (deploy khi alias đổi); ranh giới hai lớp; secrets; GitLab CI/Jenkins/CML so sánh. Chạy trên GitHub thật là tuỳ chọn |
| 09 | `09-monitoring-observability` | Monitoring & observability | **Prometheus + Grafana**: metric service (RED: rate, error, duration), metric model (phân phối dự đoán, tỉ lệ fallback); log dự đoán để join nhãn sau; alert rule và routing (Alertmanager); dashboard as code; OTel trace ôn nhanh từ AE 20 |
| 10 | `10-drift-incidents` | Drift, nhãn về muộn & xử lý sự cố | Data drift, prediction drift, concept drift; **Evidently** + PSI/KS tự tính (ôn DS 14); drift đa biến; nhãn về muộn và ước lượng chất lượng khi chưa có nhãn; **khung quyết định retrain / rollback / giữ nguyên**; runbook, on-call, postmortem; bài sự cố cố ý; NannyML/WhyLabs/Arize so sánh |
| 11 | `11-deep-learning-serving` | Deploy model Deep Learning | **SegFormer** trên Oxford-IIIT Pets: export ONNX, ONNX Runtime CPU vs CUDA, kiểm sai số sau export, dynamic batching, benchmark throughput/latency, quản lý bộ nhớ GPU 4 GB (batch size, FP16, OOM), quantization INT8 cơ bản; Triton/TensorRT so sánh; SAM 2 chỉ trong bảng so sánh (quá nặng cho 4 GB) |
| 12 | `12-ml-platform-governance` | Nền tảng ML, governance & cloud | Reproducibility audit; model governance (approval, audit log, model card, quyền truy cập registry); chi phí; IaC cho ML ở mức đọc hiểu (ôn DE 08); **Cloud ML services** (SageMaker, Vertex AI, Azure ML) so sánh; lab cloud tuỳ chọn có hướng dẫn free tier, budget alarm, lệnh dọn; data engineering cho ML ôn nhanh (Spark/Kafka/Flink từ DE) |
| 13 | `13-kubernetes-for-ml` | Kubernetes cho ML (nâng cao) | Bảng "kế thừa từ track DevOps" (phần nào học ở DevOps 10–12, không dạy lại); kind; **chuyển service ETA từ Compose sang K8s** (Deployment, Service, ConfigMap, probes, resources); **KServe** InferenceService; **Argo Workflows** cho pipeline training (Argo CD giới thiệu cho GitOps); GPU trên K8s ở mức khái niệm |

| 14 | `14-kubernetes-ml-production` ★ | K8s cho ML production | Autoscaling inference (HPA theo custom metric, KEDA, KServe scale-to-zero, cold start); **Triton trên K8s dưới tải**; GPU scheduling (device plugin, time-slicing, MIG ở mức khái niệm); hàng đợi batch job (**Kueue**); multi-tenant: namespace, quota, priority, preemption; K8s chung (RBAC, NetworkPolicy, Helm) chỉ ôn và trỏ về DevOps 10–12 |
| 15 | `15-distributed-training` ★ | Distributed training & GPU compute | Data/model parallel, DDP, FSDP, ZeRO ở mức hiểu và đo; **torchrun nhiều tiến trình trên CPU (gloo)** để thực hành không cần nhiều GPU; **Ray** (Train, Tune); checkpoint và resume khi bị preempt (spot); throughput data loading; ước tính chi phí GPU; Horovod/DeepSpeed so sánh |
| 16 | `16-streaming-realtime-ml` ★ | Streaming feature & real-time ML | Kafka (ôn DE 07) → tính feature theo cửa sổ thời gian → **Feast push** vào online store; freshness và độ trễ end-to-end; online learning (**River**) và khi nào không nên; feedback loop và thiên lệch do chính model gây ra; Flink/Spark Structured Streaming/Bytewax so sánh |
| 17 | `17-ml-platform-security` ★ | Nền tảng ML nhiều đội & bảo mật model | Nền tảng cho nhiều đội: golden path, template dự án (Copier), self-service đăng ký và deploy model, chuẩn hoá registry; **FinOps cho ML** (cost attribution theo đội/model); build vs buy (Databricks, SageMaker, Vertex vs open source); **supply chain của model**: rủi ro pickle, safetensors, quét model (modelscan), ký model (sigstore / model-transparency), SBOM, phân quyền registry |
| 18 | `18-senior-system-design` ★ | ML system design & dẫn dắt vận hành | SLO/SLI và error budget riêng cho ML (chất lượng, freshness, latency); incident command, dẫn postmortem không đổ lỗi; design review và design doc; đánh đổi chi phí / độ trễ / chất lượng ở quy mô lớn; **bộ đề ML system design mức senior** (recommendation, fraud realtime, ETA, search ranking, LLM platform) có rubric |

★ = tầng senior. Phần cứng: laptop 4 GB, nên multi-GPU, MIG, cluster nhiều node chỉ ở mức khái niệm, đo và
mô phỏng (nhiều tiến trình CPU, kind nhiều node); PC 3060 là tuỳ chọn để đo thêm, test không cần.

Topic con và tên bài: builder quyết, miễn phủ đủ nội dung trên.

### 4.2 Đối chiếu roadmap PDF

| Mục roadmap | Ở đâu |
| --- | --- |
| Programming fundamentals (Python, Go, Bash) | 01 (Go giới thiệu) |
| Version control (Git, GitHub) | 01, 08 |
| Cloud computing, cloud-native ML services | 12 |
| Containerization (Docker, Kubernetes) | 02, 13 |
| ML fundamentals | 00 (trỏ về DS/AE) |
| Data engineering fundamentals (pipelines, lake/warehouse, ingestion, Airflow, Spark, Kafka, Flink) | 05, 12 (ôn nhanh, trỏ về DE) |
| MLOps principles | 00 |
| Version control (data/model) | 03, 04 |
| CI/CD | 08 |
| Orchestration | 05, 13 |
| Experiment tracking & model registry | 04 |
| Data lineage & feature stores | 03, 06 |
| Model training & serving | 05, 07, 11 |
| Monitoring & observability | 09, 10 |
| Infrastructure as Code | 12 |

## 5. Dạng bài và cách chấm

`pytest` là bộ chấm duy nhất. Test gọi công cụ thật (docker, dvc, mlflow, act, kubectl…) khi được, tự skip
khi thiếu công cụ, dịch vụ, dữ liệu hay GPU.

- **Bài code Python**: hàm/lớp có tên cố định trong `starter/`, test trên dữ liệu nhỏ sinh trong test.
- **Bài file cấu hình**: Dockerfile, `compose.yaml`, `dvc.yaml`, workflow `.github/workflows/*.yml`,
  `prometheus.yml`, rule alert, dashboard JSON, manifest K8s. Test **chạy thật**: build image, `dvc repro`,
  `act`, `promtool check rules` + test rule (`promtool test rules`), gọi HTTP vào service.
- **Bài notebook dữ liệu thật**: theo quy ước notebook của `CONTENT_SPEC.md` (cell `ensure`, quiz
  `data`/`knowledge`).
- **Bài sự cố cố ý** (từ module 07 trở đi, ≥1 bài mỗi module): README chỉ tả triệu chứng, nguyên nhân chỉ
  trong `solutions/`. Ví dụ: training-serving skew do tiền xử lý lệch, model sai version sau deploy, alert
  không bắn do rule sai, drift giả do pipeline đổi đơn vị, OOM GPU do batch size. Test chứng minh hành vi
  đúng sau khi sửa và có ca hồi quy chứng minh starter tái hiện triệu chứng.
- **Bài quyết định** (module 10, capstone): cho tình huống drift kèm số liệu; người học nộp quyết định và lý
  do dưới dạng tệp có cấu trúc (YAML) để test kiểm phần quyết định, rubric chấm phần lý do.
- **Bài "chọn công cụ"**: quiz `knowledge` theo tình huống.
- **Advanced**: thiết kế, runbook, postmortem, review kiến trúc; rubric trong `SOLUTION.md`.

**Helper (`mlopskit.py`, có test):** builder tự xác định cần gì, tối thiểu gồm: gate `require_mlops_stack()`
(skip nếu stack `setup/mlops` chưa bật); gate GPU (skip nếu không có CUDA); MLflow tạm cho test
(tracking URI file trong `tmp_path` khi không cần server); chạy `act` an toàn (cách ly như `DockerLab`).

## 6. Dữ liệu

| Bộ | Dùng ở | Ghi chú |
| --- | --- | --- |
| `nyc-tlc` (đã có, 2019-01..12) | capstone, 03–10 | **Không sửa** entry này (track DE dùng) |
| `nyc-tlc-2020` (**mới**) | capstone, 10 | Yellow taxi 2020-01..2020-12 + zone lookup, cùng nguồn CloudFront. Chứa cú sốc COVID tháng 3/2020 |
| `oxford-pets` (đã có, mirror HF, **không có trimap**) | 11 | Ảnh |
| `oxford-pets-trimaps` (**mới**) | 11 | `annotations.tar.gz` chính thức của VGG (~19 MB). Builder kiểm khớp `image_id` với mirror HF. Nếu nguồn chính quá chậm hoặc hỏng thì tìm mirror có trimap và ghi lý do |

Không commit mẫu trích từ bộ dữ liệu. Fixture test sinh trong test.

## 7. Capstone: dịch vụ ETA cho taxi NYC

**Bài toán:** dự đoán thời gian chuyến đi (giây) từ zone đón, zone trả, thời điểm, khoảng cách. Model là
gradient boosting (LightGBM hoặc sklearn HistGradientBoosting). Model chỉ cần "đủ tốt"; trọng tâm là vận hành.

**Hai đường gọi model:**
- **Realtime**: REST API FastAPI, giả lập app đặt xe hỏi ETA. Log mọi dự đoán (request id, version model,
  feature, dự đoán).
- **Batch theo lịch**: flow Prefect chấm cả ngày/tháng.

**Phát lại theo tháng:** một "đồng hồ mô phỏng" đẩy dữ liệu từng tháng của 2019 rồi 2020 vào hệ thống như
dữ liệu production. **Nhãn về muộn:** thời gian chuyến thật chỉ được "công bố" sau một độ trễ cấu hình
được (mặc định một tháng, phỏng theo việc TLC công bố dữ liệu chậm), rồi mới join với log dự đoán để tính
chất lượng thật. Trong khoảng chưa có nhãn, người học chỉ có tín hiệu drift.

**Sự cố có thật trong dữ liệu:** mùa vụ, ngày lễ, và COVID 3/2020 (lưu lượng sập, tốc độ đường phố tăng,
phân phối zone đổi). Người học phải phân biệt drift không làm hỏng dự đoán với drift làm hỏng, rồi quyết
định và bảo vệ quyết định bằng số.

**Milestone** (mỗi milestone sau một module; test `test_mNN_*`, `-k mNN`; `SOLUTION=1` chấm
`capstone/solutions/project/`):

| M | Sau module | Nội dung |
| --- | --- | --- |
| m01 | 01 | Biến notebook baseline ETA thành package có test, config, logging |
| m02 | 02 | Đóng gói training và serving thành image; stack Compose (API + MLflow + MinIO + Postgres) |
| m03 | 03 | DVC pipeline từ parquet thô tới tập train; data validation chặn tháng dữ liệu hỏng |
| m04 | 04 | Tracking, registry, cổng promotion có tiêu chí rõ |
| m05 | 05 | Flow Prefect: train theo lịch, batch inference, đồng hồ mô phỏng phát lại theo tháng |
| m06 | 06 | Feature (vd. tốc độ trung bình theo zone/giờ) qua Feast, không skew giữa batch và online |
| m07 | 07 | API production, shadow model mới, canary và rollback |
| m08 | 08 | Workflow GitHub Actions (chạy bằng `act`): CI code + CT model + deploy khi promotion qua |
| m09 | 09 | Prometheus + Grafana: dashboard service và model, alert rule có test |
| m10 | 10 | Phát lại 2019 → 2020: phát hiện, xác minh, quyết định retrain/rollback/giữ có số liệu; runbook + postmortem sự cố COVID |
| m11 | 12 | (Tuỳ chọn) Đưa một phần lên cloud free tier, có lệnh dọn |
| m12 | 13 | Chuyển service ETA sang kind + KServe; pipeline training trên Argo Workflows |
| m13 | 13 | Đánh giá độc lập mức junior: tình huống mới (vd. tháng dữ liệu lạ), người học tự chẩn đoán và vận hành theo rubric |
| m14 | 14 | ETA trên K8s chịu tải: autoscale theo custom metric, Kueue cho job retrain, quota tách serving và training |
| m15 | 15 | Retrain bằng Ray nhiều worker, checkpoint, chịu được worker bị kill giữa chừng |
| m16 | 16 | Feature real-time cho ETA (tốc độ theo zone 15 phút gần nhất) từ stream phát lại qua Kafka, đo freshness |
| m17 | 17 | Onboard model thứ hai (vd. dự đoán tiền tip) qua template nền tảng trong vài bước; model được ký và quét trước khi deploy; báo cáo chi phí theo model |
| m18 | 18 | Đánh giá độc lập mức senior: design doc cho nền tảng ETA nhiều thành phố, SLO và error budget, dẫn xử lý một sự cố dựng sẵn, postmortem; chấm theo rubric |

**Model SegFormer cho module 11:** không có checkpoint công khai cho trimap Pets, nên module cấp sẵn script
fine-tune `segformer-b0` (khởi từ checkpoint ImageNet/ADE20K công khai trên HF) mà người học **chạy một lần
như bước chuẩn bị**, không phải bài học: trên tập con nhỏ, vài phút trên 3050 4 GB hoặc lâu hơn một chút trên CPU
(chất lượng vừa đủ cho bài serving, không theo đuổi điểm cao). Không host artifact nào; model nằm trong MLflow local của người học.
Test dùng model nhỏ sinh trong test (vài lớp conv export ONNX), không cần model đã fine-tune.

Module 11 (DL serving) **không** có milestone; nó có bài portfolio riêng ở mức Advanced (service SegFormer
có benchmark CPU/GPU) vì bài toán ETA không phải DL.

## 8. Thứ tự làm (gợi ý cho plan)

- **Giai đoạn 1:** hạ tầng (`setup/mlops`, `mlopskit.py`, entry dữ liệu mới, `track.json`, README track, mục
  "Track MLOps" trong `CONTENT_SPEC.md`), module 00–04, capstone m01–m04; đổi `status` sang `active` ngay
  (như track DevOps) để học dần các module đã xong.
- **Giai đoạn 2:** module 05–10, capstone m05–m10.
- **Giai đoạn 3:** module 11–13, capstone m11–m13 (xong lõi junior).
- **Giai đoạn 4 (senior):** module 14–18, capstone m14–m18.

Mỗi task có implementer và reviewer độc lập; cuối mỗi giai đoạn review toàn nhánh. Làm liên tục hết track
(subagent-driven), chỉ dừng khi cần người học: tài khoản/khoá, PC, merge/push.

## 9. Quyết định của Claude (người học chưa duyệt từng điểm)

1. Capstone dùng NYC TLC (không dùng Olist) để tránh dính vào Olist Shop của track DevOps, và vì có drift
   thật (COVID).
2. **Prefect 3** là orchestrator chính (nhẹ, thuần Python, chạy local dễ); Airflow chỉ ôn và so sánh vì đã
   dạy ở DE.
3. **Feast** cho feature store, **Evidently** cho drift, **Pandera** cho data validation, **Locust hoặc k6**
   cho load test (builder chọn một).
4. Nhãn về muộn mô phỏng bằng độ trễ công bố (mặc định một tháng).
5. Module DL dùng SegFormer + Oxford-IIIT Pets kèm trimap tải riêng; SAM 2 chỉ so sánh.
6. Hạ tầng MLOps để ở tệp/thư mục riêng để tránh conflict với Phase 2 DevOps.
7. 19 module (00–13 lõi, 14–18 senior), khoảng 125 bài, 18 milestone.
11. Tầng senior: Kueue cho hàng đợi job, Ray cho distributed, River cho online learning, Copier cho template,
    modelscan + sigstore/model-transparency cho bảo mật model. Thực hành distributed bằng nhiều tiến trình CPU.
12. Stack Kafka cho module 16 đặt trong `setup/mlops` (không dùng service `kafka` của compose dùng chung, để
    không phụ thuộc file DevOps đang sửa).
8. `mlopskit.py` tự viết helper Docker/act/kind tối thiểu thay vì chờ DevOps Phase 2; hợp nhất sau khi cả
   hai vào `main`.
9. Dependency MLOps vào môi trường mặc định để nút "Run tests" chạy được; xung đột thì chạy công cụ trong
   container. Đường GPU dùng `setup/gpu`. Đã kiểm 2026-11-03: `dvc[s3]` và `evidently` resolve cùng pin hiện
   tại; `feast[redis]` kéo pandas 3.1 → 2.3.3, nên Giai đoạn 2 phải xử lý (chạy Feast trong container hoặc tìm
   bản tương thích), không hạ pandas của môi trường chung.
10. SegFormer: người học fine-tune `segformer-b0` một lần bằng script cấp sẵn (bước chuẩn bị); test không
    cần model đó.

## 10. Để builder quyết

- Phiên bản cụ thể của mọi công cụ (bản ổn định mới nhất, ghi vào bảng `## 0. Cài đặt`).
- Cổng của stack `setup/mlops` (kiểm không trùng bằng `ss -ltn` và các compose hiện có).
- Feature cụ thể của model ETA, ngưỡng cổng promotion, ngưỡng alert: chọn theo số đo thật và ghi lý do.
- Kích thước mẫu dữ liệu cho test và bài tập để chạy kịp trên laptop.
- Tên và số lượng bài trong từng module, miễn đủ nội dung ở mục 4.
