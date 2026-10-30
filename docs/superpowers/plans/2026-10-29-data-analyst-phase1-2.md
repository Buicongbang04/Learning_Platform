# Data Analyst track: hạ tầng + module mẫu 08 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bật track `data-analyst` trong app (15 module khai báo, capstone README) với một module mẫu hoàn chỉnh `08-visualization-chart-reading`, kèm phần sửa app để có bài chỉ gồm trắc nghiệm.

**Architecture:** Nội dung viết theo `CONTENT_SPEC.md` và dùng lại `testkit.Exercise` (`notebook()`, `dataset()`), registry `DATASETS` trong `data/download_dataset.py`, quiz `quiz.yaml`/`quiz-answers.yaml`. App thêm một nhánh hiển thị cho **bài quiz-only** (không có starter, không có test): card giới thiệu + card trắc nghiệm, dùng lại `QuizCard`. Biểu đồ luôn vẽ trong notebook (cell `explore`), không dùng ảnh tĩnh, nên app không cần render ảnh.

**Tech Stack:** Python 3.12, uv, pytest, pandas, matplotlib, seaborn, plotly (thêm), nbformat; app Vite + React + TypeScript, `node --test`.

**Spec:** `docs/superpowers/specs/2026-10-29-data-analyst-track-design.md`. Plan này chỉ phủ mục 8 bước 1–2. Bước 3 (14 module còn lại, sửa app cho `.xlsx` và quiz trên bài không phải notebook, Superset, milestone capstone) có plan riêng sau khi người học duyệt module 08.

## Global Constraints

- Mọi nội dung đúng `CONTENT_SPEC.md` (cấu trúc, frontmatter, chỉ 4 heading `## Mục tiêu` / `## Đề bài` / `## Tiêu chí đạt` / `## Gợi ý` trong đề, quy tắc notebook, quy tắc quiz gồm quy tắc độ dài đáp án).
- Tiếng Việt, giữ thuật ngữ tiếng Anh. Chuẩn DA senior: có quyết định thực tế, đánh đổi, lỗi hay gặp.
- Track id `data-analyst`, tên `Data Analyst`, icon `chart-column`, `order: 2` (giữ), `source`: `https://roadmap.sh/data-analyst`.
- Kiến thức trùng track DE/DS: tối đa **một** phần `## ` nhắc lại, có link module gốc. Bài tập không chép/đổi tên bài track DE/DS.
- Dữ liệu thật cho notebook; dữ liệu sinh chỉ trong test. Không commit dữ liệu tải về; không commit mẫu trích từ bộ có giấy phép chưa rõ.
- Test không cần mạng, Docker hay bộ đầy đủ; phần cần bộ thật gọi `ex.dataset(...)` và tự skip.
- Track DE và DS giữ nguyên hành vi: `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science -q` cho cùng kết quả trước và sau; `cd app && pnpm test && pnpm typecheck` pass.
- Commit không có dòng Co-Authored-By.

## Review Focus

1. Bài quiz-only (frontmatter `files: []`, `run: []`, không có `starter/`, `tests/`) → app hiện card giới thiệu + trắc nghiệm, **không** hiện khung code rỗng hay nút chạy test. Test trong Task 1.
2. Bài notebook hiện có (DE/DS) → vẫn vào `NotebookPanel`; bài `.py` vẫn vào `Workspace`. Test trong Task 1.
3. Bài quiz-only thiếu `quiz.yaml` (lỗi soạn bài) → card báo rõ "chưa có câu hỏi", không trang trắng. Test trong Task 1 (hàm phân loại) + `tests/test_da_module08.py` (Task 7) kiểm mọi bài quiz-only có `quiz.yaml`.
4. Người học chạy notebook khi chưa tải dữ liệu → cell đầu gọi `ensure(...)` tải về; khi chấm (cell `explore` bị bỏ) test vẫn chạy. Kiểm ở Task 5–7 bằng chạy starter khi `data/raw/<bộ>` không có (đổi tên tạm thư mục).
5. Online Retail II có hoá đơn huỷ (`Invoice` bắt đầu `C`), số lượng âm, thiếu `Customer ID`, tháng 12/2011 chỉ có dữ liệu tới ngày 9 → hàm tính doanh thu trong lời giải xử lý đúng, có test fixture nhỏ chứa đủ các trường hợp này. Test trong Task 5 và 6.

---

### Task 1: App — bài chỉ gồm trắc nghiệm

**Files:**
- Create: `app/src/code/exerciseKind.ts`, `app/src/code/exerciseKind.test.ts`, `app/src/code/QuizOnlyPanel.tsx`
- Modify: `app/src/code/NotebookPanel.tsx` (export `QuizCard` và các khối intro dùng lại), `app/src/pages/ExercisePage.tsx:261-270`, `CONTENT_SPEC.md` (mục "Bài tập notebook": thêm tiểu mục "Bài chỉ có trắc nghiệm")

**Interfaces:**
- Produces: `exerciseKind(exercise: Pick<Exercise, "files">): "notebook" | "quiz-only" | "code"` trong `exerciseKind.ts`. `"notebook"` khi có `starter/*.ipynb` (giữ logic `notebookOf`); `"quiz-only"` khi `files` không có tệp nào bắt đầu bằng `starter/` hoặc `tests/`; còn lại `"code"`. `isNotebookExercise` giữ export cũ (gọi qua `exerciseKind`).
- Produces: `QuizOnlyPanel({ exercise, trackId, done, onMarkDone })`: card giới thiệu (mục tiêu lấy từ đề, nút "Đánh dấu hoàn thành" như `NotebookPanel`) + `QuizCard`. Khi `useQuiz` trả `none`, hiện thông báo "Bài này chưa có câu hỏi".

- [ ] **Step 1: Viết test thất bại** `exerciseKind.test.ts`:

```ts
test("notebook DS vẫn là notebook", () => assert.equal(exerciseKind({ files: [{ path: "starter/eda.ipynb" }, { path: "starter/MEMO.md" }] }), "notebook"));
test("bài .py là code", () => assert.equal(exerciseKind({ files: [{ path: "starter/load.py" }, { path: "tests/test_x.py", note: "Không sửa" }] }), "code"));
test("files rỗng là quiz-only", () => assert.equal(exerciseKind({ files: [] }), "quiz-only"));
test("chỉ có tệp ngoài starter/tests vẫn là quiz-only", () => assert.equal(exerciseKind({ files: [{ path: "README.md" }] }), "quiz-only"));
```

- [ ] **Step 2:** `cd app && pnpm test` → FAIL (module chưa có).
- [ ] **Step 3: Cài `exerciseKind`, `QuizOnlyPanel`, nối vào `ExercisePage`** (switch 3 nhánh; nhánh quiz-only dùng cùng `section` layout như notebook).
- [ ] **Step 4:** `cd app && pnpm test && pnpm typecheck && pnpm build` → PASS.
- [ ] **Step 5: Cập nhật `CONTENT_SPEC.md`**: bài quiz-only có `README.md` (frontmatter `files: []`, `run: []`), `quiz.yaml`, `solutions/.../quiz-answers.yaml` + `SOLUTION.md` giải thích từng đáp án; không có `starter/`, `tests/`.
- [ ] **Step 6: Kiểm tay** sau Task 5 (khi đã có bài quiz-only thật): `pnpm dev`, mở `08/basic/01-chart-chooser` thấy card giới thiệu + trắc nghiệm, nộp được, điểm lưu vào `progress.json`; mở một bài notebook DS và một bài `.py` DE thấy như cũ.
- [ ] **Step 7: Commit** — `git commit -m "App: bài chỉ có trắc nghiệm (quiz-only) hiện card giới thiệu và trắc nghiệm"`

### Task 2: Bộ dữ liệu thật cho module 08 và capstone

**Files:**
- Modify: `data/download_dataset.py` (`DATASETS`), `data/README.md` (bảng bộ dữ liệu), `pyproject.toml` (thêm `plotly>=5.24`, `openpyxl` nếu chưa có)
- Test: `tests/test_download_dataset.py` (theo kiểu test registry đang có)

**Interfaces:**
- Produces các khoá trong `DATASETS` (tên tệp giữ lại do builder chốt sau khi tải thử, ghi trong `files`):
  - `bike-sharing-uci`: UCI Bike Sharing (`hour.csv`, `day.csv`), CC BY 4.0, https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset
  - `online-retail-ii`: UCI Online Retail II (2009–2011), CC BY 4.0, https://archive.ics.uci.edu/dataset/502/online+retail+ii. Nếu bản gốc chỉ có `.xlsx` thì giữ `.xlsx` (đọc bằng `pd.read_excel` + `openpyxl`); được thay bằng mirror Kaggle CSV nếu giấy phép ghi rõ.
  - `dunnhumby-complete-journey`: Kaggle `frtgnn/dunnhumby-the-complete-journey`, giấy phép Open Database License (đã kiểm 2026-10-29), 8 tệp CSV.
  - Olist dùng bộ đã có (`data/download_olist.py`), không thêm khoá.
- Builder tải thật từng bộ một lần, ghi số dòng từng tệp vào `data/README.md` (để Task 5–7 và capstone dùng làm số tham chiếu).

- [ ] **Step 1: Test thất bại**: thêm 3 khoá vào danh sách khoá mong đợi trong test registry (mỗi khoá có `license` khác rỗng, `homepage` https).
- [ ] **Step 2:** `uv run pytest tests/test_download_dataset.py -q` → FAIL.
- [ ] **Step 3: Thêm 3 mục registry + dependency**.
- [ ] **Step 4:** test → PASS; `uv run python data/download_dataset.py <tên>` cho cả 3 bộ → tải xong, chạy lại lần 2 không tải lại.
- [ ] **Step 5: Commit** — `git commit -m "Dữ liệu: Bike Sharing, Online Retail II, dunnhumby Complete Journey"`

### Task 3: Khai báo track + README track + capstone README

**Files:**
- Modify: `tracks/data-analyst/track.json`
- Create: `tracks/data-analyst/README.md`, `tracks/data-analyst/capstone/README.md`

**Interfaces:**
- Produces: `track.json` với `status: "active"`, `description` một câu, `source`, `modules` đủ 15 mục đúng id và tiêu đề ở bảng mục 4 của spec, mỗi mục có `summary` và `topics`. **Chưa** có khoá `capstone` (thêm ở plan sau cùng milestone docs).

- [ ] **Step 1: `track.json`** theo spec mục 4.
- [ ] **Step 2: `README.md` track**: đối tượng (người đã học DE/DS muốn làm DA tới mức senior), cách học (lý thuyết ngắn, chủ yếu bài tập; phần trùng thì nhắc lại + link), chuẩn bị dữ liệu, cách làm bài notebook và bài quiz-only, sơ đồ mermaid phụ thuộc 15 module, bảng module ↔ mục roadmap gốc (★ cho phần thêm), **bảng tổng quan công cụ** (Excel/Sheets, SQL, Python, R, Metabase, Superset, Power BI, Tableau, Looker, Streamlit: dùng khi nào, mạnh, yếu), phần ngoài phạm vi theo spec mục 2.
- [ ] **Step 3: `capstone/README.md`**: bối cảnh dunnhumby, câu hỏi xuyên suốt, schema 8 bảng (mermaid ER), định nghĩa dùng chung (doanh thu ròng = `SALES_VALUE` + giảm giá theo tài liệu bộ dữ liệu — builder kiểm tài liệu bộ và ghi đúng; basket = `BASKET_ID`; hộ = `household_key`), các con số tham chiếu (số dòng, số hộ, số tuần) lấy từ dữ liệu đã tải, danh sách 7 milestone gợi ý ở spec mục 7 (chưa có tệp milestone), ánh xạ 5 tình huống đề Drive (địa lý → nhân khẩu học).
- [ ] **Step 4: Kiểm app**: `cd app && pnpm build`; `pnpm dev` thấy track Data Analyst có 15 module, chỉ 08 có nội dung sau Task 4.
- [ ] **Step 5: Commit** — `git commit -m "Track Data Analyst: khai báo 15 module, README và capstone dunnhumby"`

### Task 4: Lý thuyết + interview module 08

**Files:**
- Create: `tracks/data-analyst/modules/08-visualization-chart-reading/README.md`, `.../interview.md`

- [ ] **Step 1: `README.md`** — 8 phần `## `:
  1. Nhắc lại nhanh (matplotlib/seaborn, EDA — link `data-science/09-eda-storytelling`)
  2. Chart trả lời câu hỏi gì: so sánh, xu hướng, phân phối, thành phần, quan hệ, luồng (funnel) → bảng chọn chart cho đủ 8 loại roadmap (bar, line, scatter, funnel, histogram, stacked, heatmap, pie)
  3. Nguyên tắc hiển thị: pre-attentive attributes, data-ink, sắp xếp, nhãn trực tiếp, màu (categorical/sequential/diverging), chú thích
  4. Chart gây hiểu nhầm: trục cắt, dual axis, pie nhiều lát, 3D, diện tích sai tỉ lệ, chọn khoảng thời gian, kỳ chưa đủ dữ liệu, Simpson's paradox, tổng vs trung bình
  5. Đọc chart như một DA: quy trình 5 bước (đọc trục và đơn vị → hình dạng tổng → điểm bất thường → so sánh với kỳ/nhóm khác → câu hỏi tiếp theo), phân biệt quan sát và kết luận
  6. Từ chart tới câu chuyện: headline là insight, small multiples, annotation, thứ tự chart trong slide/dashboard
  7. Chọn công cụ vẽ: matplotlib vs seaborn vs plotly vs Excel vs BI (Metabase/Superset/Power BI/Tableau) — bảng dùng khi nào, mạnh, yếu
  8. Tài liệu tham khảo (link mục Data Visualisation/Charting trong PDF roadmap + Cole Nussbaumer Knaflic "Storytelling with Data", Claus Wilke "Fundamentals of Data Visualization")
  ≥2 mermaid (cây chọn chart theo câu hỏi; quy trình đọc chart). Code mẫu chạy được trên Bike Sharing / Online Retail II.
- [ ] **Step 2: `interview.md`** — ≥14 câu: chọn chart cho từng tình huống; vì sao tránh pie; dual axis khi nào chấp nhận được; đọc một chart doanh thu giảm (case); Simpson's paradox; mean vs median trên chart; log scale; dashboard bị chê "rối" sửa thế nào; chọn matplotlib/plotly/BI; ≥3 câu case ("CEO thấy chart doanh thu tháng này giảm 40%", "chart A/B test đã cắt trục y", "trình bày funnel cho PM").
- [ ] **Step 3: Kiểm** — mọi khối ` ```python ` trong README chạy được bằng `uv run python` khi đã tải dữ liệu; đếm `## ` interview ≥ 14.
- [ ] **Step 4: Commit** — `git commit -m "Module 08 trực quan hoá & đọc biểu đồ: lý thuyết và câu hỏi phỏng vấn"`

### Task 5: Bài Basic (3 bài)

**Files:** dưới `tracks/data-analyst/modules/08-visualization-chart-reading/`
- `exercises/basic/01-chart-chooser/{README.md,quiz.yaml}`, `solutions/basic/01-chart-chooser/{SOLUTION.md,quiz-answers.yaml}` — **quiz-only**
- `exercises/basic/02-bike-chart-types/{README.md,quiz.yaml,starter/bike_charts.ipynb,tests/test_bike_charts.py}`, `solutions/basic/02-bike-chart-types/{SOLUTION.md,bike_charts.ipynb,quiz-answers.yaml}`
- `exercises/basic/03-order-value-distribution/{README.md,quiz.yaml,starter/order_values.ipynb,tests/test_order_values.py}`, `solutions/...` tương ứng

**Interfaces (hàm trong cell chấm; nhận/trả `pd.DataFrame` / `pd.Series`):**
- 01: 10–12 câu `knowledge`: tình huống → loại chart; tình huống → công cụ (matplotlib/seaborn/plotly/Excel/BI). `SOLUTION.md` giải thích từng câu.
- 02 (Bike Sharing `hour.csv`): `daily_rides(hour) -> Series` (index ngày, tổng `cnt`); `rides_by_season(hour) -> Series` (nhãn mùa tiếng Anh `spring/summer/fall/winter`, sắp giảm dần); `weekday_hour_matrix(hour) -> DataFrame` (7×24, trung bình `cnt`, dùng cho heatmap); `casual_share_by_month(hour) -> DataFrame` (tỉ trọng casual/registered theo tháng, dùng cho stacked). Cell `explore` vẽ line, bar, heatmap, stacked. Quiz 6–8 câu (giờ cao điểm ngày thường vs cuối tuần, mùa cao nhất, tháng casual cao nhất…).
- 03 (Online Retail II): `invoice_totals(tx) -> Series` (tổng `Quantity*Price` mỗi hoá đơn, **bỏ hoá đơn huỷ `C…` và dòng Quantity ≤ 0 hoặc Price ≤ 0**); `summary_stats(s) -> dict` khoá `mean, median, p90, p99, skew`; `log_bins(s, n: int) -> np.ndarray` (biên bin cách đều trên log10). Explore: histogram tuyến tính vs log, boxplot, ECDF. Quiz: mean vs median, chart nào làm rõ đuôi dài.

- [ ] **Step 1: Test thất bại** cho 02 và 03 trên fixture nhỏ sinh trong test, ví dụ:

```python
def test_invoice_totals_excludes_cancel_and_negative():
    tx = pd.DataFrame({"Invoice": ["1", "1", "C2", "3", "4"], "Quantity": [2, 1, -1, 5, 3], "Price": [1.5, 2.0, 9.0, 0.0, 1.0]})
    assert nb.invoice_totals(tx).to_dict() == {"1": 5.0, "4": 3.0}
def test_weekday_hour_matrix_shape(): shape == (7, 24), giá trị đúng trên fixture 2 ngày
def test_rides_by_season_sorted_desc(): index[0] == mùa có tổng lớn nhất trong fixture
```

Thêm một test `real_data` mỗi bài dùng `ex.dataset(...)`, ghim số tham chiếu (ví dụ tổng `cnt` 2011 vs 2012, số hoá đơn hợp lệ) với dung sai nhỏ.
- [ ] **Step 2:** `uv run pytest <bài> -q` → FAIL (starter `NotImplementedError`), không ERROR.
- [ ] **Step 3: Viết đề, starter, lời giải notebook, `SOLUTION.md`, quiz** (đáp án câu `data` tính từ lời giải trên dữ liệu thật; tuân quy tắc độ dài).
- [ ] **Step 4:** `SOLUTION=1 uv run pytest <bài> -q` → PASS; `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q` → PASS; lời giải chạy được bằng `uv run jupyter nbconvert --to notebook --execute --stdout <nb> > /dev/null`.
- [ ] **Step 5: Commit** — `git commit -m "Module 08: 3 bài Basic (chọn chart, các loại chart Bike Sharing, phân phối giá trị đơn)"`

### Task 6: Bài Intermediate (3 bài)

**Files:** `exercises/intermediate/{01-misleading-chart-audit,02-retail-chart-reading,03-simpson-and-funnel}/…` + `solutions/…` cùng cấu trúc notebook như Task 5.

**Interfaces:**
- 01 `chart_audit.ipynb`: `audit_chart(fig: matplotlib.figure.Figure) -> set[str]` trả các mã lỗi trong `{"truncated_bar_axis", "dual_axis", "pie_too_many_slices", "unsorted_bars", "missing_axis_label"}` (bar ylim > 0 ở gốc; figure có trục twin; pie > 6 lát; bar category không sắp theo giá trị khi trục x là danh mục; trục thiếu nhãn). `honest_bar(ax, s: pd.Series) -> Axes` vẽ bar sắp giảm dần, y từ 0, có nhãn trục. Test dựng figure nhỏ cho từng lỗi và kiểm `audit_chart(honest_bar(...).figure) == set()`. Explore: 4 chart "xấu" vẽ từ dữ liệu thật để người học soi. Quiz `knowledge` 6 câu.
- 02 `retail_reading.ipynb` (Online Retail II): `monthly_revenue(tx) -> Series` (theo `InvoiceDate` tháng, đã làm sạch như Basic 03); `country_share(tx, top: int) -> Series` (tỉ trọng, gộp còn lại vào `"Other"`, tổng = 1); `month_coverage(tx) -> Series` (số ngày có giao dịch mỗi tháng, để phát hiện tháng thiếu dữ liệu). Quiz `data` 7–8 câu đọc từ chart (tháng đỉnh, tỉ trọng UK, tháng 12/2011 thiếu dữ liệu nên "giảm" là giả…).
- 03 `simpson_funnel.ipynb`: Simpson trên số liệu tuyển sinh UC Berkeley 1973 (bảng 6 khoa đã công bố trong Bickel et al. 1975, ghi nguồn, nhập làm hằng trong notebook): `admit_rate(df, by: list[str]) -> Series`; `simpson_flip(df) -> bool` (tỉ lệ gộp và tỉ lệ theo khoa đảo chiều). Funnel trên Olist thật (`orders`): `order_funnel(orders) -> Series` các bước `purchased → approved → carrier → delivered` (đếm đơn có timestamp tương ứng không null), `step_conversion(funnel) -> Series`. Quiz trộn `data`/`knowledge`.

- [ ] **Step 1–5:** như Task 5 (test thất bại trên fixture → FAIL → viết bài → `SOLUTION=1` PASS + quiz test PASS + nbconvert lời giải → commit `git commit -m "Module 08: 3 bài Intermediate (soi chart gây hiểu nhầm, đọc chart Online Retail, Simpson và funnel)"`).

### Task 7: Bài Advanced (2 bài) + kiểm tổng module

**Files:**
- `exercises/advanced/01-revenue-drop-investigation/{README.md,starter/investigation.ipynb,starter/MEMO.md,tests/test_investigation.py}`, `solutions/advanced/01-revenue-drop-investigation/SOLUTION.md`
- `exercises/advanced/02-redesign-for-stakeholder/{README.md,starter/redesign.ipynb,starter/MEMO.md,tests/test_redesign.py}`, `solutions/advanced/02-redesign-for-stakeholder/SOLUTION.md`
- Create: `tests/test_da_module08.py`

**Interfaces:**
- 01: stakeholder báo "doanh thu tháng 12/2011 giảm mạnh so với 11/2011, vì sao?" trên Online Retail II. Người học điều tra bằng chart (độ phủ ngày, theo quốc gia, theo khách mới/cũ, theo sản phẩm), viết `MEMO.md` (headline, 3 chart, kết luận, việc cần làm). Test (Advanced, tự skip khi không `SOLUTION`… theo cơ chế sẵn có) kiểm `MEMO.md` có đủ heading bắt buộc. `SOLUTION.md`: hướng làm (bẫy kỳ chưa đủ dữ liệu — dữ liệu chỉ tới 9/12/2011; so sánh cùng số ngày; trừ mùa vụ), rubric.
- 02: starter vẽ sẵn "bộ chart xấu" từ Bike Sharing cho COO (pie, dual axis, bảng số dày); người học thiết kế lại 1 trang storytelling + `MEMO.md`. `SOLUTION.md` rubric (headline là insight, chart đúng loại, annotation, thứ tự, bỏ chart thừa).
- `tests/test_da_module08.py`: mọi bài trong module có `README.md` frontmatter hợp lệ (`level` khớp thư mục); bài quiz-only có `quiz.yaml` + `quiz-answers.yaml` + `SOLUTION.md`; bài Basic/Intermediate có lời giải trùng tên với tệp `starter/`; notebook commit không có output.

- [ ] **Step 1:** viết `tests/test_da_module08.py` → chạy, FAIL ở các bài Advanced chưa có.
- [ ] **Step 2:** viết 2 bài Advanced.
- [ ] **Step 3: Kiểm tổng**: `uv run pytest tracks/data-analyst -q` (starter: FAIL/skip, không ERROR); `SOLUTION=1 uv run pytest tracks/data-analyst -q` (Basic/Intermediate PASS); `uv run pytest tests -q`; `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science -q` cùng kết quả như trước plan; `cd app && pnpm test && pnpm typecheck && pnpm build`.
- [ ] **Step 4: Kiểm tay trong app** (Task 1 Step 6) và mở một notebook starter trong Jupyter chạy toàn bộ khi đã tải dữ liệu.
- [ ] **Step 5: Commit** — `git commit -m "Module 08: 2 bài Advanced (điều tra doanh thu giảm, thiết kế lại chart cho COO) và test kiểm module"`
