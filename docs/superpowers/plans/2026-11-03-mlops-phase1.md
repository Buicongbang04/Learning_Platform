# MLOps track Phase 1: hạ tầng + module 00–04 + capstone m01–m04 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bật track `mlops` trong app với hạ tầng riêng (helper `mlopskit.py`, stack `setup/mlops` gồm Postgres + MinIO + MLflow, bộ dữ liệu mới, validator), module 00–04 đầy đủ và capstone dịch vụ ETA m01–m04.

**Architecture:** Nội dung viết theo `CONTENT_SPEC.md`, app không đổi. Hạ tầng MLOps nằm ở tệp/thư mục riêng để không đụng các tệp track DevOps đang sửa ở máy khác: helper ở `mlopskit.py` (dựng trên `testkit.DockerLab`), stack ở `setup/mlops/compose.yaml`. Capstone là package Python `eta/` trong `tracks/mlops/capstone/project/`, chấm bằng `capstone/project/tests` (`SOLUTION=1` chấm `capstone/solutions/project/`).

**Tech Stack:** Python 3.12, uv, pytest; pandas/pyarrow, scikit-learn (HistGradientBoostingRegressor), MLflow 3.17.1, pandera, FastAPI (đã có trong `pyproject.toml`); **mới:** `dvc[s3]`; Docker, Docker Compose; MinIO, Postgres 16 (image).

**Spec:** `docs/superpowers/specs/2026-11-03-mlops-track-design.md`. Plan này phủ Giai đoạn 1 ở mục 8 của spec. Giai đoạn 2–4 có plan riêng, viết ngay sau khi giai đoạn trước xong.

## Global Constraints

- Làm trong worktree `/home/bangbc/Documents/DataScience-mlops`, nhánh `mlops-track` (`data/raw` là symlink tới checkout chính). Không đụng `tracks/devops/`. PR vào `main`, người học merge.
- **Không sửa** `testkit.py`, `setup/docker-compose.yml`, `setup/DEVOPS-TOOLS.md`, mục DevOps của `CONTENT_SPEC.md`, entry cũ trong `data/download_dataset.py`. Chỉ **thêm**: mục "Track MLOps" cuối `CONTENT_SPEC.md`, entry dataset mới, dòng biến mới cuối `setup/.env.example`.
- Track: id `mlops`, name `MLOps`, icon `workflow`, `order: 6` (giữ), `status: active`, `source: https://roadmap.sh/mlops`.
- Tiếng Việt, giữ thuật ngữ tiếng Anh. Có quyết định thực tế, đánh đổi, lỗi hay gặp; không dừng ở định nghĩa.
- **Model nhẹ, việc thật:** mỗi bài chạy trên laptop ≤5 phút CPU (không kể tải dữ liệu lần đầu). Dữ liệu thật dùng mẫu (vd. 200 000 dòng của một tháng, `seed=0`), không đọc cả 84 triệu chuyến.
- Mỗi module: 5–8 phần `## ` (không tính `## 0. Cài đặt`), ≥2 khối mermaid, phần cuối `## N. Tài liệu tham khảo`. Phần ôn kiến thức đã có ở DS 14 / AE 20 / DE tối đa **một** `## `, có link module gốc.
- Công cụ dùng lần đầu trong module có `## 0. Cài đặt`: bảng phiên bản đã kiểm, kiểm checksum trước khi cài, cài vào `~/.local/bin` hoặc qua `uv`, lệnh xác nhận, cách gỡ. Không `curl | sudo bash`.
- `interview.md` ≥12 câu, có câu sự cố, câu "vì sao chọn công cụ này", câu thiết kế hệ thống ML.
- Khoảng 7 bài/module (3 Basic, 2–3 Intermediate, 2 Advanced); module 00 được 4–6 bài. Starter: test fail hoặc skip, không error. `SOLUTION=1` pass, không skip khi stack/công cụ/dữ liệu đã có. Advanced chỉ `SOLUTION.md` (hướng làm + rubric).
- Bài tập không chép/đổi tên bài của DS `14-mlops-for-ds`, AE `20-evaluation-production`, DE `08-devops-for-data`.
- Test bài tập không gọi `docker` trần: dùng `testkit.DockerLab` hoặc helper `mlopskit` (Task 1). Script người học chạy qua `testkit.run_sandboxed`.
- Dependency mới ghim phiên bản phát hành ≥2 tuần trước ngày thêm (như cách `pyproject.toml` đang làm), thêm vào `dependencies` chính để nút "Run tests" chạy được.
- Việc nặng của builder chạy `nice -n 15`; tắt stack/container sau mỗi đợt kiểm.
- Code không có comment inline; docstring chỉ khi thật cần.
- Track khác giữ nguyên hành vi: `uv run pytest tests -q` và `SOLUTION=1 uv run pytest tracks/<từng track> -q` (chạy **riêng từng track**) cho cùng kết quả trước và sau; `cd app && pnpm test && pnpm typecheck` pass.
- Commit không có dòng Co-Authored-By.

## Review Focus

1. **Người học chưa bật stack `setup/mlops`** → test cần MLflow server/MinIO skip với thông báo nêu đúng lệnh `docker compose -f setup/mlops/compose.yaml up -d`; test dùng được MLflow file store (`mlopskit.mlflow_local`) thì **không** đòi stack. Test trong Task 1 (`test_require_stack_down_skips`) và Task 9 (bài Basic chạy không cần stack).
2. **Cổng mặc định đã bị chiếm** (máy này đã dùng 5432, 9000, 8000) → stack MLOps mặc định dải 2xxxx, đọc override từ `setup/.env`. Test trong Task 3 (`test_ports_avoid_taken_defaults`, `test_ports_from_env`).
3. **Dữ liệu NYC TLC bẩn thật**: thời lượng âm hoặc 0, `trip_distance` 0 hoặc rất lớn, ngày ngoài tháng của tệp (tệp 2019-01 có chuyến năm 2008/2018), zone 264/265 (Unknown). `clean()` phải loại theo luật cố định, có số dòng còn lại kiểm được. Test trong Task 10 (`test_m01_clean_rules`).
4. **Đọc cả tháng làm tràn RAM** → `load_month` chỉ đọc cột cần, lấy mẫu xác định theo `seed`. Test trong Task 10 (`test_m01_load_month_columns_and_sample`).
5. **Test bị ngắt giữa chừng để lại image/container/compose project** → mọi tài nguyên do `mlopskit` tạo có nhãn `mlops-ex=1` và tiền tố `mlops-ex-`, dọn trong `finally`. Test trong Task 1 (`test_built_image_removed_on_error`, `test_compose_down_on_error`).

---

### Task 1: `mlopskit.py` và dependency mới

**Files:**
- Create: `mlopskit.py`, `tests/test_mlopskit.py`
- Modify: `pyproject.toml`, `uv.lock` (thêm `dvc[s3]`)

**Interfaces:**
- Consumes: `testkit.DockerLab`, `testkit.docker_ready()`, `testkit.docker_cpu_args()`, `testkit.free_port()`, `testkit._load_env_file` (đọc `setup/.env` theo cách testkit đang làm; gọi qua import, không sửa testkit).
- Produces: `STACK_SERVICES: dict[str, tuple[str, int]]` = `{"postgres": ("MLOPS_PG_PORT", 25433), "minio": ("MLOPS_MINIO_PORT", 29000), "mlflow": ("MLOPS_MLFLOW_PORT", 25000)}`.
- Produces: `stack_port(service: str) -> int`: đọc biến môi trường (sau khi nạp `setup/.env`), mặc định theo bảng trên.
- Produces: `require_stack(*services: str) -> None`: skip `"Stack MLOps chưa bật ({service}). Chạy: docker compose -f setup/mlops/compose.yaml up -d"` nếu cổng không mở trên `127.0.0.1`.
- Produces: `mlflow_local(tmp_path: Path) -> str`: trả tracking URI `sqlite:///<tmp_path>/mlflow.db`, artifact root trong `tmp_path`, đặt `MLFLOW_TRACKING_URI` cho tiến trình hiện tại qua `mlflow.set_tracking_uri` (không cần server).
- Produces: `built_image(context: Path, dockerfile: str = "Dockerfile", build_args: dict[str, str] | None = None) -> ContextManager[str]`: `docker build` với nhãn `mlops-ex=1`, tag `mlops-ex-<uuid8>:test`, timeout 600 s; yield tag; luôn `docker rmi -f` trong `finally`. Skip nếu `not docker_ready()`. Build lỗi → `pytest.fail` kèm 40 dòng log cuối.
- Produces: `compose_project(file: Path, env: dict[str, str] | None = None, services: tuple[str, ...] = ()) -> ContextManager[ComposeProject]`: project name `mlops-ex-<uuid8>`, `docker compose -p … -f … up -d --build --wait` (timeout 600 s); `ComposeProject.port(service: str, container_port: int) -> int` (qua `docker compose port`), `.logs(service: str) -> str`, `.exec(service: str, *cmd: str) -> CompletedProcess`; luôn `down -v --remove-orphans --rmi local` trong `finally`. Skip nếu docker không sẵn sàng.
- Produces: `leftovers() -> list[str]`: container/image/network có nhãn `mlops-ex=1` hoặc project `mlops-ex-*` còn sót.

- [ ] **Step 1: Test thất bại** `tests/test_mlopskit.py` (giả lập `subprocess.run`/socket bằng `monkeypatch` cho phần logic; phần chạy Docker thật đánh dấu skip khi không có docker):

```python
def test_stack_port_default(monkeypatch): monkeypatch.delenv("MLOPS_MLFLOW_PORT", raising=False); assert mlopskit.stack_port("mlflow") == 25000
def test_stack_port_env(monkeypatch): monkeypatch.setenv("MLOPS_MLFLOW_PORT", "25999"); assert mlopskit.stack_port("mlflow") == 25999
def test_require_stack_down_skips(monkeypatch): ...      # cổng đóng → pytest.skip.Exception, message chứa "setup/mlops/compose.yaml"
def test_mlflow_local_roundtrip(tmp_path): uri = mlopskit.mlflow_local(tmp_path); log một run có metric mae=1.0; mlflow.search_runs() thấy run đó; uri.startswith("sqlite:///")
def test_built_image_removed(tmp_path): ...               # Dockerfile "FROM busybox:1.37" → image tồn tại trong with, mất sau with
def test_built_image_removed_on_error(tmp_path): ...      # raise trong with → image vẫn bị xoá
def test_compose_down_on_error(tmp_path): ...             # compose 1 service busybox sleep; raise trong with → leftovers() rỗng
```

- [ ] **Step 2:** `uv run pytest tests/test_mlopskit.py -q` → FAIL (`ModuleNotFoundError: mlopskit`).
- [ ] **Step 3: Viết `mlopskit.py`** theo Interfaces. Thêm `dvc[s3]` (bản ≥2 tuần tuổi; đã kiểm `dvc==3.67.1` resolve cùng pin hiện tại) vào `dependencies`, `uv lock`, `uv sync`.
- [ ] **Step 4:** `uv run pytest tests/test_mlopskit.py -q` → PASS (Docker có); `uv run dvc --version` chạy được; `uv run pytest tests -q` cùng kết quả như trước khi thêm.
- [ ] **Step 5: Commit** — `git commit -m "MLOps: mlopskit (stack, MLflow local, build image, compose tạm) và dvc"`

### Task 2: Bộ dữ liệu mới

**Files:**
- Modify: `data/download_dataset.py` (chỉ thêm entry), `data/README.md` (thêm dòng bảng)
- Test: `tests/test_download_dataset.py` (thêm test, không sửa test cũ)

**Interfaces:**
- Produces: `DATASETS["nyc-tlc-2020"]`: `url`, 12 tệp `yellow_tripdata_2020-{01..12}.parquet` từ `https://d37ci6vzurychx.cloudfront.net/trip-data/` + `taxi_zone_lookup.csv`; license và homepage như `nyc-tlc`; `about` ghi rõ có giai đoạn COVID 3/2020.
- Produces: `DATASETS["oxford-pets-trimaps"]`: `url` `https://thor.robots.ox.ac.uk/~vgg/data/pets/data/annotations.tar.gz` (~19 MB), `extract=True`; license CC BY-SA 4.0; `about` ghi chú dùng cùng `oxford-pets` (ảnh từ mirror HF). Builder tải thử: nếu > 30 phút hoặc lỗi, tìm mirror có trimap, ghi nguồn và lý do trong `about`.

- [ ] **Step 1: Test thất bại**: `test_nyc_tlc_2020_entry` (12 tệp đúng tên tháng, thêm lookup, cùng host với `nyc-tlc`), `test_oxford_trimaps_entry` (`extract` bật), `test_old_entries_unchanged` (so `nyc-tlc` và `oxford-pets` với bản copy hằng trong test).
- [ ] **Step 2:** chạy → FAIL.
- [ ] **Step 3: Thêm entry và dòng README.**
- [ ] **Step 4:** test → PASS. Tải thật cả hai bằng `uv run python data/download_dataset.py nyc-tlc-2020 oxford-pets-trimaps`; ghi vào `data/README.md` số dòng tháng 2020-03 và 2020-04 (để module/capstone sau dùng làm số tham chiếu) và việc `image_id` trong trimap khớp mirror HF (đếm số ảnh khớp).
- [ ] **Step 5: Commit** — `git commit -m "data: NYC TLC 2020 và trimap Oxford-IIIT Pets cho track MLOps"`

### Task 3: Stack `setup/mlops`

**Files:**
- Create: `setup/mlops/compose.yaml`, `setup/mlops/README.md`, `setup/mlops/mlflow/Dockerfile`
- Modify: `setup/.env.example` (thêm cuối tệp: `# MLOPS_PG_PORT=25433`, `# MLOPS_MINIO_PORT=29000`, `# MLOPS_MINIO_CONSOLE_PORT=29001`, `# MLOPS_MLFLOW_PORT=25000`)
- Test: `tests/test_mlops_setup.py`

**Interfaces:**
- Consumes: `mlopskit.STACK_SERVICES` (Task 1).
- Produces: project compose `mlops` với service:
  - `postgres` (`postgres:16.x` tag cụ thể), user/pass/db `mlops`/`mlops`/`mlflow`, cổng `127.0.0.1:${MLOPS_PG_PORT:-25433}:5432`, healthcheck `pg_isready`.
  - `minio` (tag cụ thể), `minioadmin`/`minioadmin`, cổng `${MLOPS_MINIO_PORT:-29000}:9000`, `${MLOPS_MINIO_CONSOLE_PORT:-29001}:9001`, healthcheck.
  - `minio-init` (image `minio/mc` tag cụ thể) tạo bucket `mlflow` và `dvc`, chạy một lần.
  - `mlflow` build từ `setup/mlops/mlflow/Dockerfile` (`mlflow==3.17.1` + `psycopg2-binary` + `boto3`), `--backend-store-uri postgresql://…`, `--artifacts-destination s3://mlflow`, `--serve-artifacts`, cổng `${MLOPS_MLFLOW_PORT:-25000}:5000`, healthcheck `/health`.
  - Mọi service `cpuset: "${DEVOPS_CPUSET:-}"`, giới hạn RAM (`mem_limit`), volume tên riêng `mlops_*`.
- Produces: `setup/mlops/README.md`: bật/tắt, kiểm, xoá dữ liệu, biến `MLFLOW_TRACKING_URI=http://127.0.0.1:25000`, `MLFLOW_S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` cho client.

- [ ] **Step 1: Test thất bại** `tests/test_mlops_setup.py` (đọc YAML, không chạy Docker):

```python
def test_services_present(): assert {"postgres", "minio", "minio-init", "mlflow"} <= set(compose["services"])
def test_images_pinned(): mọi `image` có tag và tag != "latest"
def test_ports_avoid_taken_defaults(): mọi cổng host mặc định ∉ {5432, 5433, 6379, 8000, 8080, 9000, 9001, 5000, 25432, 26379, 28000}
def test_ports_bound_localhost(): mọi mapping cổng bắt đầu "127.0.0.1:"
def test_ports_from_env(): mỗi cổng host là "${MLOPS_..._PORT:-<mặc định>}" khớp mlopskit.STACK_SERVICES
def test_env_example_lists_mlops_ports(): các biến MLOPS_* có trong setup/.env.example
```

- [ ] **Step 2:** chạy → FAIL.
- [ ] **Step 3: Viết compose, Dockerfile MLflow, README, dòng `.env.example`.**
- [ ] **Step 4:** test → PASS. Kiểm thật: `nice -n 15 docker compose -f setup/mlops/compose.yaml up -d --build --wait`; client Python log một run kèm artifact lên `http://127.0.0.1:25000`, thấy artifact trong bucket `mlflow` của MinIO; `docker compose … down -v`.
- [ ] **Step 5: Commit** — `git commit -m "setup: stack MLOps (Postgres, MinIO, MLflow server) ở setup/mlops"`

### Task 4: Khai báo track, README, quy ước, validator

**Files:**
- Modify: `tracks/mlops/track.json`, `CONTENT_SPEC.md` (thêm mục `## Track MLOps` ở cuối)
- Create: `tracks/mlops/README.md`, `tracks/mlops/capstone/README.md`
- Test: `tests/test_mlops_track.py`

**Interfaces:**
- Produces: `track.json` có module ids chính xác: `00-introduction`, `01-engineering-foundations`, `02-containers-for-ml`, `03-data-versioning-quality`, `04-tracking-registry`, `05-training-pipelines`, `06-feature-stores`, `07-model-serving`, `08-cicd-for-ml`, `09-monitoring-observability`, `10-drift-incidents`, `11-deep-learning-serving`, `12-ml-platform-governance`, `13-kubernetes-for-ml`, `14-kubernetes-ml-production`, `15-distributed-training`, `16-streaming-realtime-ml`, `17-ml-platform-security`, `18-senior-system-design`; capstone "Dịch vụ ETA cho taxi NYC", milestones `m01`…`m18` với `after` đúng bảng mục 7 của spec (m01→01, m02→02, m03→03, m04→04, m05→05, m06→06, m07→07, m08→08, m09→09, m10→10, m11→12, m12→13, m13→13, m14→14, m15→15, m16→16, m17→17, m18→18) và `doc` dạng `capstone/milestones/mNN-<slug>.md`.
- Produces: `tracks/mlops/README.md`: mục tiêu hai tầng (lõi junior 00–13, senior 14–18, câu nói thẳng về kinh nghiệm thật), sơ đồ mermaid module + milestone, bảng "đã học ở track khác → ôn ở đâu", cách bật stack, nguyên tắc model nhẹ.
- Produces: `capstone/README.md`: bài toán ETA, hai đường gọi (REST + batch), phát lại 2019 → 2020, nhãn về muộn, bảng 18 milestone, cách chấm (`capstone/project/tests`, `-k mNN`, `SOLUTION=1`).
- Produces: mục `## Track MLOps` trong `CONTENT_SPEC.md`: helper `mlopskit` (bảng như mục DevOps), stack và cổng, nguyên tắc model nhẹ ≤5 phút, môi trường Python (dependency vào môi trường mặc định; xung đột thì chạy công cụ trong container; GPU qua `setup/gpu`), bài sự cố cố ý, bài quyết định (YAML `decision`/`reasons`).
- Produces: validator chạy trên **mọi module có thư mục trên đĩa**:
  - README: dòng đầu `# `; số `## ` (trừ `## 0. Cài đặt`) trong [5, 8]; ≥2 ` ```mermaid `; `## ` cuối chứa `Tài liệu tham khảo`.
  - interview: ≥12 `## `.
  - Mỗi bài: frontmatter `title`, `level` khớp thư mục, `files`, `run`; đề chỉ có 4 heading `## ` cho phép; mỗi `files[].path` tồn tại; Basic/Intermediate có lời giải trùng tên mọi tệp `starter/`; Advanced có `SOLUTION.md`.
  - `tests/*.py` của bài tập và capstone không chứa `subprocess` gọi `"docker"` trực tiếp (chỉ qua `mlopskit`/`DockerLab`).
  - Không có `curl …| sudo bash` hoặc `| sudo sh` trong `tracks/mlops/**/*.md`.
  - Mỗi module 4–9 bài, ≥3 basic (trừ `00-introduction`), ≥2 advanced.
  - `test_phase1_present`: thư mục module 00–04 và tệp milestone m01–m04 tồn tại.

- [ ] **Step 1: Viết validator**; chạy → chỉ `test_phase1_present` FAIL (các kiểm khác pass rỗng).
- [ ] **Step 2: Cập nhật `track.json`, viết hai README và mục `CONTENT_SPEC.md`.** `cd app && pnpm test && pnpm typecheck && pnpm build`; `pnpm dev` thấy thẻ MLOps active, 19 module, icon `workflow`.
- [ ] **Step 3:** `uv run pytest tests/test_mlops_track.py -q` → chỉ `test_phase1_present` fail (xanh sau Task 10).
- [ ] **Step 4: Commit** — `git commit -m "MLOps: khai báo track, README, quy ước, validator nội dung"`

### Task 5–9: Module 00–04

Mỗi task là một module: `README.md`, `interview.md`, bài tập + lời giải, kiểm chứng. Tên bài và chi tiết do builder quyết; bảng dưới chốt **trọng tâm, bài bắt buộc, cơ chế chấm**. Quy trình giống nhau:

- [ ] **Step 1: Viết `tests/` của từng bài trước**, chạy trên starter → FAIL hoặc skip (không ERROR).
- [ ] **Step 2: Viết starter, lời giải, đề, `SOLUTION.md` Advanced, quiz nếu có.**
- [ ] **Step 3: Kiểm chứng** (stack bật khi module cần, dữ liệu đã tải):
  ```bash
  M=tracks/mlops/modules/<id>
  for d in $M/exercises/{basic,intermediate,advanced}/*/; do uv run pytest "$d" -q -rs | tail -1; done   # starter: failed/skipped, không error/passed
  SOLUTION=1 nice -n 15 uv run pytest $M -q -rs --durations=5   # passed, không skip; bài chậm nhất ≤ 300 s
  uv run pytest tests/test_mlops_track.py tests/test_quiz_files.py -q
  ```
- [ ] **Step 4: Viết lý thuyết + interview**, chạy lại validator → PASS cho module này.
- [ ] **Step 5: Commit** — `git commit -m "MLOps: module <id>"`

| Task | Module | Trọng tâm lý thuyết | Bài bắt buộc (ngoài bài builder tự chọn) | Chấm bằng |
| --- | --- | --- | --- | --- |
| 5 | `00-introduction` | Vòng đời ML trong production; MLOps maturity (Google level 0–2, Microsoft); vai trò MLOps / ML eng / DS / DE; hidden technical debt in ML; bản đồ công cụ roadmap; **một** phần ôn "đã học ở DS 14, AE 20, DE 05/08" có link | Phân loại maturity của 3 hệ thống mô tả sẵn (YAML, test kiểm level); quiz "chọn công cụ" theo tình huống (`kind: knowledge`); Advanced: viết bản đánh giá khoảng cách vận hành cho một dự án ML giả định (rubric) | pytest thuần Python; `tests/test_quiz_files.py` |
| 6 | `01-engineering-foundations` | Notebook → package (`src/` layout, `pyproject`, `uv`), config tách code (env + YAML, không hard-code đường dẫn), logging JSON, test cho code ML (unit, data test, test có seed, test hành vi model: invariance/directional), Makefile, Git flow dự án ML (không commit data/model, `.gitignore`, pre-commit); Bash đủ dùng; Go chỉ giới thiệu | Refactor một notebook "train ETA mini" cho sẵn thành package có `train()` gọi được và test pass; viết test hành vi model (đổi thứ tự cột không đổi dự đoán, tăng khoảng cách thì ETA không giảm trên trung bình); **bài sự cố**: train không tái lập (seed rò, đọc thứ tự file theo `os.listdir`) — đề chỉ tả "hai lần train ra MAE khác nhau" | `ex.module`, `run_sandboxed` cho lệnh `make`/CLI |
| 7 | `02-containers-for-ml` | Image cho ML: multi-stage, `uv` trong Docker, ghim phiên bản, cache layer dependency nặng, image nhỏ (slim vs full, kích thước torch CPU), không đóng model vào image vs có (đánh đổi); CUDA base image + NVIDIA Container Toolkit (đọc hiểu, đường CPU); Compose nhiều dịch vụ (healthcheck, depends_on condition, volume, profile, env file); trivy cơ bản; `## 0. Cài đặt` (Docker Compose v2 kiểm phiên bản, trivy) | Viết Dockerfile cho service dự đoán sklearn nhỏ: test build qua `mlopskit.built_image`, kiểm image < ngưỡng MB, chạy không bằng root, `/healthz` trả 200; viết compose 2 dịch vụ (API + MLflow file store) có healthcheck, test bằng `mlopskit.compose_project`; **bài sự cố**: container exit ngay vì model path sai/thiếu volume — đề chỉ tả "container restart liên tục" | `mlopskit.built_image`, `compose_project`, `httpx` |
| 8 | `03-data-versioning-quality` | DVC: track data, remote MinIO (`dvc remote add` S3 endpoint), `dvc.yaml` stages, `dvc repro`, cache, `dvc.lock` là hợp đồng tái lập; data validation (Pandera chính; Great Expectations so sánh); data contract giữa đội data và đội ML; lineage cơ bản (data version ↔ commit); lakeFS/Delta so sánh; `## 0. Cài đặt` (dvc qua `uv`) | Viết `dvc.yaml` 2 stage (prepare → split) trên mẫu NYC TLC nhỏ sinh trong test; test chạy `dvc repro` trong repo git tạm (`run_sandboxed`), đổi input → stage chạy lại, không đổi → skip; schema Pandera cho chuyến taxi bắt được 4 loại lỗi thật (thời lượng âm, distance 0, ngày ngoài tháng, zone ngoài 1–265); bài notebook trên `nyc-tlc` thật: đo tỉ lệ dòng bị loại theo từng luật trên mẫu 2019-01 (quiz `data`); **bài sự cố**: `dvc repro` không chạy lại sau khi sửa script vì thiếu `deps` | `run_sandboxed` với `git`/`dvc`; `ex.dataset("nyc-tlc")`; `require_stack("minio")` cho bài remote |
| 9 | `04-tracking-registry` | Ôn nhanh MLflow (một phần, link DS 14); MLflow server thật (Postgres + MinIO): vì sao không dùng file store khi nhiều người; lineage run ↔ git commit ↔ `dvc.lock`; alias `champion`/`challenger`; **cổng promotion**: tiêu chí so model đang chạy (MAE tổng, không tệ hơn ở slice quan trọng, latency), quyết định ghi lại được; model card; W&B/Neptune/Comet so sánh | Basic chạy với `mlflow_local` (không cần stack): log run có tag `git_commit`, `data_version`; hàm `decide_promotion(challenger, champion, policy) -> Decision` với ca biên (tổng tốt hơn nhưng slice xấu đi → không promote); Intermediate với `require_stack("mlflow")`: đăng ký 2 version, đặt alias, rollback alias về version cũ và chứng minh client load đúng version; **bài sự cố**: service load "model mới nhất" theo version number thay vì alias nên deploy nhầm model chưa duyệt | `mlopskit.mlflow_local`, `require_stack` |

### Task 10: Capstone m01–m04 (dịch vụ ETA)

**Files:**
- Create: `tracks/mlops/capstone/milestones/m01-package.md`, `m02-containers.md`, `m03-data-pipeline.md`, `m04-registry-promotion.md`
- Create: `tracks/mlops/capstone/project/README.md`, `project/notebooks/baseline.ipynb` (notebook baseline cho sẵn: điểm xuất phát của người học), `project/tests/conftest.py` (chọn `project/` hoặc `solutions/project/` như `tracks/devops/capstone/project/tests/conftest.py`), `project/tests/test_m01.py` … `test_m04.py`
- Create: `tracks/mlops/capstone/solutions/project/` (lời giải tham chiếu đầy đủ cho m01–m04), `tracks/mlops/capstone/solutions/SOLUTION.md`

**Interfaces** (package `eta` trong `project/src/eta/`, người học viết; lời giải tham chiếu cùng tên):
- `eta.config.Config` (dataclass): `data_dir: Path`, `months: list[str]`, `sample_rows: int = 200_000`, `seed: int = 0`, `model_params: dict`, `mlflow_uri: str`; `load_config(path: Path) -> Config` đọc YAML, cho phép biến môi trường `ETA_*` ghi đè.
- `eta.data.COLUMNS` = `["tpep_pickup_datetime", "tpep_dropoff_datetime", "PULocationID", "DOLocationID", "trip_distance"]`; `load_month(path: Path, sample_rows: int | None, seed: int) -> pd.DataFrame` (chỉ đọc `COLUMNS`, mẫu xác định).
- `eta.features.clean(df: pd.DataFrame, month: str) -> pd.DataFrame`: giữ `60 <= duration_s <= 10_800`, `0 < trip_distance <= 100`, pickup thuộc tháng `month`, zone trong `1..263`; thêm cột `duration_s`. `FEATURES` = `["PULocationID", "DOLocationID", "pickup_hour", "pickup_dow", "trip_distance"]`; `build_features(df) -> tuple[pd.DataFrame, pd.Series]`.
- `eta.train.train(X, y, params: dict) -> sklearn.pipeline.Pipeline` (HistGradientBoostingRegressor, zone là categorical); `evaluate(model, X, y) -> dict[str, float]` với đúng ba khoá `mae`, `p90_abs_err`, `mae_airport` (chuyến đón hoặc trả ở zone 132, 138 — JFK, LaGuardia).
- `eta.cli`: `python -m eta.cli train --config <yaml>` (in JSON metric), `python -m eta.cli validate <parquet> --month YYYY-MM` (exit 1 khi vi phạm schema).
- `eta.validate.SCHEMA` (Pandera), `validate_month(df: pd.DataFrame, month: str) -> None` (raise `pandera.errors.SchemaErrors`).
- `eta.registry.log_and_register(model, metrics: dict, config: Config, data_version: str) -> str` (trả version), tag `git_commit`, `data_version`.
- `eta.promotion.Policy` (dataclass: `max_mae_regression: float = 0.0`, `max_airport_regression: float = 0.05`); `decide(challenger: dict, champion: dict | None, policy: Policy) -> Decision` (`promote: bool`, `reasons: list[str]`); `promote_if_better(name: str, version: str, policy: Policy) -> Decision` (đặt alias `champion` khi qua).
- `eta.serve`: FastAPI `app`, `GET /healthz`, `POST /predict` body `{PULocationID, DOLocationID, pickup_datetime, trip_distance}` → `{"eta_s": float, "model_version": str}`; load model từ `models:/eta@champion` hoặc đường dẫn `ETA_MODEL_PATH`.
- `project/Dockerfile.train`, `project/Dockerfile.serve`, `project/compose.yaml` (API + dùng stack `setup/mlops` qua biến môi trường), `project/dvc.yaml` (`prepare` → `validate` → `train`), `project/params.yaml`.

- [ ] **Step 1: Viết test m01–m04** (`test_mNN_*`), chạy trên `project/` trống → FAIL/skip, không ERROR:

```python
def test_m01_load_month_columns_and_sample(project, tiny_parquet): df = load_month(tiny_parquet, 100, 0); assert list(df.columns) == COLUMNS and len(df) == 100; assert df.equals(load_month(tiny_parquet, 100, 0))
def test_m01_clean_rules(project, dirty_frame): out = clean(dirty_frame, "2019-01"); assert số dòng còn lại == giá trị tính tay trên fixture 12 dòng (mỗi luật loại đúng 1–2 dòng); assert out.duration_s.between(60, 10_800).all()
def test_m01_train_reproducible(project, synthetic_trips): hai lần train cùng seed → MAE bằng nhau tuyệt đối
def test_m01_cli_train_prints_metrics(project, tmp_path): run_sandboxed(["python", "-m", "eta.cli", "train", "--config", cfg]) → JSON có "mae"
def test_m01_real_data_baseline(project): ex.dataset("nyc-tlc"); MAE trên mẫu 2019-01 (200k, seed 0, test = 20% cuối theo thời gian) < MAE của baseline "trung vị theo cặp zone" trong notebook
def test_m02_serve_image(project): with built_image(project/"…", "Dockerfile.serve") → /healthz 200, /predict trả eta_s > 0, chạy user không phải root
def test_m02_train_image_small(project): image train < 1.5 GB (torch không có trong image)
def test_m03_dvc_repro_idempotent(project, tmp_path): repo git tạm + data tí hon; repro lần 2 không chạy lại stage nào; đổi params.yaml → chỉ stage train chạy lại
def test_m03_validate_blocks_bad_month(project, tmp_path): parquet tháng có 5% duration âm → `eta.cli validate` exit 1, stage train không chạy
def test_m04_promotion_rules(project): bảng tham số: challenger tốt hơn → promote; tổng tốt hơn nhưng airport tệ hơn 10% → không, reasons nhắc "airport"; champion None → promote
def test_m04_alias_rollback(project): require_stack("mlflow"); đăng ký v1, v2; promote v2; rollback alias về v1; load models:/eta@champion dự đoán bằng đúng v1
```

- [ ] **Step 2: Viết milestone docs** (đúng 5 phần của `CONTENT_SPEC.md`), `baseline.ipynb` (trung vị theo cặp zone + một model thô, chạy ≤2 phút) và lời giải tham chiếu.
- [ ] **Step 3:** `SOLUTION=1 nice -n 15 uv run pytest tracks/mlops/capstone -q -rs` (stack bật, `nyc-tlc` đã tải) → PASS, không skip; ghi MAE thật của baseline và lời giải vào `SOLUTION.md`. `uv run pytest tests/test_mlops_track.py -q` → PASS toàn bộ.
- [ ] **Step 4: Commit** — `git commit -m "MLOps: capstone ETA m01–m04"`

### Task 11: Kiểm toàn nhánh và mở PR

- [ ] **Step 1:** `uv run pytest tests -q`; `SOLUTION=1 nice -n 15 uv run pytest tracks/<track> -q` cho từng track `data-engineer`, `data-science`, `data-analyst`, `ai-engineer` (chạy riêng, không gộp) → cùng kết quả với `main` (chạy cùng lệnh trên checkout `main` để so).
- [ ] **Step 2:** `SOLUTION=1 nice -n 15 uv run pytest tracks/mlops -q -rs` (stack bật, dữ liệu đã tải) → không skip; liệt kê skip còn lại kèm lý do.
- [ ] **Step 3:** `cd app && pnpm test && pnpm typecheck && pnpm build` → PASS; `pnpm dev` mở một bài mỗi module 00–04 và capstone, chạy test trong app được.
- [ ] **Step 4:** dọn: `uv run python -c "import mlopskit; print(mlopskit.leftovers())"` in `[]`; `docker compose -f setup/mlops/compose.yaml down`.
- [ ] **Step 5:** rebase lên `origin/main`, đẩy nhánh, mở PR `mlops-track` → `main` (skill `mattpocock-skills:pr`): phạm vi Giai đoạn 1, cách bật stack, dữ liệu cần tải, cách kiểm, skip còn lại. **Dừng chờ người học merge**, rồi viết plan Giai đoạn 2.
