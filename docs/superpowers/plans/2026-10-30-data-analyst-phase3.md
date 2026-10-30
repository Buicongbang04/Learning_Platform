# Data Analyst track: 14 module còn lại + capstone — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện track `data-analyst`: hạ tầng cho bài Excel/BI/Streamlit, 14 module còn lại (01–07, 09–15) cùng chuẩn với module mẫu 08 (đã được người học duyệt), và capstone dunnhumby gồm 7 milestone.

**Architecture:** Task 1–3 là hạ tầng (app, testkit + dữ liệu, dịch vụ BI). Task 4–17 mỗi task là **một module độc lập** (chỉ tạo tệp trong thư mục module), chạy tuần tự, implementer tự commit. Task 18 là capstone. Task 19 kiểm tổng.

**Tech Stack:** Python 3.12, uv, pytest, nbformat, pandas, duckdb, matplotlib/seaborn/plotly, openpyxl + LibreOffice headless, streamlit (`streamlit.testing`), dbt-duckdb, scipy/statsmodels, scikit-learn, Docker (Postgres, Metabase, Superset); app Vite + React + TS.

**Spec:** `docs/superpowers/specs/2026-10-29-data-analyst-track-design.md` (mục 2–9). Plan giai đoạn 1–2 đã xong và merge (PR #4): `docs/superpowers/plans/2026-10-29-data-analyst-phase1-2.md`.

**Mẫu chuẩn (gold standard):** `tracks/data-analyst/modules/08-visualization-chart-reading/`. Mọi module mới đọc module này trước và đạt cùng chuẩn: độ sâu, văn phong, cấu trúc đề, quiz, `SOLUTION.md`, test dùng dữ liệu thật, số liệu kiểm trên dữ liệu thật.

## Global Constraints

- Đúng `CONTENT_SPEC.md` (gồm "Bài tập notebook", "Dữ liệu thật", "Bài chỉ có trắc nghiệm", quy tắc quiz và quy tắc độ dài đáp án, LaTeX chỉ `$$...$$`).
- Mỗi module:
  - `README.md`: 5–8 phần `## `, ≥ 2 mermaid, phần cuối "Tài liệu tham khảo" (lấy link trong `roadmap/data-analyst.pdf` làm gốc; link phải `curl -L` ra 200, trang chặn bot thì bỏ). Kiến thức trùng track DE/DS: **tối đa một** phần `## ` nhắc lại, có link module gốc. Có **bảng so sánh công cụ** cho các công cụ module đụng tới (dùng khi nào, mạnh, yếu, loại công ty hay dùng). Mọi khối ` ```python ` chạy được.
  - `interview.md`: ≥ 14 câu `## `, ≥ 3 câu case study / product sense, ≥ 1 câu "vì sao chọn công cụ này".
  - 7 bài: 3 Basic, 2 Intermediate, 2 Advanced (được 3 Intermediate). Bài notebook có dữ liệu thật thì có `quiz.yaml`. Ít nhất 1 bài dạng "chọn công cụ" hoặc đọc chart/đọc số (quiz) mỗi module.
- Tiếng Việt, giữ thuật ngữ tiếng Anh. Chuẩn DA senior: bối cảnh business (stakeholder hỏi gì), quyết định thực tế, đánh đổi, lỗi hay gặp.
- **Bài tập không chép/đổi tên bài track DE/DS**, kể cả khi cùng kiến thức (đặt trong bối cảnh DA: câu hỏi business → số, bảng, chart, khuyến nghị).
- **Dữ liệu thật** cho notebook, ví dụ và workbook. Không số bịa làm dữ liệu học; ví dụ giả định phải ghi rõ "ví dụ giả định". Ngoại lệ duy nhất: bài "nghi ngờ dữ liệu" ở module 06 dùng bộ Grocery Sales synthetic. Mọi con số trong nội dung tính lại từ dữ liệu trước khi viết.
- Workbook `.xlsx` commit vào repo chỉ chứa trích mẫu từ bộ có giấy phép cho phép phân phối lại (CC BY 4.0 như Online Retail II, Bike Sharing), ghi nguồn trong sheet `README` của workbook và trong đề.
- R chỉ giới thiệu (module 04), không có bài R bắt buộc. Power BI/Tableau/Looker chỉ khái niệm + so sánh.
- Starter chạy test: chỉ FAIL hoặc SKIP, 0 ERROR. `SOLUTION=1`: Basic/Intermediate PASS; Advanced chỉ có `SOLUTION.md` (hướng làm + quyết định + rubric có điểm) và tự SKIP; mỗi bài Advanced có ≥ 1 hàm được test trên fixture, kiểm bằng bản tham chiếu trong scratch (không commit).
- Test offline, không cần Docker trừ khi gọi `ex.require_service(...)` (tự skip), mỗi bài < 30 giây (bài đọc xlsx lớn được tới 60 giây).
- Task 4–18 không sửa `testkit.py`, app, `pyproject.toml`, `data/download_dataset.py`, `setup/`, track DE/DS, module 08. Thiếu gì ở hạ tầng thì báo NEEDS_CONTEXT để người điều phối quyết.
- Cổng Docker: máy có project khác dùng 5432/6379/9000/9001; dùng giá trị trong `setup/.env`. Không chạy lệnh phá huỷ dữ liệu trên cổng mặc định.
- Commit tiếng Việt, **không có dòng Co-Authored-By**. Không push.

## Review Focus

1. Bài Excel: người học mở workbook bằng LibreOffice, điền công thức, lưu → test đọc được giá trị đã tính. Người học gõ cứng số thay vì công thức → test FAIL với thông báo rõ. Máy không có `soffice` → test SKIP, không ERROR. Test trong Task 2.
2. Bài BI khi Metabase/Superset chưa bật → SKIP với hướng dẫn lệnh bật; khi bật lần đầu (Metabase chưa setup admin) → helper tự setup hoặc báo rõ. Test trong Task 3.
3. Bài quiz trên bài code / bài Excel (không phải notebook) → app hiện thẻ trắc nghiệm dưới Workspace; tệp `.xlsx` trong `files:` → app không mở như text, có cách mở ngoài. Test trong Task 1.
4. Hai module nói khác nhau về cùng định nghĩa (doanh thu ròng Online Retail, khách hàng mới/cũ, retention) → dùng "Định nghĩa dùng chung" dưới đây.
5. Số trong lý thuyết lệch với số test ghim hoặc đáp án quiz → mỗi module task đối chiếu mọi con số trong markdown với output thật.

## Định nghĩa dùng chung (mọi module dùng y hệt)

- **Online Retail II, dòng hợp lệ**: bỏ `Invoice` bắt đầu bằng `C`, bỏ dòng `Quantity <= 0` hoặc `Price <= 0`; `Invoice` ép `str`. **Doanh thu** = `Quantity * Price` trên dòng hợp lệ (doanh thu gộp; nói rõ khi bàn tới hoá đơn bị huỷ sau đó, xem module 08 Advanced 01). Đọc cả hai sheet thì bỏ trùng 2010-12-01..09. Dữ liệu kết thúc 2011-12-09 (tháng 12/2011 chưa đủ).
- **Khách hàng**: `Customer ID` khác null; khách mới trong tháng = tháng của hoá đơn hợp lệ đầu tiên. **Cohort** theo tháng mua đầu; **retention tháng k** = tỉ lệ khách của cohort có ≥ 1 hoá đơn hợp lệ ở tháng thứ k sau tháng đầu.
- **dunnhumby**: theo `tracks/data-analyst/capstone/README.md` (doanh thu, basket = `BASKET_ID`, hộ = `household_key`).
- **Bike Sharing**: nhãn mùa theo UCI Readme (1 = spring) kèm lưu ý dữ liệu thực tế (module 08).

---

### Task 1: App — quiz trên mọi bài, tệp `.xlsx`

**Files:**
- Modify: `app/server/workspace.ts` (`isText` và đọc tệp starter), `app/src/code/Workspace.tsx`, `app/src/pages/ExercisePage.tsx`, `app/src/code/NotebookPanel.tsx` (`QuizCard` dùng lại), `CONTENT_SPEC.md`
- Test: `app/server/workspace.test.ts` (tạo mới nếu chưa có), `app/src/code/*.test.ts`

**Interfaces:**
- Produces: bài `"code"` có `quiz.yaml` → dưới Workspace có `QuizCard` (variant mặc định "optional" nếu bài có test, "main" nếu bài chỉ có `.xlsx` không có test — builder chọn tiêu chí rõ ràng và ghi trong CONTENT_SPEC). Bài không có `quiz.yaml` → không đổi gì.
- Produces: tệp nhị phân (`.xlsx`, `.xlsm`, `.ods`, `.docx`, `.pdf`, ảnh) trong `starter/` không được trả về như text; Workspace hiện dòng "tệp nhị phân — mở bằng LibreOffice/Excel" kèm đường dẫn để chép. Có nút mở bằng ứng dụng mặc định (`xdg-open`) hay không: builder quyết, nếu có thì giới hạn trong thư mục `starter/` của bài.
- Bài notebook, bài `.py` DE/DS hiện có: hành vi giữ nguyên.

- [ ] **Step 1:** Test thất bại: `isText("starter/sales.xlsx") === false`; API đọc bài có `starter/sales.xlsx` trả mục `{ path, binary: true }` không có `content`; hàm quyết định hiện quiz cho bài code trả đúng theo có/không `quiz.yaml`.
- [ ] **Step 2:** `cd app && pnpm test` → FAIL.
- [ ] **Step 3:** Cài đặt; cập nhật `CONTENT_SPEC.md` (mục mới "Bài Excel" và "Quiz trên bài không phải notebook").
- [ ] **Step 4:** `pnpm test && pnpm typecheck && pnpm build` → PASS. Kiểm bằng `pnpm dev` + curl API trên một bài tạm trong scratch (không commit bài tạm).
- [ ] **Step 5:** Commit `App: quiz trên bài code/Excel, tệp .xlsx là tệp nhị phân`.

### Task 2: Testkit cho bài Excel, dependency, bộ dữ liệu cho 14 module

**Files:**
- Modify: `testkit.py`, `tests/test_testkit_workbook.py` (mới), `pyproject.toml`, `uv.lock`, `data/download_dataset.py` (chỉ thêm vào `DATASETS`), `data/README.md`, `tests/test_download_dataset.py`

**Interfaces:**
- Produces: `Exercise.workbook(name: str) -> WorkbookView` dùng chung cơ chế `path()` (SOLUTION=1, skip Advanced). `WorkbookView` có:
  - `formula(sheet: str, cell: str) -> str | None` (chuỗi công thức nếu ô là công thức, ví dụ `"=VLOOKUP(A2,Products!A:B,2,0)"`, ngược lại `None`)
  - `value(sheet: str, cell: str) -> Any` (giá trị **đã tính lại**: chép workbook sang thư mục tạm, `soffice --headless --convert-to xlsx` để LibreOffice tính lại, rồi `openpyxl.load_workbook(data_only=True)`; cache theo mtime). Không có `soffice` → `pytest.skip("Cần LibreOffice (soffice) để tính lại công thức")`.
  - `sheetnames: list[str]`, `pivot_tables(sheet) -> list` (đọc `ws._pivots` của openpyxl, đủ để kiểm có pivot và nguồn dữ liệu).
- Produces: dependency (chỉ thêm cái chưa có): `beautifulsoup4`, `lxml`, `mlxtend` (association rules), `requests` đã có. Kiểm `dbt-duckdb`, `streamlit`, `scikit-learn`, `statsmodels` đã có.
- Produces: khoá `DATASETS` mới — ứng viên dưới đây phải **tải thử thật**, ghi số dòng; không tải được hoặc giấy phép cấm thì thay bằng bộ tương đương thật và ghi ruling vào report:

| Tên | Ứng viên | Module |
| --- | --- | --- |
| `grocery-sales-synthetic` | 7 CSV từ thư mục Google Drive người học đưa (folder `1rtawsOtllVE3FUwRZx7slywGLLU7mvol`, tệp tải qua `https://drive.usercontent.google.com/download?id=<id>&export=download&confirm=t`; id: categories `1B4APzkcF4KaslMHx8GsUOuptVzeyKL2d`, cities `1WZbxCNXar-fgbX-2AiDQDyaplFlLuc8H`, countries `1De6c9O4z3mtXFmdjtil0U25_ohhan4tM`, customers `1GG7hYlvJGgnUtGNCbKFGBPnLkD45KFfV`, employees `1rJt_kMT6AwNIpPQTKYqQprG0O8DOH7k_`, products `1kxQM4Utt5QwVU7wRpVKPn2L8nLaq6uyD`, sales `1gE2sah4dLh0a4sXSA-1bqaf-Rn5XvNGO` ~517 MB). Giấy phép: "không rõ — chỉ dùng cục bộ, không commit trích mẫu" | 06, 09 |
| `marketing-ab` | bộ A/B marketing thật **khác** các bộ DS đã dùng (cookie-cats, ab-data, hillstrom), ví dụ Kaggle `chebotinaa/fast-food-marketing-campaign-ab-test` hoặc `faviovaz/marketing-ab-testing`; chọn bộ có giấy phép ghi rõ | 11 |
| `ecommerce-events` | sự kiện web thật cho funnel (view → cart → purchase), ví dụ Kaggle `mkechinov/ecommerce-events-history-in-cosmetics-shop` (một tháng là đủ) | 12 |
| `instacart` hoặc dùng `online-retail-ii` | market basket; nếu Instacart giấy phép không rõ thì dùng Online Retail II | 12 |
| `owid-co2` hoặc `world-bank-wdi` | dữ liệu công khai CC BY (Our World in Data CSV trên GitHub) cho pandas/R đối chiếu | 04 |
| `books-toscrape` | không cần registry: trang `books.toscrape.com` (sandbox cho scraping); test dùng HTML lưu trong `tests/fixtures` do module 05 tự tạo bằng cách tải 1–2 trang (trang sandbox cho phép) | 05 |

  Bộ đã có dùng lại thoải mái: `online-retail-ii`, `bike-sharing-uci`, `dunnhumby-complete-journey` (chỉ capstone + ví dụ ngắn), `store-sales`, `telco-churn`, `open-meteo`, Olist.

- [ ] **Step 1:** Test thất bại cho `workbook()` trên fixture xlsx tạo trong test (openpyxl ghi công thức `=SUM(A1:A3)` và một ô gõ cứng): `formula` đúng, `value` trả 6 sau khi tính lại, ô gõ cứng có `formula is None`; SOLUTION=1 trỏ sang `solutions/`; giả lập không có `soffice` (monkeypatch `shutil.which`) → skip.
- [ ] **Step 2:** `uv run pytest tests/test_testkit_workbook.py -q` → FAIL. Cài đặt → PASS.
- [ ] **Step 3:** Thêm dependency + từng bộ dữ liệu; tải thật; `uv run pytest tests -q` PASS; `SOLUTION=1 uv run pytest tracks -q` không giảm số pass.
- [ ] **Step 4:** `data/README.md` cập nhật; commit `Hạ tầng DA: testkit workbook(), dữ liệu và thư viện cho 14 module`.

### Task 3: Dịch vụ BI cho module 10 (Metabase + Superset)

**Files:**
- Modify: `setup/docker-compose.yml` (thêm `superset`, profile `bi`), `setup/SETUP.md`, `setup/.env.example` nếu có, `testkit.py` (`_port`, `service_up` biết `superset`), `CONTENT_SPEC.md` (bảng dịch vụ)
- Create: `setup/bi/` (script khởi tạo Superset admin + kết nối DuckDB/Postgres; script setup Metabase admin qua `/api/setup` nếu chưa setup), `tests/test_bi_services.py`

**Interfaces:**
- Produces: `superset` cổng `${SUPERSET_PORT:-8088}`, admin `admin`/`admin`; Metabase admin cố định `admin@example.com` / mật khẩu ghi trong SETUP (tạo bằng script). Python helper `setup/bi/clients.py` với `metabase_session() -> requests.Session` và `superset_session() -> requests.Session` (đăng nhập, CSRF), để test module 10 gọi API.
- Dữ liệu cho BI: Postgres sẵn có (`${POSTGRES_PORT}`), script nạp bảng mẫu từ Online Retail II / Bike Sharing vào schema `da` (`uv run python setup/bi/load_da.py`).

- [ ] **Step 1:** Thêm service, bật `docker compose -f setup/docker-compose.yml --profile bi up -d metabase superset postgres`, chạy script khởi tạo, nạp dữ liệu.
- [ ] **Step 2:** `tests/test_bi_services.py`: `require_service` → skip khi tắt; khi bật: login hai công cụ được, liệt kê database thấy `da`. Chạy khi bật → PASS; tắt → SKIP.
- [ ] **Step 3:** Tắt dịch vụ sau khi kiểm (`docker compose ... stop superset metabase`), không xoá volume. Commit `Dịch vụ BI: Superset + script khởi tạo Metabase/Superset, nạp dữ liệu DA`.

### Task 4–17: Mỗi module một task

Mỗi task dùng **cùng một quy trình**. Nội dung bắt buộc và dữ liệu ở bảng sau.

**Files (mỗi module `<id>`):** chỉ tạo trong `tracks/data-analyst/modules/<id>/` (`README.md`, `interview.md`, `exercises/…`, `solutions/…`).

**Interfaces:**
- Consumes: `testkit.Exercise` (`module`, `notebook`, `dataset`, `read`, `path`, `workbook` từ Task 2, `require_service`), helper BI từ Task 3 (module 10), tên bộ dữ liệu từ Task 2 (đọc `data/README.md`), "Định nghĩa dùng chung". `track.json` đã khai báo `title`, `summary`, `topics`: nội dung khớp, không sửa `track.json`.

- [ ] **Step 1: Đọc mẫu.** `CONTENT_SPEC.md`; module 08 (README, interview, ít nhất 1 bài mỗi loại kèm lời giải và quiz); hàng của module trong bảng dưới; module gốc ở track DE/DS nếu có phần nhắc lại (để không chép bài).
- [ ] **Step 2: Tính số liệu thật** cho mọi con số sẽ nêu; script trong scratch, không commit.
- [ ] **Step 3: Lý thuyết + interview.** Kiểm: đếm `## `, mermaid, chạy mọi khối python (`MPLBACKEND=Agg`), curl mọi link, không có `$` đơn.
- [ ] **Step 4: Bài tập, test trước.** Viết `tests/` rồi starter. `uv run pytest <module>/exercises -q` → chỉ FAIL/SKIP, 0 ERROR.
- [ ] **Step 5: Lời giải** Basic/Intermediate trùng tên starter + `SOLUTION.md` + `quiz-answers.yaml`. `SOLUTION=1 uv run pytest <module>/exercises -q` → PASS (Advanced SKIP). Mỗi notebook lời giải chạy được bằng `uv run jupyter nbconvert --to notebook --execute --stdout <nb> > /dev/null`. `UV_NO_SYNC=1 uv run pytest tests/test_quiz_files.py -q` PASS.
- [ ] **Step 6: Advanced** kiểm bằng bản tham chiếu trong scratch; `SOLUTION.md` có rubric chấm điểm.
- [ ] **Step 7: Commit** `Module <NN> <tên ngắn>: lý thuyết, phỏng vấn, 7 bài`. Báo cáo: danh sách tệp, output các lệnh trên, các con số chính, ruling.

| Task | Module | Nội dung bắt buộc (ngoài `topics` trong `track.json`) | Dữ liệu thật | Gợi ý bài (builder quyết tên, chi tiết) |
| --- | --- | --- | --- | --- |
| 4 | `01-analyst-mindset` | Vai trò DA vs DS vs DE vs BI, 4 loại analytics (descriptive, diagnostic, predictive, prescriptive), Key Concepts of Data (collection, cleanup, exploration, visualisation, statistical analysis, ML), đặt câu hỏi business (đóng khung, giả thuyết), KPI & metric tree, north star, leading vs lagging, **bản đồ công cụ** tổng quan | Online Retail II (metric tree doanh thu = khách × tần suất × AOV), Bike Sharing | Quiz-only: phân loại câu hỏi vào 4 loại analytics; quiz-only "chọn công cụ" theo tình huống; notebook: dựng metric tree và phân rã thay đổi doanh thu theo thành phần (tháng vs tháng); Advanced: biến yêu cầu mơ hồ của stakeholder thành analysis plan |
| 5 | `02-spreadsheets` | Mọi hàm roadmap: IF, DATEDIF, VLOOKUP/HLOOKUP, REPLACE/SUBSTITUTE, UPPER/LOWER/PROPER, CONCAT, TRIM, AVERAGE, COUNT, SUM, MIN/MAX; thêm XLOOKUP/INDEX-MATCH, SUMIFS/COUNTIFS, pivot table, chart, data validation, conditional formatting; Excel vs Google Sheets vs LibreOffice (khác biệt hàm, giới hạn dòng); khi nào bỏ spreadsheet sang SQL/Python | Trích mẫu Online Retail II / Bike Sharing (CC BY 4.0) đóng vào `.xlsx` | Bài `.xlsx` dùng `ex.workbook()`: làm sạch văn bản (TRIM/PROPER/SUBSTITUTE), lookup giá/sản phẩm, SUMIFS báo cáo doanh thu, DATEDIF tuổi khách/kỳ, pivot + chart; quiz "Excel hay SQL/Python"; Advanced: dựng báo cáo tuần có kiểm lỗi (rubric) |
| 6 | `03-sql-for-analysts` | Nhắc lại SQL nâng cao (link DE); câu hỏi business → SQL: YoY/MoM, running total, top-N theo nhóm, cohort retention, funnel, so sánh kỳ chưa đủ ngày, NULL và join làm nhân bản dòng, kiểm tra kết quả (reconcile) | Online Retail II trong DuckDB; dunnhumby (bảng nhỏ: `hh_demographic`, `campaign_*`) | `.sql` chấm bằng DuckDB: doanh thu MoM với kỳ chưa đủ; top 3 sản phẩm mỗi quốc gia; cohort retention; phát hiện join nhân bản doanh thu; Advanced: trả lời 3 câu hỏi CEO bằng SQL + memo ngắn |
| 7 | `04-python-for-analysts` | pandas cho DA (groupby, merge, reshape, time series resample), matplotlib/seaborn nhanh; **R giới thiệu**: dplyr/ggplot2 đối chiếu từng thao tác với pandas/seaborn (bảng); git cho notebook/SQL (nbstripout, review diff), cấu trúc project phân tích tái lập được (data/raw → processed, notebooks, src, README) | `owid-co2` hoặc `world-bank-wdi`, Online Retail II | Reshape wide↔long và tỉ lệ tăng trưởng theo nước; hàm báo cáo tái dùng có test; quiz đọc code R → kết quả pandas tương đương; Advanced: tổ chức lại một notebook rối thành project tái lập (rubric + test cấu trúc) |
| 8 | `05-data-collection` | Databases (SQLAlchemy, Postgres/SQLite), CSV (encoding, delimiter, dtype), APIs (REST, phân trang, rate limit, retry, API key an toàn), Web scraping (robots.txt, HTML parsing, đạo đức/pháp lý), lưu dữ liệu thô có metadata | Open-Meteo API (không cần key), World Bank API, books.toscrape.com, Online Retail II | Đọc CSV bẩn encoding/delimiter; client API có phân trang + retry (test bằng `responses`/mock server cục bộ, không mạng); scraper BeautifulSoup trên HTML fixture; nạp vào SQLite và truy vấn; Advanced: pipeline thu thập hằng ngày có log + idempotent |
| 9 | `06-data-cleaning` | Missing (MCAR/MAR/MNAR, khi nào drop/impute), duplicates (exact vs fuzzy), outliers (IQR, z, nghiệp vụ), transformation (type, chuẩn hoá chuỗi, ngày, đơn vị), thư viện cleanup pandas (và dplyr đối chiếu), data quality checks, log các bước làm sạch | Online Retail II (huỷ, giá 0, mã lạ, thiếu khách), Bike Sharing, **Grocery Sales synthetic** cho bài nghi ngờ dữ liệu | Hàm làm sạch có log số dòng bị loại theo lý do; dedupe fuzzy tên sản phẩm; outlier theo nghiệp vụ vs thống kê; **bài "nghi ngờ dữ liệu"**: chứng minh Grocery Sales là synthetic (TotalPrice=0, mỗi TransactionNumber 1 dòng, Quantity đều 1–25, phân phối phẳng) bằng kiểm định + chart, kết luận "không báo cáo insight"; Advanced: data quality report cho bộ mới |
| 10 | `07-descriptive-eda` | Central tendency (mean, median, mode, average), dispersion (range, variance, SD, IQR), distribution (skewness, kurtosis), generating statistics, visualizing distributions; quy trình EDA có câu hỏi; trọng số và trung bình của trung bình | Bộ thật khác module 08 nếu được (ví dụ `telco-churn`, `store-sales`, Olist), Online Retail II | Tự viết thống kê mô tả có trọng số và so với pandas; khi mean lừa (lệch phải, outlier); EDA có câu hỏi + quiz đọc số; Advanced: EDA report 1 trang |
| 11 | `09-analytics-data-modeling` | Star schema, fact/dimension, grain, SCD (nhắc DE), dbt (nhắc DE) với dbt-duckdb, metric/semantic layer, data quality test (dbt tests), tài liệu hoá định nghĩa metric | Online Retail II → star schema; Grocery Sales chỉ dùng làm schema quan hệ để thiết kế (không lấy insight) | Xác định grain + vẽ star schema (quiz + test DDL DuckDB); dbt project nhỏ (staging → mart) chạy `dbt build` trong test; metric definitions YAML + test hai báo cáo ra cùng con số; Advanced: thiết kế mart cho câu hỏi marketing |
| 12 | `10-bi-dashboards` | Tableau/Power BI/Looker: khái niệm (data model, measure/DAX, LookML) + so sánh; thực hành **Metabase, Superset, Streamlit/Plotly**; thiết kế KPI dashboard (người dùng, câu hỏi, layout, filter, drill-down), refresh/caching, self-serve vs ad-hoc | Bảng `da` nạp ở Task 3 (Online Retail II, Bike Sharing) | Metabase: tạo question/dashboard qua API (test kiểm bằng API, skip khi tắt); Superset: dataset + chart qua API; Streamlit app chấm bằng `streamlit.testing.v1.AppTest`; quiz "chọn công cụ BI"; Advanced: dashboard spec + bản dựng trên công cụ tự chọn (rubric) |
| 13 | `11-stats-experimentation` | Nhắc lại hypothesis testing, correlation, regression (link DS 02/03/05); DA thiết kế A/B: metric chính, guardrail, sample size/MDE, thời lượng, SRM; đọc kết quả và ra quyết định; correlation ≠ causation, DiD nhanh; regression để giải thích (không dự báo) | `marketing-ab` (Task 2), Bike Sharing (regression thời tiết → lượt thuê), Online Retail II | Tính sample size + thời lượng từ baseline thật; phân tích A/B marketing (SRM, CI, quyết định); regression có diễn giải hệ số; quiz đọc output A/B; Advanced: experiment brief + readout cho stakeholder |
| 14 | `12-product-customer-analytics` | Funnel, cohort, retention, LTV (đơn giản và theo cohort), CAC/payback (ví dụ giả định ghi rõ), RFM segmentation, market basket (support, confidence, lift), tracking plan / event instrumentation | `ecommerce-events` (funnel), Online Retail II (cohort, RFM, basket), `instacart` nếu dùng | Funnel theo phiên từ event thật; cohort retention matrix + heatmap; RFM scoring + segment; association rules với mlxtend; Advanced: tracking plan cho một tính năng + phân tích phân khúc |
| 15 | `13-business-financial-analytics` | Root cause khi chỉ số biến động (phân rã mix/rate, drill-down), P&L cơ bản, gross margin, unit economics, phân tích giá/khuyến mãi (elasticity đơn giản, cannibalization), dự báo xu hướng doanh số (seasonal naive, moving average, ETS ở mức DA), scenario/what-if, giám sát KPI (anomaly, ngưỡng, alert) | `store-sales` (doanh số + khuyến mãi), Online Retail II, Bike Sharing | Phân rã thay đổi doanh thu thành price/volume/mix; dự báo 8 tuần + backtest đơn giản; anomaly KPI theo ngày với ngưỡng mùa vụ; what-if bảng kịch bản; Advanced: điều tra một chỉ số giảm và đề xuất hành động (memo) |
| 16 | `14-ml-bigdata-for-analysts` | ML types (supervised, unsupervised, reinforcement — khái niệm), thuật toán roadmap (Decision Trees, Naive Bayes, KNN, K-Means, Logistic Regression) ở mức dùng và đọc kết quả, model evaluation (train/test, confusion matrix, khi nào accuracy lừa); Deep Learning giới thiệu (NN, CNN, RNN, TF vs PyTorch, image recognition, NLP); Big Data concepts, storage, Hadoop/Spark, parallel processing, MPI, MapReduce (nhắc DE, link) | `telco-churn`, Online Retail II (k-means trên RFM), Bike Sharing | Logistic regression churn + đọc hệ số cho business; k-means segment + đặt tên segment; tự viết MapReduce đếm từ/doanh thu bằng multiprocessing và so với pandas; quiz "khi nào DA nên/không nên làm ML"; Advanced: đề xuất model churn cho stakeholder (rubric) |
| 17 | `15-stakeholder-storytelling-interview` | Nhận yêu cầu mơ hồ, scoping, ưu tiên (impact/effort), self-serve vs ad-hoc; storytelling (SCQA, headline là kết luận), memo, slide; dùng AI/LLM khi phân tích và cách kiểm lại (không gửi dữ liệu nhạy cảm); take-home, case interview, SQL live; portfolio, Kaggle, networking (phần cuối roadmap) | Online Retail II, Bike Sharing (để viết memo từ phân tích có sẵn) | Quiz-only: chọn câu hỏi làm rõ cho yêu cầu mơ hồ; quiz-only: chấm headline tốt/xấu; viết memo từ notebook cho sẵn (test cấu trúc + rubric); Advanced: take-home mô phỏng 3 giờ (đề + rubric); Advanced: kế hoạch portfolio |

### Task 18: Capstone dunnhumby — 7 milestone

**Files:**
- Create: `tracks/data-analyst/capstone/milestones/m01-….md` … `m07-….md`, `tracks/data-analyst/capstone/project/README.md`
- Modify: `tracks/data-analyst/capstone/README.md` (link milestone), `tracks/data-analyst/track.json` (thêm khoá `capstone`)

**Interfaces:**
- Consumes: capstone README hiện có (5 tình huống, định nghĩa, số tham chiếu), module 03, 06, 07, 09, 10, 11, 12, 13, 15.
- Produces: `capstone` trong `track.json`: `title`, `readme: "capstone/README.md"`, `milestones[{id, title, after, doc}]` theo bảng:

| id | Tiêu đề | after |
| --- | --- | --- |
| m01 | Nạp dữ liệu, làm sạch, data dictionary | `06-data-cleaning` |
| m02 | Trả lời tình huống 1–4 bằng SQL | `07-descriptive-eda` |
| m03 | Star schema và định nghĩa metric dùng chung | `09-analytics-data-modeling` |
| m04 | Dashboard Metabase/Superset và Streamlit | `10-bi-dashboards` |
| m05 | RFM, cohort retention, market basket, nhân khẩu học | `12-product-customer-analytics` |
| m06 | Hiệu quả campaign/coupon | `13-business-financial-analytics` |
| m07 | Memo và thuyết trình cho ban điều hành | `15-stakeholder-storytelling-interview` |

- [ ] **Step 1:** Viết từng milestone theo `CONTENT_SPEC.md` (`## Mục tiêu`, `## Việc cần làm`, `## Kết quả nộp`, `## Tiêu chí đạt`), dẫn chiếu bài liên quan, dùng số tham chiếu đã kiểm (tính lại nếu nêu số mới). m06 nói rõ giới hạn: campaign không ngẫu nhiên → không kết luận nhân quả mạnh.
- [ ] **Step 2:** Cập nhật capstone README (mermaid milestone, cấu trúc `capstone/project/`), thêm `capstone` vào `track.json`. `cd app && pnpm build` PASS; `pnpm dev` + curl thấy 7 milestone.
- [ ] **Step 3:** Commit `Capstone dunnhumby: 7 milestone`.

### Task 19: Kiểm tổng track

- [ ] **Step 1:** `uv run pytest tracks/data-analyst -q` (starter: FAIL/SKIP, 0 ERROR); `SOLUTION=1 uv run pytest tracks/data-analyst -q` (0 FAIL); `uv run pytest tests -q`; `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science -q` cùng số với `origin/main` (baseline trong worktree tạm, xoá sau); `cd app && pnpm test && pnpm typecheck && pnpm build`.
- [ ] **Step 2:** Cập nhật `tracks/data-analyst/README.md` (bỏ câu "module 08 là module mẫu làm trước", số bài thực tế), `README.md` gốc nếu có bảng track.
- [ ] **Step 3:** Commit `Track Data Analyst: hoàn thiện 15 module và capstone`.
