# Thiết kế: track Data Analyst

Ngày: 2026-10-29. Nguồn: [roadmap.sh/data-analyst](https://roadmap.sh/data-analyst)
(bản PDF ở `roadmap/data-analyst.pdf`).

## 1. Mục đích và lý do

Người học muốn **học và thực hành để làm được việc của Data Analyst**, vững kiến thức và kỹ năng
trước khi đi phỏng vấn vị trí DA. Chuẩn nhắm tới là **DA senior**, không dừng ở mức junior của
roadmap.sh ("thừa hơn thiếu").

Người học đã xong track `data-engineer` (SQL nâng cao, dbt, Spark…) và đã có track `data-science`
(thống kê, A/B testing, ML, EDA). Vì vậy:

- **Kiến thức trùng track cũ chỉ nhắc lại ngắn** những điểm quan trọng cần nhớ, rồi trỏ về module
  gốc. Track này **chủ yếu là bài tập**.
- **Bài tập phải khác bài của track cũ** dù kiến thức giống. Bài DA đặt trong bối cảnh công việc DA:
  có câu hỏi business từ stakeholder, trả lời bằng số liệu, bảng, chart và khuyến nghị. Track DS thì
  thiên về xây model và suy luận nhân quả.

Hai điểm người học tự thấy yếu, cần chạy xuyên suốt track chứ không gom vào một chỗ:

1. **Biết công dụng của từng công cụ**: khi nào dùng Excel, SQL, Python, R, Metabase, Superset,
   Power BI, Tableau, Looker, Streamlit, và điểm mạnh yếu của từng cái.
2. **Kỹ năng phân tích và đọc biểu đồ.**

Người học đọc tiếng Việt, giữ thuật ngữ tiếng Anh. Máy Linux, Docker, uv, LibreOffice có sẵn.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Lấp placeholder `tracks/data-analyst` thành track `active`, theo đúng `CONTENT_SPEC.md`.
- Phủ mọi mục trong PDF roadmap, cộng các phần một DA senior cần mà roadmap thiếu (★ ở mục 4).
- Mỗi module có **bảng so sánh công cụ** cho các công cụ module đó đụng tới (dùng khi nào, mạnh gì,
  yếu gì, loại công ty hay dùng). Có bài tập dạng **"chọn công cụ"** theo tình huống.
- Luyện đọc biểu đồ bằng nhiều dạng: đọc chart ra insight, phát hiện chart gây hiểu nhầm, chọn chart
  đúng cho câu hỏi, điều tra chỉ số (root cause).

**Ngoài phạm vi**
- **R chỉ giới thiệu**: đối chiếu dplyr/ggplot2 với pandas/seaborn trong lý thuyết module 04. Không
  có bài tập R bắt buộc, không thêm R vào môi trường.
- **Power BI, Tableau, Looker**: chỉ dạy khái niệm (data model, measure/DAX, LookML) và so sánh.
  Không có bài thực hành bắt buộc trên các công cụ này (Power BI Desktop không chạy trên Linux).
- Deep Learning, Big Data: chỉ giới thiệu, trỏ về track DS và DE.
- Dạy lại từ đầu những gì track DE/DS đã dạy: không.

**Điều cấm (làm vậy là hỏng dù chạy được)**
- Bài tập chép lại hoặc đổi tên bài của track DE/DS.
- Nội dung chỉ ở mức định nghĩa, không có quyết định thực tế (khi nào dùng, đánh đổi, lỗi hay gặp).
- Dùng dữ liệu sinh ngẫu nhiên làm dữ liệu học. Dữ liệu phẳng dạy sai kỹ năng đọc chart (chart nào
  cũng "phẳng"). Ngoại lệ duy nhất là bài "nghi ngờ dữ liệu" ở mục 6.
- Test không kiểm được đúng/sai thật, hoặc test phụ thuộc mạng, Docker đang chạy, hay bộ dữ liệu đầy đủ
  mà không tự skip.
- Phá vỡ track DE, DS hoặc app hiện có.

## 3. Ràng buộc

- Cấu trúc thư mục, frontmatter bài tập, interview, capstone, notebook, quiz: đúng `CONTENT_SPEC.md`.
- Mỗi module: 5–8 phần lý thuyết (`## `), ≥2 sơ đồ mermaid, phần cuối là tài liệu tham khảo (lấy
  link trong PDF roadmap làm gốc). Phần nhắc lại kiến thức trùng track cũ chỉ chiếm **một phần**
  `## ` (ví dụ `## 1. Nhắc lại nhanh`), có link tới module gốc.
- `interview.md` ≥12 câu, có câu case study / product sense / "vì sao chọn công cụ này".
- Khoảng 7 bài mỗi module (3 Basic, 2–3 Intermediate, 2 Advanced). Tổng khoảng **100 bài**.
- Starter chạy test phải fail (hoặc skip), không lỗi cú pháp. `SOLUTION=1` pass với Basic và
  Intermediate. Advanced chỉ có `SOLUTION.md` (hướng làm + rubric).
- Bài notebook có dữ liệu thật thì có **trắc nghiệm** (`quiz.yaml` + `quiz-answers.yaml`) theo quy
  ước hiện có. Câu đọc chart là câu `kind: data`, đáp án cố định trên dữ liệu đã ghim.
- Python 3.12, `uv`. Dịch vụ Docker mới thêm vào `setup/docker-compose.yml`. Cổng bị trùng thì remap
  qua `setup/.env` như đang làm. **Không chạy lệnh phá huỷ** trên cổng mặc định 5432/6379/9000/9001
  (máy có project khác dùng các cổng đó).

## 4. Danh sách module (đã chốt)

| # | id | Module | Gốc roadmap / nội dung chính |
| --- | --- | --- | --- |
| 01 | `01-analyst-mindset` | Vai trò DA & tư duy phân tích | Introduction, Key Concepts, 4 loại analytics (descriptive, diagnostic, predictive, prescriptive); đặt câu hỏi business, KPI, metric tree; **bản đồ công cụ** tổng quan |
| 02 | `02-spreadsheets` | Excel / Spreadsheet | Mọi hàm trong roadmap (IF, DATEDIF, VLOOKUP/HLOOKUP, REPLACE/SUBSTITUTE, UPPER/LOWER/PROPER, CONCAT, TRIM, AVERAGE, COUNT, SUM, MIN/MAX), XLOOKUP, pivot table, charting; Excel vs Google Sheets vs LibreOffice |
| 03 | `03-sql-for-analysts` | SQL cho DA | Learn SQL. Nhắc lại từ DE. Bài theo câu hỏi business: YoY/MoM, running total, top-N theo nhóm, cohort, funnel, so sánh kỳ |
| 04 | `04-python-for-analysts` | Python cho DA | Programming (pandas, matplotlib, seaborn); **R giới thiệu** (dplyr/ggplot2 đối chiếu); ★ git cho notebook/SQL, cấu trúc project phân tích tái lập được |
| 05 | `05-data-collection` | Thu thập dữ liệu | Databases, CSV, APIs, Web Scraping |
| 06 | `06-data-cleaning` | Làm sạch dữ liệu | Missing data, duplicates, outliers, data transformation, thư viện cleanup; **bài "nghi ngờ dữ liệu"** (mục 6) |
| 07 | `07-descriptive-eda` | Thống kê mô tả & EDA | Central tendency, dispersion, distribution (skewness, kurtosis), generating statistics, visualizing distributions; **Exploration (EDA)** |
| 08 | `08-visualization-chart-reading` | Trực quan hoá & đọc biểu đồ | Charting (bar, line, scatter, funnel, histogram, stacked, heatmap, pie), matplotlib/seaborn/plotly; chọn chart theo câu hỏi; chart gây hiểu nhầm; đọc chart ra insight. **Trọng tâm** |
| 09 | `09-analytics-data-modeling` ★ | Data modeling cho analytics | Star schema, fact/dimension, grain; dbt (nhắc lại từ DE); metric/semantic layer; data quality test; tài liệu hoá định nghĩa metric |
| 10 | `10-bi-dashboards` | BI & Dashboard | Tools (Tableau, Power BI): khái niệm và so sánh; thực hành **Metabase, Superset, Streamlit/Plotly**; thiết kế KPI dashboard |
| 11 | `11-stats-experimentation` | Thống kê & Experimentation cho quyết định | Hypothesis testing, correlation, regression (nhắc lại từ DS); ★ thiết kế A/B test từ phía DA (metric, guardrail, sample size), đọc kết quả; correlation ≠ causation, DiD nhanh |
| 12 | `12-product-customer-analytics` ★ | Product & customer analytics | Funnel, cohort, retention, LTV, CAC, RFM segmentation, market basket analysis (association rules), tracking plan / event instrumentation |
| 13 | `13-business-financial-analytics` ★ | Business & financial analytics | Root cause khi chỉ số biến động, P&L, margin, unit economics, phân tích giá/khuyến mãi, dự báo xu hướng doanh số, scenario/what-if, giám sát KPI (anomaly, alert) |
| 14 | `14-ml-bigdata-for-analysts` | ML & Big Data cho DA | Advanced Topics: ML types (supervised, unsupervised, reinforcement), thuật toán trong roadmap (Decision Trees, Naive Bayes, KNN, K-Means, Logistic Regression), model evaluation; Deep Learning giới thiệu (NN, CNN, RNN, TensorFlow/PyTorch, image recognition, NLP); Big Data concepts, storage, Hadoop/Spark, parallel processing, MPI, MapReduce. Ngắn, phần lớn nhắc lại |
| 15 | `15-stakeholder-storytelling-interview` ★ | Stakeholder, storytelling & phỏng vấn | Nhận yêu cầu mơ hồ, scoping, ưu tiên, self-serve vs ad-hoc; storytelling, memo, trình bày; dùng AI/LLM khi phân tích và cách kiểm tra lại; take-home, case interview; portfolio, Kaggle, networking (phần cuối roadmap) |

Topic con chi tiết, tên và nội dung từng bài: để builder quyết, miễn phủ đủ các mục trên.

## 5. Dạng bài tập và cách chấm (đã chốt)

Giữ cơ chế đang có: `.py` cho bài thuần logic, notebook (`ex.notebook`) cho bài phân tích, quiz trong
app cho phần đọc/diễn giải. Thêm các dạng sau:

- **Bài Excel (`.xlsx`)**: starter là workbook có ô trống đánh dấu TODO. Người học điền công thức
  bằng LibreOffice Calc (hoặc Excel). Test đọc bằng `openpyxl`, kiểm cả **giá trị** lẫn việc ô đó
  **là công thức** (không gõ cứng số). Lời giải là workbook trùng tên trong `solutions/`, có giá trị
  đã tính sẵn. Cách lấy giá trị đã tính (giá trị cache do LibreOffice lưu, hay tính lại bằng
  LibreOffice headless) do builder quyết. Test phải tự skip, không lỗi, nếu thiếu thứ nó cần.
- **Bài BI (Metabase, Superset)**: dịch vụ chạy bằng Docker (Superset thêm vào compose, profile `bi`
  cùng Metabase). Bài Basic/Intermediate chấm được bằng API của công cụ (sau `ex.require_service`)
  hoặc bằng file export. Bài khó đo tự động thì là Advanced chấm bằng rubric. Luân phiên công cụ
  giữa các bài để người học trải nghiệm cả ba.
- **Bài Streamlit**: chấm bằng `streamlit.testing` (AppTest), không cần mở trình duyệt.
- **Bài đọc chart**: notebook vẽ chart từ dữ liệu thật trong cell `explore`, quiz hỏi về chart đó
  (xu hướng, so sánh, điểm bất thường, chart sai ở đâu). Chart gây hiểu nhầm có thể là ảnh tĩnh do
  bài cung cấp.
- **Bài "chọn công cụ"**: quiz theo tình huống (`kind: knowledge`), kèm giải thích trong `SOLUTION.md`.
- **Bài viết insight / memo**: Advanced, rubric trong `SOLUTION.md`.

**Được sửa app (người học đã đồng ý)** để các dạng bài mới hiện đúng, với điều kiện giữ nguyên hành vi
của track DE/DS và có test cho phần sửa:
- Thẻ trắc nghiệm hiện cho **mọi bài có `quiz.yaml`**, không chỉ bài notebook. Có cả bài chỉ gồm quiz
  (ví dụ "chọn công cụ") không có starter code.
- `.xlsx` (và tệp nhị phân tương tự) được nhận là tệp nhị phân, không mở như text. Có nút mở bằng
  ứng dụng ngoài (LibreOffice) hay không: builder quyết.
- Cập nhật `CONTENT_SPEC.md` cho các dạng bài mới (Excel, BI, Streamlit, quiz-only).

## 6. Dữ liệu (đã chốt)

**Nguyên tắc: dữ liệu thật** (giống track DS). Mỗi module chọn bộ dữ liệu thật hợp chủ đề, ưu tiên đa
dạng ngành (retail, product/web, marketing, tài chính, dịch vụ công…). Không dùng lại Olist làm
xương sống. Mỗi bộ thêm vào registry `DATASETS` trong `data/download_dataset.py` và bảng
`data/README.md` (nguồn, giấy phép). Builder kiểm tra bộ còn tải được và giấy phép trước khi dùng.
Test trên dữ liệu thật tự skip khi chưa tải.

**Bộ "Grocery Sales Database"** (Kaggle; người học đưa bản trên Google Drive, đề "Bài 18: Sales of
FMCG Stores", 7 bảng, khoảng 6,7 triệu dòng sales). Đã kiểm trên 40 nghìn dòng đầu: `TotalPrice` = 0
ở 100% số dòng, mỗi `TransactionNumber` chỉ có 1 dòng (không tính được basket), `Quantity` rải đều
1–25, tên và địa chỉ khách là tên giả. Kết luận: **dữ liệu sinh ngẫu nhiên**. Chỉ dùng cho **một bài
ở module 06: "nghi ngờ dữ liệu"**: người học phát hiện bộ dữ liệu là synthetic và có lỗi, trước khi
báo cáo. Có thể dùng thêm cho bài thiết kế star schema ở module 09 nếu cần một schema quan hệ, nhưng
không lấy insight từ đó.

## 7. Capstone: dunnhumby "The Complete Journey" (đã chốt)

Dữ liệu **thật** của một chuỗi siêu thị (FMCG/grocery): khoảng 2,6 triệu dòng giao dịch trong 2 năm
của 2.500 hộ gia đình, 8 bảng quan hệ (transactions, products, household demographics, campaigns,
campaign descriptions, coupons, coupon redemptions, causal/promotions). Nguồn: Kaggle
`frtgnn/dunnhumby-the-complete-journey` (khoảng 130 MB, giấy phép Open Database License, đã kiểm
2026-10-29), tải tự động qua registry `DATASETS` bằng token Kaggle sẵn có.

Câu hỏi xuyên suốt: người học đóng vai DA của chuỗi siêu thị, trả lời ban điều hành về doanh thu,
khách hàng và hiệu quả marketing. Capstone phủ cả **5 tình huống của đề Drive** (doanh thu theo thời
gian và tỷ trọng ngành hàng; xếp hạng sản phẩm; phân khúc khách hàng, repeat vs one-time, AOV và
basket size; địa lý thay bằng phân tích theo nhóm nhân khẩu học vì bộ không có địa lý), cộng thêm
**hiệu quả campaign/coupon** và market basket.

Milestone gợi ý (builder gán `after` sao cho mỗi milestone chỉ cần kiến thức các module trước):

1. Nạp dữ liệu, làm sạch, data dictionary (sau 06)
2. Trả lời các câu hỏi business bằng SQL (sau 03 và 07)
3. Mô hình hoá star schema + định nghĩa metric dùng chung (sau 09)
4. Dashboard: một trên Metabase hoặc Superset, một trên Streamlit (sau 10)
5. Phân khúc RFM, cohort retention, market basket (sau 12)
6. Hiệu quả campaign/coupon, đọc như một thí nghiệm có giới hạn (sau 11 và 13)
7. Memo và bài thuyết trình cho ban điều hành (sau 15)

## 8. Cách giao (đã chốt)

Giống track DS:

1. **Hạ tầng**: `track.json` (status `active`, tên "Data Analyst", `source` trỏ roadmap, giữ
   `order: 2`), `README.md` của track với sơ đồ mermaid, capstone README, script tải dữ liệu cho
   module mẫu, các helper testkit hoặc dịch vụ Docker mà module mẫu cần.
2. **Module mẫu: `08-visualization-chart-reading`** (người học chọn), đầy đủ lý thuyết, interview,
   bài tập, lời giải, quiz. Người học duyệt văn phong, độ khó, trải nghiệm. Các phần sửa app (mục 5)
   mà module 08 cần (ví dụ bài quiz-only) làm ở bước này. Cơ chế chấm Excel và BI kiểm khi tới module
   02 và 10, ở bài đầu tiên của module đó.
3. Sau khi duyệt mới soạn các module còn lại và các milestone capstone.

## 9. Để builder quyết

Tên bài tập và nội dung cụ thể; bộ dữ liệu thật cho từng module; cơ chế nội bộ chấm Excel/BI/Streamlit;
thư viện cụ thể (plotly, mlxtend…) miễn phổ biến trong ngành; phiên bản Superset; thứ tự soạn các
module sau module mẫu.
