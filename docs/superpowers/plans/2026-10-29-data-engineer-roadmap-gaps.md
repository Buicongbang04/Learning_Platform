# Lấp chỗ thiếu track Data Engineer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phủ đủ roadmap PDF cho track `data-engineer` (module 00, hybrid ingestion, các mục mỏng) và chuyển phần thực hành mới + capstone sang dữ liệu thật, mỗi bài ra dữ liệu sạch, insight, biểu đồ, báo cáo.

**Architecture:** Nội dung là tệp markdown/notebook theo `CONTENT_SPEC.md`, app tự đọc. Bộ dữ liệu khai báo trong danh mục chung `data/download_dataset.py`; notebook gọi `ensure(name)` ở cell đầu. Bài notebook chấm bằng `testkit.Exercise.notebook()` + `Exercise.dataset()` (skip khi chưa tải). App thêm một endpoint mở tệp trong VS Code.

**Tech Stack:** Python 3.12 + uv, pytest, pandas/DuckDB/PySpark, nbformat, matplotlib; app Vite + React + TS.

**Spec:** `docs/superpowers/specs/2026-10-29-data-engineer-roadmap-gaps-design.md`

## Global Constraints

- Theo đúng `CONTENT_SPEC.md`; tiếng Việt, giữ thuật ngữ tiếng Anh.
- Không đổi tên, xoá, đánh số lại heading `## ` của README module đã có; bổ sung bằng `###`.
- Không sửa `data/generate_olist.py`. Olist thật ở `data/raw/olist_*.csv`; bộ giả khi cần: `data/raw/olist_synthetic/`.
- Bộ dữ liệu mới vào `data/raw/<bộ>/` (không commit); dữ liệu sạch người học sinh ra vào `data/clean/<bộ>/` (không commit).
- Bài dữ liệu thật ra đủ 4 sản phẩm: dữ liệu sạch (Parquet), insight có số, biểu đồ trong notebook, báo cáo (mục bắt buộc: Bộ dữ liệu, Làm sạch, Insight, Giới hạn).
- Spark dùng NYC TLC tổng 1–3 GB. M06 dùng NYC TLC; M11 dùng Olist thật.
- Test không cần mạng: phần dữ liệu thật dùng `Exercise.dataset(...)`/kiểm tệp Olist để skip; phần logic có test trên fixture nhỏ.
- Tệp dùng chung với phiên track AI & DS (`app/`, `testkit.py`, `pyproject.toml`, `data/download_dataset.py`): đọc bản mới nhất ngay trước khi sửa, sửa tối thiểu, không format lại, commit riêng từng task, chỉ `git add` tệp của task.
- Mỗi bài mới: `uv run pytest <bài> -q` trên starter fail/skip (không lỗi collect); `SOLUTION=1 uv run pytest <bài> -q` pass với Basic/Intermediate (khi bộ đã tải); Advanced chỉ `SOLUTION.md`.

## Review Focus

1. Bộ dữ liệu chưa tải → cell đầu notebook tự tải; test **skip** kèm lệnh tải, không fail. (Task 1, Task 4)
2. Tải bị ngắt giữa chừng (mạng, Kaggle) → không để lại thư mục dở dang bị coi là "đã tải"; lần sau tải lại được. (Task 1)
3. Chạy notebook hai lần → không tải lại, ghi đè `data/clean/<bộ>/` chứ không nhân đôi dòng. (Task 4, Task 7)
4. Chạy cả `tracks/` một lệnh (cùng track AI & DS) → không đụng tên module/test. (Task 9)
5. Tiến độ cũ: heading `## ` module 01/03/06/07/08/09/10/11 không đổi sau khi bổ sung. (Task 5, Task 6)

---

### Task 1: Danh mục bộ dữ liệu DE và hàm `ensure`

**Files:**
- Modify: `data/download_dataset.py` (thêm nguồn nhiều URL, `ensure()`, các bộ DE)
- Modify: `.gitignore` (thêm `data/clean/`)
- Create: `data/tests/test_download_dataset.py`
- Modify: `data/README.md` (bảng bộ dữ liệu DE: nguồn, giấy phép, kích thước, mốc ghim)

**Interfaces:**
- Produces: `ensure(name: str) -> Path` — trả `data/raw/<name>/`; đã có tệp thì không tải; chưa có thì tải vào thư mục tạm rồi đổi tên (atomic).
- Produces: các khoá trong `DATASETS`: `nyc-tlc` (Yellow Taxi Parquet, các tháng ghim cụ thể, tổng 1–3 GB), `nasa-http-logs` (tháng 7/1995), `air-quality-uci` (UCI Air Quality, cảm biến thật), `open-meteo-archive` không vào danh mục (API, bài tự gọi).
- `Dataset` thêm khả năng `source="url"` với `ref` là tuple nhiều URL, `files` cùng độ dài (giữ tương thích bộ cũ một URL).

- [ ] **Step 1: Viết test**

```python
def test_ensure_skips_download_when_present(tmp_path, monkeypatch):  # tạo raw/<name>/x, download không được gọi
def test_ensure_atomic_on_failure(tmp_path, monkeypatch):            # download ném lỗi → raw/<name>/ không tồn tại
def test_multi_url_dataset_downloads_each_file(tmp_path, monkeypatch):  # requests.get giả, 2 URL → 2 tệp đúng tên
def test_de_datasets_declared():  # {"nyc-tlc","nasa-http-logs","air-quality-uci"} <= DATASETS.keys(), mỗi bộ có license, homepage
```

- [ ] **Step 2:** `uv run pytest data/tests -q` → FAIL (`ensure` chưa có).
- [ ] **Step 3:** Hiện thực `ensure`, nguồn nhiều URL, khai báo 3 bộ. Builder kiểm URL còn tải được, giấy phép, chọn tháng TLC sao cho tổng 1–3 GB và ghi mốc vào `about`.
- [ ] **Step 4:** `uv run pytest data/tests -q` → PASS; tải thật từng bộ: `uv run python -c "from data.download_dataset import ensure; ..."` hoặc `uv run python data/download_dataset.py <bộ>` → tệp có trong `data/raw/<bộ>/`.
- [ ] **Step 5:** Commit `data/download_dataset.py data/tests .gitignore data/README.md`.

### Task 2: Nút "Mở trong VS Code"

**Files:**
- Modify: `app/server/workspace.ts` (endpoint `POST /api/workspace/open`)
- Modify: `app/src/pages/ExercisePage.tsx` (nút cạnh tệp `.ipynb` và cạnh thư mục bài)
- Modify: `setup/SETUP.md` (VS Code + extension Jupyter, chọn kernel `.venv`)
- Modify: `pyproject.toml` chỉ nếu `ipykernel` chưa có

**Interfaces:**
- Produces: `POST /api/workspace/open` body `{ "path": "<đường dẫn từ gốc repo>" }` → chạy `code <tuyệt đối>`; 400 nếu đường dẫn ra ngoài repo hoặc không tồn tại; 500 kèm thông báo nếu không có lệnh `code`.

- [ ] **Step 1:** Hiện thực endpoint (dùng lại kiểm tra đường dẫn sẵn có trong `workspace.ts`) và nút (nút viền, icon `ExternalLink`, nhãn "Mở trong VS Code").
- [ ] **Step 2:** `cd app && pnpm typecheck` → sạch.
- [ ] **Step 3:** Chạy `pnpm dev`; `curl -s -X POST localhost:5173/api/workspace/open -d '{"path":"../etc/passwd"}'` → 400; đường dẫn một notebook có thật → 200 và VS Code mở tệp.
- [ ] **Step 4:** `uv run python -c "import ipykernel"` thành công.
- [ ] **Step 5:** Commit các tệp của task.

### Task 3: Module 00 — lý thuyết, phỏng vấn, khai báo

**Files:**
- Create: `tracks/data-engineer/modules/00-introduction/README.md`, `interview.md`
- Modify: `tracks/data-engineer/track.json` (module `00-introduction` ở **đầu** `modules`; topics: What is DE, DE vs DS, Lifecycle, Data Generation, Data Collection, Choosing Technologies)

**Interfaces:**
- Produces: id module `00-introduction`, dùng ở Task 4.

- [ ] **Step 1:** Viết README: 5–8 phần `## N.` + `## N. Tài liệu tham khảo` (link gốc trong PDF roadmap), ≥2 mermaid (vòng đời + undercurrents; bản đồ nguồn dữ liệu DB/API/log/mobile/IoT), bảng DE vs DS vs DA, bảng data collection considerations (volume, velocity, schema, rate limit, privacy, chi phí, pháp lý), mỗi phần nối sang module 01–11. `interview.md` ≥12 câu.
- [ ] **Step 2:** Kiểm: `python3 -c "import json;print(json.load(open('tracks/data-engineer/track.json'))['modules'][0]['id'])"` → `00-introduction`; mở app, module 00 hiện đầu lộ trình, đếm đúng số phần.
- [ ] **Step 3:** Commit.

### Task 4: Module 00 — bài tập notebook trên dữ liệu thật

**Files:**
- Create: `tracks/data-engineer/modules/00-introduction/exercises/basic/01-api-weather-collection/` (Open-Meteo Historical API, khoảng ngày + thành phố ghim cố định)
- Create: `.../basic/02-web-server-logs/` (bộ `nasa-http-logs`)
- Create: `.../basic/03-iot-air-quality/` (bộ `air-quality-uci`)
- Create: 2–3 bài Intermediate (vd. thu thập API có phân trang + rate limit + incremental; so sánh nguồn theo data collection considerations) và 2 Advanced (vd. ma trận chọn công nghệ cho một bài toán; thiết kế thu thập nhiều nguồn) — tên do builder đặt
- Create: lời giải tương ứng trong `solutions/`

**Interfaces:**
- Consumes: `ensure(name)` (Task 1); `Exercise.notebook()`, `Exercise.dataset()` (testkit sẵn có).
- Mỗi notebook starter: cell 1 `from data.download_dataset import ensure; RAW = ensure("<bộ>")` (bài API: gọi API và cache JSON vào `data/raw/open-meteo/`); các hàm làm sạch/insight là hàm có tên để test lấy ra; cell biểu đồ gắn tag `explore`; cell cuối ghi `data/clean/<bộ>/*.parquet` và `report.md` trong thư mục bài (hoặc biến `REPORT`).

- [ ] **Step 1:** Mỗi bài viết test: fixture nhỏ trong `tests/fixtures/` cho hàm làm sạch (luôn chạy); test dữ liệu thật dùng `ex.dataset("<bộ>")` rồi so số insight với tham chiếu ghim (vd. số request 404 trong tháng 7/1995, ngưỡng CO trung bình theo giờ); test báo cáo có đủ 4 mục; test chạy notebook hai lần không nhân đôi dòng trong `data/clean/` (Review Focus 3).
- [ ] **Step 2:** `uv run pytest tracks/data-engineer/modules/00-introduction -q` → starter FAIL/skip.
- [ ] **Step 3:** Viết lời giải (notebook trùng tên + `SOLUTION.md`); Advanced chỉ `SOLUTION.md` + rubric.
- [ ] **Step 4:** `SOLUTION=1 uv run pytest tracks/data-engineer/modules/00-introduction -q` → PASS (bộ đã tải); xoá một bộ khỏi `data/raw/` tạm thời → test tương ứng SKIP kèm lệnh tải (Review Focus 1).
- [ ] **Step 5:** Commit.

### Task 5: Bổ sung lý thuyết các mục mỏng + bài DSA

**Files:**
- Modify (chỉ thêm `###`): `modules/01-foundations/README.md` (Java/Scala/Go + JVM; DSA cho DE), `03-nosql/README.md` (Memcached vs Redis), `06-spark-big-data/README.md` (DFS, job scheduling FIFO/fair/capacity, cluster managers), `08-devops-for-data/README.md` (functional/A-B/load/smoke testing; Datadog/Sentry/New Relic; GitLab CI/CircleCI/ArgoCD; declarative vs imperative, reusability, environment management, Google Deployment Manager), `10-security-governance/README.md` (Data Obfuscation, Metadata Management đúng tên roadmap), `09-serving-bi/README.md` (phần "Data cho ML": training pipeline, feature store, data versioning, trỏ track `mlops`)
- Modify: `interview.md` của các module trên (thêm câu cuối file)
- Create: `modules/01-foundations/exercises/intermediate/04-dsa-for-data/` (external sort, top-k heap, bloom filter, HyperLogLog — Python thuần) + lời giải
- Create: `modules/08-devops-for-data/exercises/intermediate/04-load-test-api/` (load test API serving của module 09 bằng thư viện có sẵn hoặc `httpx` + asyncio) + lời giải

- [ ] **Step 1:** Ghi lại heading trước khi sửa: `grep -h '^## ' tracks/data-engineer/modules/*/README.md > /tmp/headings-before.txt`.
- [ ] **Step 2:** Viết test cho 2 bài mới (vd. external sort trên tệp lớn hơn bộ nhớ cho phép giữ đúng thứ tự; bloom filter tỉ lệ dương tính giả ≤ ngưỡng; load test báo p50/p95 và error rate đúng trên server giả) → starter FAIL.
- [ ] **Step 3:** Viết lý thuyết + lời giải.
- [ ] **Step 4:** `SOLUTION=1 uv run pytest` hai bài → PASS; `diff /tmp/headings-before.txt <(grep -h '^## ' tracks/data-engineer/modules/*/README.md)` → không khác (Review Focus 5).
- [ ] **Step 5:** Commit.

### Task 6: Hybrid ingestion trên Wikimedia EventStreams

**Files:**
- Modify: `modules/07-streaming-kafka/README.md` (`###` batch/streaming/hybrid/realtime, Lambda vs Kappa, đối soát) và `interview.md`
- Modify: `data/download_dataset.py` chỉ nếu cần (EventStreams là stream trực tiếp — không vào danh mục)
- Create: `modules/07-streaming-kafka/exercises/advanced/03-hybrid-wikimedia/` (hoặc intermediate nếu vừa sức) + `SOLUTION.md`

**Interfaces:**
- Notebook ghi N phút `recentchange` ra `data/raw/wikimedia-recentchange/<timestamp>.jsonl`; phần stream tính số sửa theo phút/wiki, phần batch tính lại trên tệp; hàm `reconcile(stream_counts, batch_counts) -> DataFrame` chênh lệch.

- [ ] **Step 1:** Test: trên fixture JSONL nhỏ có event trùng/trễ, `reconcile` ra chênh lệch 0 sau khi dedup; trên tệp người học tự ghi, test tính tham chiếu bằng hàm lời giải (skip nếu chưa ghi tệp nào).
- [ ] **Step 2:** Starter FAIL/skip → viết `SOLUTION.md` (có code tham chiếu) → kiểm code tham chiếu pass khi chép tạm vào starter, rồi khôi phục starter.
- [ ] **Step 3:** Kiểm heading 07 không đổi; commit.

### Task 7: Spark trên NYC TLC

**Files:**
- Create: `modules/06-spark-big-data/exercises/intermediate/04-nyc-taxi-real/` (notebook PySpark: làm sạch chuyến đi, giờ cao điểm, tip theo khu vực, so thời gian trước/sau tối ưu: partition, broadcast zone lookup, small files) + lời giải

**Interfaces:**
- Consumes: `ensure("nyc-tlc")`; fixture Spark `local[*]` với `spark.driver.host=127.0.0.1`, `spark.driver.bindAddress=127.0.0.1`, `spark.sql.warehouse.dir` thư mục tạm (theo module 06 hiện có).

- [ ] **Step 1:** Test: hàm làm sạch trên fixture nhỏ (loại quãng đường ≤0, thời gian âm, giá âm); trên bộ thật: số chuyến sau làm sạch và giờ cao điểm khớp tham chiếu ghim; `data/clean/nyc-tlc/` partition theo ngày; chạy lại không nhân đôi.
- [ ] **Step 2:** Starter FAIL/skip → lời giải → `SOLUTION=1` PASS; thời gian chạy toàn bài dưới vài phút.
- [ ] **Step 3:** Commit.

### Task 8: Capstone trên dữ liệu thật

**Files:**
- Modify: `tracks/data-engineer/capstone/README.md` (Olist thật mặc định, kiến trúc hai nguồn Olist + NYC TLC, mục "Bài nộp cuối": pipeline, dữ liệu sạch, insight, dashboard trình duyệt Metabase/Streamlit, README portfolio)
- Modify: `capstone/milestones/m01..m11*.md` (lệnh mặc định `uv run python data/download_olist.py`; bộ giả `--out data/raw/olist_synthetic`; M06 sang `nyc-tlc`; M11 Olist thật; tiêu chí M09/M10 khớp bài nộp cuối)
- Modify: `capstone/project/ingestion/load_postgres.py` và `capstone/project/tests/` nếu đường dẫn mặc định đổi
- Create: `capstone/project/notebooks/olist_exploration.ipynb` (làm sạch, insight, biểu đồ, báo cáo trên Olist thật) + test trong `capstone/project/tests/`

- [ ] **Step 1:** Test notebook khám phá: skip nếu thiếu `data/raw/olist_orders_dataset.csv`; có thì kiểm insight tham chiếu (vd. số đơn `delivered`, điểm review trung bình đơn trễ vs đúng hạn) và báo cáo đủ 4 mục.
- [ ] **Step 2:** `uv run pytest tracks/data-engineer/capstone -q` → PASS (Olist thật đã có trên máy).
- [ ] **Step 3:** Rà mọi lệnh trong milestone chạy được (`--help` hoặc chạy thật với Olist thật).
- [ ] **Step 4:** Commit.

### Task 9: Cập nhật tài liệu, kiểm toàn bộ

**Files:**
- Modify: `README.md`, `tracks/data-engineer/README.md` (số module/bài, sơ đồ thêm M00 và hai nguồn capstone), `CONTENT_SPEC.md` (mẫu notebook dữ liệu thật + 4 sản phẩm, nếu track AI & DS chưa ghi)

- [ ] **Step 1:** `SOLUTION=1 uv run pytest tracks/data-engineer -q` → không fail; `uv run pytest tracks -q` (cả track AI & DS) → không lỗi collect (Review Focus 4).
- [ ] **Step 2:** `cd app && pnpm typecheck`; mở app: module 00 đầu lộ trình, nút "Mở trong VS Code" hoạt động.
- [ ] **Step 3:** Mỗi notebook mới chạy từ đầu tới cuối trên dữ liệu thật trong VS Code ra đủ 4 sản phẩm.
- [ ] **Step 4:** Commit (không push — hỏi người dùng).
