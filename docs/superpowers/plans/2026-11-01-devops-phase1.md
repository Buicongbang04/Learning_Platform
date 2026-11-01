# DevOps track Phase 1: hạ tầng + module 00–05 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bật track `devops` trong app với hạ tầng dùng chung (helper testkit, Mailpit, ứng dụng mẫu Olist Shop, validator nội dung), module 00–05 đầy đủ và milestone capstone m01–m02.

**Architecture:** Nội dung viết theo `CONTENT_SPEC.md`, app không đổi. Test bài tập gọi công cụ thật qua helper mới trong `testkit.py` (`require_tool`, `require_cluster`, `docker_cpu_args`) và tự skip khi thiếu. Olist Shop là app FastAPI nhỏ ở `tracks/devops/sample-app/` có test riêng chạy không cần Docker; bài tập và capstone vận hành nó. Một validator (`tests/test_devops_track.py`) khoá quy ước nội dung cho mọi module đã có trên đĩa.

**Tech Stack:** Python 3.12, uv, pytest; FastAPI, SQLAlchemy, redis/fakeredis, prometheus-client (đã có trong `pyproject.toml`); Bash; Docker; Nginx (image chính thức); Mailpit; shellcheck.

**Spec:** `docs/superpowers/specs/2026-11-01-devops-track-design.md`. Plan này phủ Phase 1 ở mục 8. Phase 2 (module 06–11, m03–m06) và Phase 3 (12–16, m07–m09) có plan riêng sau khi PR Phase 1 được merge.

## Global Constraints

- Làm trong worktree `/home/bangbc/Documents/Learning_Platform-devops`, nhánh `devops-track`. PR vào `main`, người học merge.
- Nội dung đúng `CONTENT_SPEC.md`: cấu trúc, frontmatter, chỉ 4 heading `## Mục tiêu` / `## Đề bài` / `## Tiêu chí đạt` / `## Gợi ý` trong đề, quy tắc quiz.
- Tiếng Việt, giữ thuật ngữ tiếng Anh. Chuẩn DevOps senior: có quyết định thực tế, đánh đổi, lỗi hay gặp.
- Track: id `devops`, name `DevOps`, icon `container`, `order: 5` (giữ), `status: active`, `source: https://roadmap.sh/devops`.
- Mỗi module: 5–8 phần `## `, ≥2 khối mermaid, phần cuối `## N. Tài liệu tham khảo`. Phần nhắc lại kiến thức track DE tối đa **một** `## `, có link module gốc.
- Công cụ dùng lần đầu trong module có phần `## 0. Cài đặt`: bảng phiên bản đã kiểm, lệnh tải, kiểm checksum, cài vào `~/.local/bin` (không sudo nếu được), lệnh xác nhận, cách gỡ. Không bao giờ `curl | sudo bash`.
- `interview.md` ≥12 câu, có câu sự cố, câu "vì sao chọn công cụ này", câu thiết kế.
- Khoảng 7 bài/module (3 Basic, 2–3 Intermediate, 2 Advanced). Starter: test fail hoặc skip, không error. `SOLUTION=1` pass (không skip) với Basic/Intermediate **khi công cụ đã cài**. Advanced chỉ `SOLUTION.md` (hướng làm + rubric). Test skip không tính là pass.
- Bài tập không chép/đổi tên bài của track DE (đặc biệt DE module 08, 11).
- Bài sự cố cố ý: đề chỉ tả triệu chứng, nguyên nhân nằm trong `solutions/`. Module 05 có ≥1 bài.
- Bảng so sánh công cụ cho mọi nhóm công cụ module đụng tới; có ≥1 bài "chọn công cụ" (quiz `kind: knowledge`) trong phase.
- Container do test, compose hoặc hướng dẫn khởi chạy dùng cpuset từ `docker_cpu_args()` (Task 1); việc nặng của builder chạy `nice -n 15 taskset -c 12-35`, mỗi lúc một job nặng, tắt container sau mỗi đợt kiểm.
- Không đụng service `localstack` và các service hiện có trong `setup/docker-compose.yml`. Không chạy lệnh phá huỷ trên cổng 5432/6379/9000/9001.
- Code không có comment inline; docstring đầu hàm chỉ khi thật cần.
- Track DE, DS, DA giữ nguyên hành vi: `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science tracks/data-analyst tests -q` cho cùng kết quả trước và sau; `cd app && pnpm test && pnpm typecheck` pass.
- Commit không có dòng Co-Authored-By.

## Review Focus

1. Máy người học có ít hơn 36 core → `docker run --cpuset-cpus 12-35` sẽ lỗi. `docker_cpu_args()` chỉ ghim khi máy có đủ core hoặc người học đặt `DEVOPS_CPUSET`. Test trong Task 1.
2. Công cụ có nhưng phiên bản cũ hơn mức tối thiểu → skip kèm lời nhắc rõ phiên bản cần và chỗ hướng dẫn cài, không fail khó hiểu. Chuỗi phiên bản của mỗi công cụ một kiểu (`nginx version: nginx/1.27.3`, `ShellCheck - version: 0.10.0`, `Docker version 27.3.1, build ...`, `v0.13.2`). Test trong Task 1.
3. Có lệnh `docker` nhưng daemon tắt hoặc user không có quyền socket → skip, không error. Test trong Task 1.
4. Máy người học có project khác chiếm 5432/6379/8000 → Olist Shop chạy compose riêng, cổng lấy từ biến môi trường với mặc định không trùng. Test trong Task 3.
5. Test bị ngắt giữa chừng để lại container → test dùng tên container ngẫu nhiên có tiền tố `devops-ex-` và dọn trong fixture `finally`; validator kiểm mọi test bài tập gọi `docker run` đều có `--rm`. Test trong Task 4.

---

### Task 1: Helper testkit cho bài DevOps

**Files:**
- Modify: `testkit.py` (thêm hàm module-level và staticmethod trên `Exercise`; cập nhật docstring đầu tệp)
- Test: `tests/test_testkit_devops.py`

**Interfaces:**
- Produces: `parse_version(text: str) -> tuple[int, ...] | None`: lấy cụm `\d+(\.\d+)+` đầu tiên trong chuỗi, bỏ tiền tố `v`.
- Produces: `tool_version(name: str) -> tuple[int, ...] | None`: chạy lệnh phiên bản theo bảng `TOOL_VERSION_ARGS` (`docker: ["--version"]`, `nginx: ["-v"]` (đọc stderr), `shellcheck: ["--version"]`, `kubectl: ["version", "--client"]`, `kind: ["version"]`, `helm: ["version", "--short"]`, `tofu: ["version"]`, mặc định `["--version"]`), timeout 10 s, gộp stdout+stderr; không có binary → `None`.
- Produces: `docker_ready() -> bool`: `docker info` exit 0 trong 10 s.
- Produces: `docker_cpu_args() -> list[str]`: `DEVOPS_CPUSET` khác rỗng → `["--cpuset-cpus", <giá trị>]`; không đặt và `os.cpu_count() >= 36` → `["--cpuset-cpus", "12-35"]`; còn lại `[]`. `DEVOPS_CPUSET=none` → `[]`.
- Produces: `Exercise.require_tool(name: str, min_version: str | None = None) -> None` (staticmethod): skip với thông báo `"Chưa cài {name}. Xem setup/DEVOPS-TOOLS.md"` hoặc `"{name} {có} cũ hơn {min_version} cần cho bài này. Xem setup/DEVOPS-TOOLS.md"`. Với `name == "docker"` thêm kiểm `docker_ready()`, skip `"Docker daemon chưa chạy hoặc user chưa có quyền dùng docker"`.
- Produces: `Exercise.require_cluster(name: str = "devops-lab") -> None` (staticmethod): `require_tool("kind")` rồi skip nếu `name` không có trong `kind get clusters`. (Dùng từ Phase 2, viết luôn để testkit đổi một lần.)

- [ ] **Step 1: Viết test thất bại** `tests/test_testkit_devops.py`, giả lập bằng `monkeypatch` trên `shutil.which` và `subprocess.run`, không gọi công cụ thật:

```python
@pytest.mark.parametrize("text,expected", [
    ("nginx version: nginx/1.27.3", (1, 27, 3)),
    ("ShellCheck - shell script analysis tool\nversion: 0.10.0", (0, 10, 0)),
    ("Docker version 27.3.1, build ce12230", (27, 3, 1)),
    ("v0.13.2", (0, 13, 2)),
    ("OpenTofu v1.13.2\non linux_amd64", (1, 13, 2)),
    ("no version here", None),
])
def test_parse_version(text, expected): assert testkit.parse_version(text) == expected

def test_require_tool_missing_skips(monkeypatch): ...      # which -> None => pytest.skip.Exception, message chứa "setup/DEVOPS-TOOLS.md"
def test_require_tool_too_old_skips(monkeypatch): ...      # version 0.9.0, min "0.10" => skip, message chứa "0.10"
def test_require_tool_ok(monkeypatch): ...                 # version 0.10.0, min "0.10" => không skip
def test_require_docker_daemon_down_skips(monkeypatch): ...# which ok, docker info exit 1 => skip "daemon"
def test_cpu_args_env(monkeypatch): ...                    # DEVOPS_CPUSET=0-3 => ["--cpuset-cpus","0-3"]; =none => []
def test_cpu_args_small_machine(monkeypatch): ...          # cpu_count 8, không env => []
def test_cpu_args_big_machine(monkeypatch): ...            # cpu_count 36 => ["--cpuset-cpus","12-35"]
def test_require_cluster_absent_skips(monkeypatch): ...    # kind get clusters trả "other" => skip chứa "devops-lab"
```

- [ ] **Step 2:** `uv run pytest tests/test_testkit_devops.py -q` → FAIL (`AttributeError: parse_version`).
- [ ] **Step 3: Cài các hàm trên trong `testkit.py`**. So sánh phiên bản bằng tuple sau khi `parse_version(min_version)`.
- [ ] **Step 4:** `uv run pytest tests/test_testkit_devops.py tests/test_testkit_notebook.py tests/test_testkit_workbook.py -q` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "testkit: require_tool, require_cluster, docker_cpu_args cho track DevOps"`

### Task 2: Mailpit trong compose và `setup/DEVOPS-TOOLS.md`

**Files:**
- Modify: `setup/docker-compose.yml` (thêm service `mailpit`, profile `[devops]`, không thêm vào `all`), `setup/.env.example` (`MAILPIT_SMTP_PORT=11025`, `MAILPIT_HTTP_PORT=18025`), `testkit.py` (`SERVICES["mailpit"] = ("MAILPIT_HOST", "localhost", "MAILPIT_SMTP_PORT", 11025)`)
- Create: `setup/DEVOPS-TOOLS.md`
- Test: `tests/test_devops_setup.py`

**Interfaces:**
- Produces: service compose `mailpit` (image `axllent/mailpit` pin tag cụ thể, `cpuset: "${DEVOPS_CPUSET:-}"` để trống được, cổng `${MAILPIT_SMTP_PORT:-11025}:1025`, `${MAILPIT_HTTP_PORT:-18025}:8025`). API HTTP Mailpit `GET /api/v1/messages` dùng cho test module 04.
- Produces: `setup/DEVOPS-TOOLS.md`: bảng `công cụ | module dạy cài | phiên bản tối thiểu | link tới "## 0. Cài đặt"`. Phase 1 có dòng: docker (tham chiếu `setup/SETUP.md`), shellcheck (01), jq (01), curl (có sẵn), openssl (04), dig (04), nginx chạy bằng image (05). Mục cuối "Ghim CPU": giải thích `DEVOPS_CPUSET` và vì sao `nice`/`taskset` không giới hạn container.

- [ ] **Step 1: Test thất bại** `tests/test_devops_setup.py`: đọc YAML compose, assert `mailpit` có `profiles == ["devops"]`, image có tag không phải `latest`, cổng host không thuộc `{5432, 6379, 9000, 9001, 8000, 8080}`; assert các service đã có (`localstack` …) không đổi image so với bản copy hằng trong test; assert mọi link `](../tracks/devops/...#...)` trong `DEVOPS-TOOLS.md` trỏ tới tệp tồn tại (anchor kiểm ở Task 10).
- [ ] **Step 2:** chạy test → FAIL.
- [ ] **Step 3: Thêm service, biến, `SERVICES`, viết `DEVOPS-TOOLS.md`**.
- [ ] **Step 4:** test → PASS; `docker compose -f setup/docker-compose.yml --profile devops config` hợp lệ; bật Mailpit, gửi một thư bằng `smtplib` tới cổng 11025, `GET :18025/api/v1/messages` thấy thư; tắt Mailpit.
- [ ] **Step 5: Commit** — `git commit -m "setup: Mailpit (profile devops) và mục lục cài công cụ DevOps"`

### Task 3: Ứng dụng mẫu Olist Shop

**Files:**
- Create: `tracks/devops/sample-app/README.md`, `app/main.py`, `app/db.py`, `app/worker.py`, `app/settings.py`, `app/logging.py`, `app/seed.py`, `compose.yaml`, `.env.example`, `tests/test_api.py`, `tests/test_worker.py` (tất cả dưới `tracks/devops/sample-app/`)

**Interfaces:**
- Produces: `settings.Settings` đọc env: `DATABASE_URL` (mặc định `sqlite:///./olist_shop.db`), `REDIS_URL` (mặc định `redis://localhost:16379/0`), `LOG_LEVEL` (`INFO`), `APP_VERSION` (`dev`).
- Produces: FastAPI `app` trong `app/main.py`:
  - `GET /healthz` → `200 {"status":"ok","version":APP_VERSION}`, không chạm DB/Redis.
  - `GET /readyz` → `200 {"db":"ok","redis":"ok"}`; một thành phần lỗi → `503`, thành phần đó `"error"`.
  - `GET /orders/{order_id}` → đơn + items + tổng tiền; không có → `404`.
  - `GET /stats/revenue-by-state` → `[{"state": str, "revenue": float}]` giảm dần theo revenue, đọc từ bảng `revenue_by_state` do worker tính.
  - `POST /jobs/recompute` → đẩy job `recompute_revenue` vào list Redis `olist:jobs`, trả `202 {"job_id": str}`.
  - `GET /metrics` → định dạng Prometheus: `http_requests_total{method,path,status}`, `http_request_duration_seconds` (histogram), `jobs_enqueued_total`.
- Produces: `worker.run_once(redis, engine) -> int` (xử lý tối đa 1 job, trả số job đã xử lý) và `worker.main()` (vòng lặp `BLPOP` timeout 5 s, thoát sạch khi nhận SIGTERM, tăng `jobs_processed_total`/`jobs_failed_total` trên cổng metrics `WORKER_METRICS_PORT` mặc định 9101).
- Produces: `logging.configure()`: log JSON một dòng/sự kiện với `ts`, `level`, `msg`, `request_id` (lấy từ header `X-Request-ID` hoặc sinh mới, trả lại trong response header).
- Produces: `seed.load(engine, olist_dir: Path, limit_orders: int = 5000)`: nạp `orders`, `order_items`, `customers` từ CSV Olist (`data/raw/olist` hoặc thư mục sinh bởi `data/generate_olist.py`).
- Produces: `compose.yaml` với `api` (build từ Dockerfile đơn giản do builder viết, sẽ được người học viết lại ở module 06), `worker`, `postgres:16` cổng host `${OLIST_SHOP_PG_PORT:-15432}`, `redis:7` cổng `${OLIST_SHOP_REDIS_PORT:-16379}`, `api` cổng `${OLIST_SHOP_API_PORT:-18000}`; mọi service có `cpuset: "${DEVOPS_CPUSET:-}"`; project name `olist-shop`.

- [ ] **Step 1: Test thất bại** (SQLite tạm + `fakeredis`, `TestClient`):

```python
def test_healthz_no_dependencies(client_without_db): r = client.get("/healthz"); assert r.status_code == 200 and r.json()["status"] == "ok"
def test_readyz_reports_redis_down(client, broken_redis): r = client.get("/readyz"); assert r.status_code == 503 and r.json() == {"db": "ok", "redis": "error"}
def test_order_found_and_total(client_seeded): r = client.get("/orders/o1"); assert r.json()["total"] == 35.5
def test_order_missing_404(client_seeded): assert client.get("/orders/nope").status_code == 404
def test_recompute_then_stats(client_seeded, fake_redis, engine):
    assert client.post("/jobs/recompute").status_code == 202
    assert worker.run_once(fake_redis, engine) == 1
    assert client.get("/stats/revenue-by-state").json()[0] == {"state": "SP", "revenue": 35.5}
def test_metrics_counts_requests(client): client.get("/healthz"); assert 'http_requests_total{method="GET",path="/healthz",status="200"}' in client.get("/metrics").text
def test_request_id_roundtrip(client): assert client.get("/healthz", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"
def test_worker_empty_queue(fake_redis, engine): assert worker.run_once(fake_redis, engine) == 0
def test_ports_avoid_common_defaults(): ...  # đọc compose.yaml, mọi cổng host mặc định ∉ {5432, 6379, 8000, 8080, 9000, 9001}
```

`path` trong metric là route template (`/orders/{order_id}`), không phải URL thật, để không nổ cardinality: thêm test gọi 3 order id khác nhau và assert chỉ có một series.

- [ ] **Step 2:** `uv run pytest tracks/devops/sample-app -q` → FAIL.
- [ ] **Step 3: Cài app, worker, seed, logging, compose** theo Interfaces.
- [ ] **Step 4:** test → PASS. Rồi kiểm thật (ghim CPU): `DEVOPS_CPUSET=12-35 nice -n 15 docker compose -f tracks/devops/sample-app/compose.yaml up -d --build`, seed bằng dữ liệu sinh, `curl :18000/readyz` → 200, `POST /jobs/recompute` rồi `GET /stats/revenue-by-state` có dữ liệu, `docker compose ... down -v`.
- [ ] **Step 5: Commit** — `git commit -m "DevOps: ứng dụng mẫu Olist Shop (API, worker, metrics, log JSON)"`

### Task 4: Khai báo track, README, validator nội dung

**Files:**
- Modify: `tracks/devops/track.json` (đủ 17 module, capstone 9 milestone theo spec mục 4 và 7)
- Create: `tracks/devops/README.md` (tổng quan, sơ đồ mermaid các module và capstone, cách dùng công cụ/cluster, lời nhắc ghim CPU), `tracks/devops/capstone/README.md` (Olist Shop, 9 milestone, cách chấm: m01–m08 có test trong `capstone/project/tests`, m09 rubric)
- Test: `tests/test_devops_track.py`

**Interfaces:**
- Produces: `track.json` có module ids chính xác: `00-introduction`, `01-linux-terminal`, `02-scripting`, `03-git-vcs-hosting`, `04-networking-protocols`, `05-web-server-proxy`, `06-containers`, `07-cicd-artifacts`, `08-iac-provisioning`, `09-config-management`, `10-kubernetes-core`, `11-kubernetes-production`, `12-gitops-secrets`, `13-observability`, `14-cloud-serverless`, `15-service-mesh-patterns`, `16-sre-operations`; milestones `m01`…`m09` với `after` đúng bảng spec mục 7 (m01→02, m02→05, m03→06, m04→07, m05→09, m06→11, m07→12, m08→13, m09→16).
- Produces: validator chạy trên **mọi module có thư mục trên đĩa** (Phase 2/3 tự được kiểm khi thêm):
  - README: dòng đầu `# `; số `## ` không tính `## 0. Cài đặt` trong [5, 8]; ≥2 ` ```mermaid `; `## ` cuối khớp `Tài liệu tham khảo`.
  - interview: ≥12 `## `.
  - Mỗi bài: frontmatter có `title`, `level` khớp thư mục, `files`, `run`; đề chỉ có 4 heading `## ` cho phép; mỗi `files[].path` tồn tại; Basic/Intermediate có `solutions/` cùng tên cho mọi tệp `starter/`; Advanced có `solutions/.../SOLUTION.md`.
  - Mọi `tests/*.py` gọi `docker run` thì có `--rm` và dùng `docker_cpu_args()`.
  - Không có chuỗi `curl` … `| sudo bash` / `| sudo sh` trong `tracks/devops/**/*.md`.
  - Mỗi module 0X có 5–9 bài, ≥3 basic, ≥2 advanced.
  - Ràng buộc phase: test riêng `test_phase1_modules_present` assert thư mục module 00–05 và milestone m01–m02 tồn tại.

- [ ] **Step 1: Viết validator**; chạy → FAIL ở `test_phase1_modules_present` (module chưa có), các kiểm còn lại pass rỗng.
- [ ] **Step 2: Cập nhật `track.json`, viết hai README.** Chạy `cd app && pnpm test && pnpm typecheck && pnpm build`; `pnpm dev` thấy thẻ DevOps active, 17 module, icon container (không có cảnh báo fallback icon).
- [ ] **Step 3:** `uv run pytest tests/test_devops_track.py -q` → chỉ `test_phase1_modules_present` fail (sẽ xanh sau Task 11).
- [ ] **Step 4: Commit** — `git commit -m "DevOps: khai báo track, README, capstone README, validator nội dung"`

### Task 5–10: Module 00–05

Mỗi task là một module: `README.md`, `interview.md`, bài tập + lời giải, và kiểm chứng. Tên bài và chi tiết do builder quyết; bảng dưới chốt **trọng tâm, dạng bài bắt buộc và cơ chế chấm**. Quy trình giống nhau cho mọi task:

- [ ] **Step 1: Viết `tests/` của từng bài trước**, chạy trên starter → FAIL hoặc skip (không ERROR).
- [ ] **Step 2: Viết starter, lời giải, đề, `SOLUTION.md` Advanced, quiz nếu có.**
- [ ] **Step 3: Kiểm chứng** khi công cụ đã cài (builder cài theo chính `## 0. Cài đặt` của module, vào `~/.local/bin`):
  ```bash
  M=tracks/devops/modules/<id>
  for d in $M/exercises/{basic,intermediate,advanced}/*/; do uv run pytest "$d" -q -rs | tail -1; done   # starter: failed/skipped, không error/passed
  SOLUTION=1 nice -n 15 taskset -c 12-35 uv run pytest $M -q -rs   # Basic/Intermediate: passed, không skip vì thiếu công cụ
  uv run pytest tests/test_devops_track.py tests/test_quiz_files.py -q
  ```
- [ ] **Step 4: Viết lý thuyết + interview**, chạy lại validator → PASS cho module này.
- [ ] **Step 5: Commit** — `git commit -m "DevOps: module <id>"`

| Task | Module | Trọng tâm lý thuyết | Bài bắt buộc (ngoài các bài builder tự chọn) | Chấm bằng |
| --- | --- | --- | --- | --- |
| 5 | `00-introduction` ★ | CALMS, DORA 4 key metrics (+ reliability), DevOps vs SRE vs Platform Eng, vòng đời phần mềm, bản đồ công cụ toàn roadmap, giới thiệu Olist Shop | Tính DORA metrics từ log deploy/incident cho sẵn (`.py`); quiz "chọn công cụ" theo tình huống; Advanced: đánh giá độ trưởng thành DevOps một team giả định (rubric) | pytest thuần Python; `tests/test_quiz_files.py` |
| 6 | `01-linux-terminal` | OS families + so sánh distro, filesystem/quyền, process & signal, systemd, performance (`top`, `vmstat`, `iostat`, `ss`), networking tools, text manipulation (`grep`/`awk`/`sed`/`jq`), editors; `## 0. Cài đặt` cho shellcheck, jq | **Cài và xác minh** (Q25): người học cài một binary (shellcheck) đúng cách, ghi `starter/install-log.md` + tệp `.sha256`; test kiểm `which`, phiên bản ≥ mức tối thiểu, checksum khớp, log không có `curl … \| sudo`. Bài phân tích access log Nginx thật-dạng bằng pipeline shell; bài viết systemd unit (kiểm bằng `systemd-analyze verify` nếu có) | `require_tool("shellcheck")`, subprocess chạy script trên fixture |
| 7 | `02-scripting` | Bash strict mode, trap, idempotency, exit code, getopts, xử lý lỗi; Python cho automation (subprocess, pathlib, argparse); so sánh Go/Node/Ruby/Rust/PowerShell | Script healthcheck/backup cho Olist Shop chạy lại nhiều lần không hỏng; script phải qua `shellcheck`; bài retry với backoff | subprocess + `shellcheck` + fixture thư mục tạm |
| 8 | `03-git-vcs-hosting` | Nhắc lại ngắn (1 phần, link DE 01), branching strategy, trunk-based, conventional commits, hooks, `bisect`, `rebase` an toàn, monorepo, so sánh GitHub/GitLab/Bitbucket, CODEOWNERS/branch protection | Bài `git bisect` tìm commit gây lỗi trong repo dựng sẵn bằng script trong test; bài viết pre-commit hook chặn secret; quiz chọn branching strategy | subprocess `git` trong `tmp_path` |
| 9 | `04-networking-protocols` | OSI/TCP-IP, DNS (record, TTL, resolve path), HTTP/1.1–2–3, TLS handshake & chứng chỉ, SSH (key, agent, tunnel), FTP/SFTP, email (SMTP/IMAP/POP3S, SPF/DKIM/DMARC, white/grey listing); `## 0. Cài đặt` cho dig, openssl | **Bài email offline**: phân tích bản ghi SPF/DKIM/DMARC và header `Received`/`Authentication-Results` cho sẵn, trả kết luận pass/fail từng thư; bài gửi thư qua Mailpit và kiểm qua API; bài sinh chuỗi CA → cert server, kiểm bằng `openssl verify` | Python thuần (offline); `require_service("mailpit")`; `require_tool("openssl")` |
| 10 | `05-web-server-proxy` | Nginx (server block, location, upstream, proxy headers, cache, rate limit, TLS), forward vs reverse proxy, caching server, load balancer (thuật toán, health check), firewall (nftables/ufw khái niệm), so sánh Nginx/Caddy/Apache/Tomcat/IIS; `## 0. Cài đặt` (nginx qua image Docker) | Reverse proxy + load balance trước 2 bản Olist Shop; **≥1 bài sự cố cố ý** (vd. 502 do upstream sai cổng/`proxy_pass` thiếu `/`, cert không khớp tên): đề tả triệu chứng, test kiểm sau sửa trả 200; Advanced: postmortem cho sự cố đó (rubric) | `require_tool("docker")`, `docker run --rm` nginx với `docker_cpu_args()`, `nginx -t` rồi gọi HTTP bằng `httpx` |

Task 10 Step 3 thêm: chạy `tests/test_devops_track.py` toàn bộ → PASS trừ `test_phase1_modules_present` (xanh sau Task 11).

### Task 11: Capstone m01–m02

**Files:**
- Create: `tracks/devops/capstone/milestones/m01-ops-scripts.md`, `m02-nginx-front.md`; `tracks/devops/capstone/project/README.md`; `tracks/devops/capstone/project/tests/test_m01.py`, `test_m02.py`; `tracks/devops/capstone/solutions/` (theo cách track DE: lời giải tham chiếu cho phần chấm được)

**Interfaces:**
- Consumes: Olist Shop (Task 3) và cổng `OLIST_SHOP_API_PORT`; `docker_cpu_args()`, `require_tool` (Task 1).
- Produces: m01: `capstone/project/ops/bootstrap.sh`, `healthcheck.sh` (exit 0 khi `/readyz` 200, exit 1 kèm thông báo thành phần lỗi), `backup.sh` (pg_dump vào thư mục có timestamp, giữ N bản mới nhất, idempotent). Test chạy script với `PATH` chứa binary giả (`pg_dump`, `curl`) trong `tmp_path` để không cần Docker; một test tích hợp tuỳ chọn `require_tool("docker")`.
- Produces: m02: `capstone/project/nginx/olist-shop.conf`: reverse proxy, TLS tự ký, rate limit `/jobs/`, header `X-Request-ID` truyền xuống app. Test dựng nginx + 1 app bằng `docker run --rm`, kiểm HTTPS 200, HTTP → 301, vượt rate limit → 429, request id tới log app.

- [ ] **Step 1: Viết test m01, m02** → FAIL trên project trống.
- [ ] **Step 2: Viết milestone docs + lời giải tham chiếu**.
- [ ] **Step 3:** chạy test trên lời giải (cách track DE dùng `solutions/` capstone) → PASS; `uv run pytest tests/test_devops_track.py -q` → PASS toàn bộ.
- [ ] **Step 4: Commit** — `git commit -m "DevOps: capstone m01–m02"`

### Task 12: Kiểm toàn nhánh và mở PR

- [ ] **Step 1:** `uv run pytest tests -q` và `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science tracks/data-analyst -q` → cùng kết quả với `main` (chạy cùng lệnh trên `main` để so, ghim CPU).
- [ ] **Step 2:** `SOLUTION=1 nice -n 15 taskset -c 12-35 uv run pytest tracks/devops -q -rs` → không có skip vì thiếu công cụ đã cài; liệt kê skip còn lại (nếu có) kèm lý do trong mô tả PR.
- [ ] **Step 3:** `cd app && pnpm test && pnpm typecheck && pnpm build` → PASS; `pnpm dev` mở một bài mỗi module 00–05, chạy test trong app được.
- [ ] **Step 4:** dọn: `docker ps -a --filter name=devops-ex- -q` rỗng; Olist Shop và Mailpit đã `down`.
- [ ] **Step 5:** đẩy nhánh, mở PR `devops-track` → `main` (dùng skill viết PR), mô tả: phạm vi Phase 1, công cụ cần cài, cách kiểm, skip còn lại. Người học merge.
