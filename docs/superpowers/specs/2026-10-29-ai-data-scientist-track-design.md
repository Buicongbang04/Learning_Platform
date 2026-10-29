# Thiết kế: track AI & Data Scientist

Ngày: 2026-10-29. Nguồn: [roadmap.sh/ai-data-scientist](https://roadmap.sh/ai-data-scientist)
(bản PDF chi tiết ở `ai-data-scientist.pdf` gốc repo).

## 1. Mục đích và lý do

Người học đang theo hướng Data Engineer (track `data-engineer` đã xong). Track này **bổ sung**,
không thay thế: học để (a) làm được việc của Data Scientist khi công việc cần, và (b) đủ sức phỏng
vấn vị trí DS / AI-ML khi có cơ hội. Chuẩn nhắm tới là **làm được thật trong doanh nghiệp, tới mức
senior**, không dừng ở "biết khái niệm".

Người học: đã dùng Python/pandas/SQL ở mức Analyst/DS, đã học SQL nâng cao trong track DE. Đọc
tiếng Việt, giữ thuật ngữ tiếng Anh. Máy: Linux, 16 core, 31GB RAM, GPU RTX 3050 Laptop 4GB.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Lấp placeholder `tracks/data-science` thành track `active`, theo đúng `CONTENT_SPEC.md`.
- Phủ hết 8 node roadmap gốc (Mathematics, Statistics, Econometrics, Coding, EDA, Machine Learning,
  Deep Learning, MLOps) và mọi mục con trong PDF (gồm cụm A/B testing: MDE, CUPED, CUPAC,
  stratification, ratio metrics / delta method).
- Bổ sung phần roadmap đã thiếu so với DS senior hiện nay (đánh dấu ★ ở mục 4).
- Bài tập làm trên notebook như thực tế, nhưng vẫn chấm tự động bằng pytest.

**Ngoài phạm vi**
- MLOps sâu (CI/CD cho model, drift monitoring đầy đủ, feature store): để cho track `mlops`.
- Ứng dụng LLM (RAG, agent, prompt engineering): để cho track `ai-engineer`.
- Rust, Go: không dạy ở track này. Module 14 chỉ giới thiệu ONNX và việc service Rust/Go/C++ gọi
  model; học ngôn ngữ thật để cho track `mlops`/`devops` hoặc track riêng sau này.
- R: không dùng. Chỉ Python.
- Dạy lại Python/SQL cơ bản: không, trỏ sang `data-engineer/01-foundations`.

**Điều cấm (làm vậy là hỏng dù chạy được)**
- Nội dung chỉ ở mức định nghĩa, không có quyết định thực tế (khi nào dùng, đánh đổi, lỗi hay gặp).
- Bài tập mà test không kiểm được đúng/sai thật (ví dụ chỉ kiểm hàm có chạy).
- Test phụ thuộc GPU, mạng, hay bộ Olist đầy đủ.
- Phá vỡ track DE hoặc app hiện có.

## 3. Ràng buộc

- Cấu trúc thư mục, frontmatter bài tập, interview, capstone: đúng `CONTENT_SPEC.md`.
- Mỗi module: 5–8 phần lý thuyết (`## `), ≥2 sơ đồ mermaid, phần cuối là tài liệu tham khảo (dùng
  các link trong PDF roadmap làm gốc); `interview.md` ≥12 câu, có câu product sense / case study;
  khoảng 7 bài tập (3 Basic, 2–3 Intermediate, 2 Advanced). Tổng ~105 bài.
- Starter chạy test phải fail (hoặc skip), không lỗi cú pháp; `SOLUTION=1` pass với Basic và
  Intermediate; Advanced chỉ có `SOLUTION.md` (hướng làm + rubric).
- Python 3.12, quản lý bằng `uv` (thêm dependency vào `pyproject.toml`).

## 4. Danh sách module (đã chốt)

| # | id | Module | Gốc roadmap |
| --- | --- | --- | --- |
| 01 | `01-math-for-ml` | Toán cho ML: linear algebra, calculus, optimization, gradient descent tự viết | Mathematics |
| 02 | `02-probability-statistics` | Xác suất & thống kê suy luận: distributions, CLT, sampling, estimation, bootstrap, Bayesian cơ bản | Statistics |
| 03 | `03-ab-testing` | Hypothesis testing & A/B testing: thiết kế thí nghiệm, power, MDE, multiple testing, SRM, peeking | Statistics |
| 04 | `04-advanced-experimentation` | CUPED, CUPAC, stratification, ratio metrics & delta method, novelty, network effect | Statistics |
| 05 | `05-econometrics-regression` | OLS & giả định, GLM, fitting distributions, panel data | Econometrics |
| 06 | `06-causal-inference` ★ | DiD, synthetic control, IV, RDD, propensity score, uplift | mở rộng Econometrics |
| 07 | `07-time-series` | ARIMA, ETS, ML với lag feature, backtesting, hierarchical forecasting | Econometrics |
| 08 | `08-coding-for-ds` | DSA cho phỏng vấn, SQL dạng phỏng vấn DS (window, funnel, retention), pandas/polars hiệu năng | Coding |
| 09 | `09-eda-storytelling` | EDA, visualization, data storytelling | EDA |
| 10 | `10-feature-engineering` ★ | Leakage, encoding, sklearn Pipeline, CV theo thời gian / nhóm | mở rộng ML |
| 11 | `11-classic-ml` | Supervised/unsupervised, metrics, tuning, imbalanced, calibration, interpretability (SHAP) | Machine Learning |
| 12 | `12-advanced-ml` | Ensembles, XGBoost/LightGBM, ★ recommender systems, ★ anomaly detection | Machine Learning |
| 13 | `13-deep-learning` | PyTorch: MLP, CNN, RNN/LSTM, Transformers, transfer learning, ★ embeddings | Deep Learning |
| 14 | `14-mlops-for-ds` | MLflow, đóng gói model, serve FastAPI, monitoring cơ bản, giới thiệu ONNX | MLOps |
| 15 | `15-ml-system-design` ★ | Đóng khung bài toán, chọn metric, ML system design, trình bày cho business, case phỏng vấn | mở rộng |

Topic con chi tiết của từng module, tên và nội dung từng bài tập: để builder quyết, miễn phủ đủ các
mục trên và mục con trong PDF.

## 5. Notebook và cách chấm (đã chốt)

- Bài EDA / modeling: starter là `starter/<tên>.ipynb`. Người học điền các cell có `TODO` (định
  nghĩa hàm hoặc gán biến kết quả). Bài thuần logic (ví dụ tự cài một kiểm định): vẫn `.py` như cũ.
- Test chạy toàn bộ notebook rồi lấy hàm / biến từ namespace để kiểm. Thêm vào `testkit.Exercise`
  một phương thức `notebook("x.ipynb")` cùng tinh thần với `module()` (cùng cơ chế `SOLUTION=1`,
  cùng hành vi skip cho Advanced). Thêm `nbclient` / `nbformat` / `ipykernel` vào dependency.
- Lời giải Basic/Intermediate: notebook trùng tên trong `solutions/…`, kèm `SOLUTION.md`.
- Notebook starter nên có cell khám phá (biểu đồ, in dữ liệu) bên cạnh cell chấm điểm; test không
  được phụ thuộc vào output biểu đồ.
- App chỉ cần liệt kê tệp `.ipynb` trong `files:` và lệnh mở (`uv run jupyter lab …` hoặc mở bằng
  VS Code) trong `run:`. Không bắt buộc app render notebook.

## 6. Deep learning (đã chốt)

Bài DL thiết kế để train vài phút trên RTX 3050 (4GB). Test dùng dữ liệu và model cực nhỏ, chạy
CPU được, không đòi CUDA. Dataset chuẩn từ torchvision (FashionMNIST…) chỉ dùng trong notebook
thực hành, không dùng trong test (test không cần mạng).

## 7. Dữ liệu (đã chốt)

**Nguyên tắc: dữ liệu thật càng nhiều càng tốt.** Mỗi bộ dữ liệu có insight và cái "bẩn" riêng;
người học phải quen làm với dữ liệu thật. Không tự sinh dữ liệu để thay dữ liệu thật trong notebook.
Không sửa `data/generate_olist.py` (track DE giữ nguyên).

- **Notebook thực hành và capstone dùng bộ thật**: Olist thật từ Kaggle (`data/download_olist.py`
  đã có) là xương sống cho EDA, feature engineering, classic ML, forecasting, NLP review, capstone.
  Module nào Olist không phù hợp thì chọn bộ thật khác, ưu tiên bộ **có đáp số đã công bố** để
  chấm được. Gợi ý (builder kiểm tra còn tải được và giấy phép trước khi dùng, được thay bằng bộ
  tương đương):
  - A/B testing: bộ A/B thật công khai (ví dụ Cookie Cats, Udacity ab_data, marketing A/B).
  - Causal: LaLonde/NSW (có kết quả thí nghiệm ngẫu nhiên làm chuẩn), Prop 99 California
    (synthetic control), dữ liệu IV/RDD kinh điển (ví dụ Card 1995).
  - Time series: Olist số đơn theo ngày; thêm bộ có seasonality rõ (ví dụ Rossmann / M5) nếu cần.
  - Recommender: MovieLens. Anomaly: credit card fraud. Deep learning: FashionMNIST / CIFAR-10;
    NLP: review Olist.
- **Mỗi bộ có script tải** trong `data/` (cùng phong cách `download_olist.py`), ghi vào
  `data/raw/<bộ>/` (không commit), ghi rõ nguồn, giấy phép, cách lấy Kaggle token. Bảng tổng hợp
  các bộ trong `data/README.md`.
- **Chấm điểm**:
  - Hàm cài đặt phương pháp (kiểm định, CUPED, estimator…) được test trên fixtures nhỏ. Fixtures là
    mẫu trích từ bộ thật khi giấy phép cho phép (ghi nguồn), nếu không thì dữ liệu nhỏ sinh trong
    test. Một số thuộc tính toán học (ví dụ "CUPED giảm variance", "phát hiện SRM", độ phủ của
    confidence interval) được kiểm bằng mô phỏng nhỏ trong test; đây là công cụ kiểm chứng, không
    phải dữ liệu học.
  - Kết quả phân tích trên bộ thật: kiểm so với đáp số đã công bố (trong khoảng hợp lý) khi có;
    còn lại là bài Advanced chấm bằng rubric.
  - Test không cần mạng, không cần bộ dữ liệu đầy đủ: phần chạy trên bộ thật tự skip khi chưa tải.

## 8. Capstone: "Olist Customer Experience" (đã chốt)

Milestone gắn với module (`after`), cùng format capstone DE. Code ở `capstone/project/`.

1. EDA và định nghĩa metric (sau 09)
2. Dự báo nhu cầu (sau 07)
3. Model dự đoán đơn có nguy cơ review xấu (sau 11/12)
4. Causal analysis: tác động của giao trễ lên review (sau 06)
5. Thiết kế A/B test cho can thiệp với đơn rủi ro: metric, power, MDE, CUPED tính từ baseline
   thật của Olist, kèm kế hoạch phân tích (sau 03/04). Olist không có dữ liệu thí nghiệm nên
   milestone này dừng ở thiết kế và pre-registration; kỹ năng phân tích đã luyện trên bộ A/B thật
   ở module 03/04.
6. Đóng gói model bằng MLflow, serve qua FastAPI (sau 14)
7. Memo trình bày cho stakeholder (sau 15)

Gán `after` cụ thể và thứ tự milestone: builder quyết sao cho mỗi milestone chỉ cần kiến thức của
các module trước đó.

## 9. Cách giao (đã chốt)

1. Hạ tầng: testkit hỗ trợ notebook, dependency mới, script tải bộ dữ liệu cho module mẫu, `track.json` (status `active`, tên hiển thị
   "AI & Data Scientist", `source` trỏ roadmap), `README.md` của track với sơ đồ mermaid, capstone
   README.
2. **Một module mẫu: `03-ab-testing`**, đầy đủ lý thuyết, interview, bài tập, lời giải. Người học
   duyệt văn phong, độ khó, trải nghiệm notebook.
3. Sau khi duyệt mới soạn hàng loạt các module còn lại và capstone milestones.

## 10. Để builder quyết

Cấu trúc nội bộ của `notebook()` trong testkit; tên bài tập; chọn thư viện cụ thể trong mỗi
module (statsmodels, scikit-learn, lightgbm, shap, torch, mlflow, fastapi…) miễn phổ biến trong
ngành; thứ tự soạn các module sau module mẫu.
