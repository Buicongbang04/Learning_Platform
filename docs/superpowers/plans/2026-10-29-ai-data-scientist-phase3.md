# AI & Data Scientist track: 14 module còn lại + capstone — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn thiện track `data-science`: soạn đủ 14 module còn lại (01, 02, 04–15) cùng chuẩn với module mẫu 03, và capstone "Olist Customer Experience" gồm 7 milestone.

**Architecture:** Không đổi app hay testkit, chỉ thêm nội dung. Task 1 chuẩn bị dữ liệu và dependency dùng chung. Task 2–15 mỗi task là **một module độc lập** (thư mục riêng, không tệp dùng chung), nên chạy song song được. Task 16 là capstone, cần nội dung các module đã xong.

**Tech Stack:** Python 3.12, uv, pytest, nbformat; numpy, pandas, scipy, statsmodels, scikit-learn, lightgbm, shap, linearmodels, torch/torchvision (CPU wheel trong test), mlflow, fastapi, onnx/onnxruntime/skl2onnx.

**Spec:** `docs/superpowers/specs/2026-10-29-ai-data-scientist-track-design.md` (mục 3–8). Plan giai đoạn 1–2 đã xong: `docs/superpowers/plans/2026-10-29-ai-data-scientist-phase1-2.md`.

**Mẫu chuẩn (gold standard):** `tracks/data-science/modules/03-ab-testing/`. Mọi module mới phải đọc module này trước và đạt cùng chuẩn: độ sâu, văn phong, cấu trúc đề bài, `SOLUTION.md`, cách test dùng dữ liệu thật.

## Global Constraints

- Đúng `CONTENT_SPEC.md`, gồm các mục "Bài tập notebook", "Dữ liệu thật" và quy ước LaTeX `$$...$$`.
- Mỗi module có:
  - `README.md`: 5–8 phần `## `, ≥ 2 sơ đồ mermaid, phần cuối là tài liệu tham khảo. Mọi link phải được kiểm (`curl -L` ra 200; trang chặn bot như medium.com thì bỏ). Mọi khối ` ```python ` phải chạy được.
  - `interview.md`: ≥ 14 câu `## `, trong đó ≥ 3 câu case study / product sense.
  - 8 bài tập: 3 Basic, 3 Intermediate, 2 Advanced. Ít nhất 2 bài là notebook.
- Tiếng Việt, giữ thuật ngữ tiếng Anh. Chuẩn senior: luôn có "khi nào dùng / đánh đổi / lỗi hay gặp", không dừng ở định nghĩa. Công thức viết LaTeX `$$...$$`, không viết trong khối code.
- Dữ liệu thật cho notebook và ví dụ. Mọi con số nêu trong nội dung phải tính lại từ dữ liệu hoặc từ code trước khi viết. Fixture của test sinh trong test; không commit dữ liệu tải về.
- Starter chạy test: chỉ FAIL hoặc SKIP, không ERROR (không gọi hàm của người học trong fixture). `SOLUTION=1`: Basic/Intermediate PASS; Advanced chỉ có `SOLUTION.md` (hướng làm + rubric có điểm) và tự SKIP. Test Advanced phải được kiểm bằng một bản cài đặt tham chiếu đặt ngoài repo (scratch), không commit.
- Test chạy offline, không GPU, mỗi bài < 30 giây; test mô phỏng phải ổn định qua nhiều seed (thử ≥ 10 seed trước khi chốt ngưỡng).
- Không sửa `testkit.py`, app, `data/generate_olist.py`, track DE hay module 03. Chỉ Task 1 được sửa `pyproject.toml`, `data/download_dataset.py`, `data/README.md`.
- Không commit trong lúc chạy song song: người điều phối commit từng module sau khi kiểm (tránh tranh chấp git index).

## Review Focus

1. Một module dùng bộ dữ liệu có trong registry nhưng tên tệp CSV khác thực tế: notebook `explore` lỗi khi người học chạy, dù test vẫn xanh vì test dùng fixture. Mỗi module task phải chạy trọn notebook lời giải bằng `nbconvert --execute`.
2. Import `torch` làm test chậm hoặc lỗi trên máy không có CUDA. Task 1 chốt cách cài; Task 14 kiểm test chạy được khi `CUDA_VISIBLE_DEVICES=""`.
3. Con số trong lý thuyết lệch với con số test ghim (như 14 731 / 14 749 ở module 03). Mỗi module task đối chiếu mọi con số trong markdown với output thật.
4. Hai module nói khác nhau về cùng một khái niệm (ví dụ định nghĩa "giao trễ", "review xấu", cách chia train/test theo thời gian của Olist). Dùng định nghĩa ở mục "Định nghĩa dùng chung" dưới đây.
5. Advanced chỉ kiểm "đã viết đủ chữ" mà không kiểm được gì thật. Mỗi bài Advanced phải có ít nhất một hàm được test trên fixture, cộng với tài liệu chấm theo rubric.

## Định nghĩa dùng chung cho Olist (mọi module dùng y hệt)

- **Đơn giao xong**: `order_status == "delivered"` và có `order_delivered_customer_date`.
- **Giao trễ**: so nguyên timestamp `order_delivered_customer_date > order_estimated_delivery_date`. Tỉ lệ: 8.1% đơn giao xong.
- **Review**: mỗi đơn giữ review có `review_answer_timestamp` mới nhất. **Review xấu**: `review_score <= 2`. Tỉ lệ: 12.8%; ở đơn trễ 54.1%.
- **Khách**: `customer_unique_id` (không phải `customer_id`).
- **Chia theo thời gian** cho mọi bài ML trên Olist: train là đơn mua trước 2018-01-01, validation từ 2018-01-01 tới trước 2018-04-01, test từ 2018-04-01 tới hết 2018-08-31. Bỏ đơn mua sau 2018-08-31 (đơn còn dở dang).
- **Traffic gần đây**: dùng giai đoạn 2017-06 tới 2018-07; trung vị khoảng 1 259 đơn giao xong mỗi tuần.

---

### Task 1: Dữ liệu và dependency dùng chung

**Files:**
- Modify: `pyproject.toml`, `uv.lock`, `data/download_dataset.py` (chỉ thêm vào `DATASETS`), `data/README.md` (bảng bộ dữ liệu)
- Test: `tests/test_download_dataset.py` (test registry hiện có phải vẫn pass)

**Interfaces:**
- Produces: các tên bộ dữ liệu trong `DATASETS` mà Task 2–16 dùng qua `ex.dataset("<tên>")` và `data/raw/<tên>/`. Ứng viên dưới đây phải được **tải thử thật**; nếu không tải được, hoặc là competition cần chấp nhận luật, hoặc giấy phép cấm dùng, thì thay bằng bộ tương đương và ghi ruling:

| Tên | Ứng viên | Module |
| --- | --- | --- |
| `lalonde` | NSW/PSID của Dehejia-Wahba (`https://users.nber.org/~rdehejia/data/`), cả mẫu thí nghiệm lẫn mẫu đối chứng quan sát | 06 |
| `prop99` | Dữ liệu thuốc lá theo bang của Abadie, Diamond, Hainmueller (2010) | 06 |
| `card` | Card (1995), dùng khoảng cách tới trường đại học làm IV | 06 |
| `store-sales` | Bộ doanh số theo ngày **không phải** competition (ví dụ Walmart / Rossmann bản dataset), có mùa vụ rõ | 07 |
| `telco-churn` | `blastchar/telco-customer-churn` | 11 |
| `movielens` | `ml-latest-small` từ grouplens.org | 12 |
| `creditcard-fraud` | `mlg-ulb/creditcardfraud` | 12 |

  Bộ dữ liệu sẵn trong thư viện thì dùng thẳng, không cần registry: `statsmodels.datasets` (grunfeld, macrodata, co2…), `torchvision.datasets.FashionMNIST`. Nếu Python package `causaldata` có đúng các bộ của module 06 và giấy phép rõ ràng thì được dùng nó thay cho registry.
- Produces: dependency mới trong `pyproject.toml`: `scikit-learn`, `lightgbm`, `shap`, `linearmodels`, `torch`, `torchvision`, `mlflow`, `fastapi`, `uvicorn`, `onnx`, `onnxruntime`, `skl2onnx`. `torch` lấy bản CPU qua `[tool.uv.sources]` / index `https://download.pytorch.org/whl/cpu`, để môi trường gọn và test chạy không cần CUDA. Trong README track, ghi cách đổi sang bản CUDA để train trên RTX 3050. Mọi phiên bản phải phát hành ít nhất 2 tuần trước 2026-10-29.

- [ ] **Step 1:** Thêm từng bộ vào `DATASETS`, chạy `uv run python data/download_dataset.py <tên>` cho từng bộ. Expected: tệp có trong `data/raw/<tên>/`, đếm số dòng và in header, ghi kết quả vào ledger.
- [ ] **Step 2:** `uv add ...` các dependency. Expected: `uv run python -c "import sklearn, lightgbm, shap, linearmodels, torch, torchvision, mlflow, fastapi, onnxruntime, skl2onnx; print(torch.__version__)"` không lỗi, và bản torch có hậu tố `+cpu`.
- [ ] **Step 3:** `uv run pytest tests -q` → PASS; `SOLUTION=1 uv run pytest tracks -q` → không giảm số pass so với trước (DS 62 pass, DE 529 pass).
- [ ] **Step 4:** Cập nhật bảng trong `data/README.md` (tên, nội dung, nguồn, giấy phép, module). Commit: `data: bộ dữ liệu thật và thư viện cho 14 module Data Science`.

### Task 2–15: Mỗi module một task

Mỗi task dùng **cùng một quy trình**. Danh sách module, nội dung bắt buộc và dữ liệu nằm ở bảng sau quy trình.

**Files (mỗi module `<id>`):**
- Create: `tracks/data-science/modules/<id>/README.md`, `interview.md`, `exercises/{basic,intermediate,advanced}/<NN-slug>/{README.md,starter/*,tests/*}`, `solutions/...`
- Không đụng tệp nào ngoài thư mục module.

**Interfaces:**
- Consumes: `testkit.Exercise` (`module`, `notebook`, `dataset`, `read`, `path`), tên bộ dữ liệu từ Task 1, định nghĩa dùng chung về Olist ở trên. `track.json` đã khai báo `id`, `title`, `summary`, `topics` của module: nội dung phải khớp, không đổi `track.json`.
- Produces: một module hoàn chỉnh mà app hiển thị được. Chỉ milestone capstone tương ứng (Task 16) đọc module này.

- [ ] **Step 1: Đọc mẫu.** Đọc `CONTENT_SPEC.md`, toàn bộ module 03 (README, interview, mỗi loại bài ít nhất một bài kèm lời giải), và mục của module này trong bảng dưới.
- [ ] **Step 2: Tính số liệu thật.** Chạy phân tích trên dữ liệu thật cho mọi con số sẽ nêu trong nội dung. Lưu script vào scratch, không commit.
- [ ] **Step 3: Lý thuyết + interview.** Viết `README.md` và `interview.md`. Kiểm: đếm `## `, số khối mermaid, chạy mọi khối python, curl mọi link.
- [ ] **Step 4: Bài tập, test trước.** Với mỗi bài, viết `tests/` trước, rồi starter. Chạy `uv run pytest <thư mục module>/exercises -q`. Expected: chỉ FAIL hoặc SKIP, 0 error.
- [ ] **Step 5: Lời giải.** Viết lời giải Basic/Intermediate (`.py` hoặc `.ipynb` trùng tên với starter) và `SOLUTION.md`. Chạy `SOLUTION=1 uv run pytest <thư mục module>/exercises -q`. Expected: PASS, chỉ SKIP ở Advanced. Chạy `uv run jupyter nbconvert --to notebook --execute --stdout <notebook lời giải> > /dev/null` cho từng notebook lời giải. Expected: không lỗi.
- [ ] **Step 6: Advanced.** Kiểm test Advanced bằng bản tham chiếu đặt trong scratch (pass), rồi viết `SOLUTION.md` có rubric chấm điểm.
- [ ] **Step 7: Kiểm KaTeX.** Render mọi tệp `.md` của module qua `remark-math` (`singleDollarTextMath: false`) + `rehype-katex`. Expected: 0 `katex-error`, 0 `$$` còn sót ngoài khối code.
- [ ] **Step 8: Báo cáo** cho người điều phối: danh sách tệp, kết quả các lệnh trên, các con số chính, và mọi quyết định lệch khỏi plan (ruling). Không commit.

| Task | Module | Nội dung bắt buộc (ngoài topics trong `track.json`) | Dữ liệu thật | Gợi ý bài (builder quyết tên và chi tiết) |
| --- | --- | --- | --- | --- |
| 2 | `01-math-for-ml` | Vector/ma trận như dữ liệu, phép chiếu, eigen/SVD và PCA, đạo hàm/gradient/chain rule, convex vs non-convex, gradient descent / SGD / momentum, điều kiện số (condition number) | Olist: hồi quy `freight_value` theo khối lượng và kích thước bằng normal equation và gradient descent | Tự viết normal equation; gradient descent có learning rate schedule; PCA bằng SVD so với sklearn; kiểm gradient bằng sai phân hữu hạn |
| 3 | `02-probability-statistics` | Phân phối (Bernoulli, Binomial, Poisson, Normal, Exponential, Lognormal, heavy tail), LLN, CLT, sampling bias, MLE, CI, bootstrap, Bayesian (Beta-Binomial, prior/posterior) | Olist: thời gian giao, giá trị đơn, điểm review theo category | MLE tự viết; mô phỏng CLT trên giá trị đơn lệch phải; bootstrap CI cho median; so sánh Beta-Binomial giữa các category ít đơn |
| 4 | `04-advanced-experimentation` | Đủ các mục con trong PDF roadmap: MDE, CUPED, CUPAC, stratification, ratio metrics và delta method (Microsoft), novelty/primacy, network effect, switchback, heterogeneous effect | Hillstrom (`history` làm covariate trước thí nghiệm cho CUPED); A/A và tác động cài thêm trên Olist thật (random theo `customer_unique_id`) cho ratio metric | CUPED tự viết và đo mức giảm variance; delta method so với bootstrap; stratified estimator; mô phỏng network effect / switchback |
| 5 | `05-econometrics-regression` | OLS và các giả định, chẩn đoán residual, heteroskedasticity (robust SE), multicollinearity (VIF), GLM (logistic, Poisson), fitting distributions (MLE, QQ-plot, KS test), panel data (fixed/random effects) | Olist (freight, giá trị đơn, số món mỗi đơn); `statsmodels.datasets.grunfeld` cho panel | OLS bằng ma trận so với statsmodels; robust SE; fit lognormal và so với gamma; fixed effects bằng `linearmodels` |
| 6 | `06-causal-inference` | DAG, confounder, collider, backdoor; propensity score (matching, IPW, kiểm overlap); DiD và parallel trends; synthetic control; IV; RDD; uplift / CATE; phân tích độ nhạy | `lalonde` (ghim kết quả thí nghiệm ≈ $1 794 làm chuẩn), `prop99`, `card`; Olist: tác động của giao trễ lên review | IPW so với kết quả thí nghiệm LaLonde; DiD; synthetic control cho California; 2SLS; Advanced: phân tích nhân quả giao trễ → review trên Olist |
| 7 | `07-time-series` | Phân rã, stationarity (ADF/KPSS), ACF/PACF, ARIMA/SARIMA, ETS, ML với lag/rolling feature, backtesting (rolling origin), metric (MAE, MAPE, sMAPE, MASE), hierarchical / reconciliation, intervals | Olist số đơn theo ngày; `store-sales` | Backtesting rolling origin tự viết; MASE; SARIMA so với seasonal naive; LightGBM với lag feature không leakage |
| 8 | `08-coding-for-ds` | DSA hay gặp khi phỏng vấn DS (hash map, two pointers, heap, binary search, sliding window); SQL dạng phỏng vấn DS (window, funnel, retention cohort, gaps-and-islands) trên DuckDB; pandas/polars hiệu năng (vector hoá, dtype, lazy) | Olist trong DuckDB | 3 bài DSA (có test độ phức tạp qua input lớn); cohort retention bằng SQL; funnel; tối ưu một pipeline pandas chậm |
| 9 | `09-eda-storytelling` | Quy trình EDA, kiểm tra chất lượng dữ liệu, chọn biểu đồ đúng, lỗi trực quan hoá hay gặp, Simpson's paradox, kể chuyện (khung SCQA, tiêu đề là kết luận), dashboard và memo | Olist | Báo cáo chất lượng dữ liệu tự động; phát hiện Simpson's paradox trong dữ liệu thật; notebook EDA kèm memo 1 trang (Advanced) |
| 10 | `10-feature-engineering` | Các loại leakage (target, temporal, train-test contamination), encoding (one-hot, target encoding có CV, hashing), scaling, feature từ thời gian/văn bản/địa lý, sklearn `Pipeline`/`ColumnTransformer`, CV theo thời gian và theo nhóm, feature selection | Olist: bài toán review xấu, chia theo thời gian như định nghĩa chung | Phát hiện leakage trong một pipeline cho sẵn; target encoding out-of-fold; `TimeSeriesSplit` so với `KFold` cho ra điểm khác nhau; `GroupKFold` theo khách |
| 11 | `11-classic-ml` | Linear/logistic, tree, random forest, SVM, kNN; bias-variance; metric (ROC-AUC, PR-AUC, F1, log loss, chọn ngưỡng theo chi phí); imbalanced data; calibration; tuning; unsupervised (k-means, DBSCAN, PCA); interpretability (permutation, SHAP) | Olist (review xấu), `telco-churn`, Olist RFM cho phân cụm | Chọn ngưỡng theo ma trận chi phí; calibration (reliability curve, Brier); RFM + k-means; SHAP giải thích model churn |
| 12 | `12-advanced-ml` | Bagging vs boosting, gradient boosting từ đầu, XGBoost/LightGBM (tham số quan trọng, early stopping), stacking; recommender (popularity, item-item CF, matrix factorization, metric @k, cold start); anomaly detection (isolation forest, autoencoder ý niệm, đánh giá khi rất mất cân bằng) | Olist, `movielens`, `creditcard-fraud` | Tự viết gradient boosting nhỏ; LightGBM early stopping trên Olist; item-item CF + precision@k trên MovieLens; isolation forest + PR-AUC trên fraud |
| 13 | `13-deep-learning` | Tensor, autograd, vòng train, MLP, CNN, RNN/LSTM, attention và Transformer, transfer learning, embeddings, regularization (dropout, weight decay, early stopping), chọn GPU/CPU | FashionMNIST; review Olist (tiếng Bồ Đào Nha) cho NLP / embeddings | Tự viết autograd nhỏ hoặc vòng train; CNN trên FashionMNIST (test dùng ảnh giả 8×8); scaled dot-product attention so với `torch.nn.functional`; phân loại review bằng embedding |
| 14 | `14-mlops-for-ds` | Vòng đời model, tracking thí nghiệm MLflow, model registry, đóng gói (pipeline + signature), serve FastAPI, batch vs online, monitoring (data drift: PSI/KS), giới thiệu ONNX và lý do Rust/Go/C++ gọi model | Olist (model review xấu) | Log run MLflow vào thư mục tạm; API FastAPI test bằng `TestClient`; PSI tự viết; export sklearn sang ONNX và so output |
| 15 | `15-ml-system-design` | Khung trả lời ML system design (đóng khung bài toán → metric → dữ liệu → feature → model → serving → monitoring → thí nghiệm), offline vs online metric, chi phí lỗi, feedback loop, fairness, làm việc với stakeholder, memo/1-pager | Olist (ước tính tác động kinh doanh) | Hàm chuyển metric model sang giá trị tiền (expected value của ngưỡng); precision@k theo ngân sách can thiệp; Advanced: tài liệu thiết kế hệ thống cảnh báo đơn rủi ro cho Olist |

Commit mỗi module (người điều phối): `Module <NN>: lý thuyết, phỏng vấn, bài tập`.

### Task 16: Capstone "Olist Customer Experience"

**Files:**
- Create: `tracks/data-science/capstone/README.md`, `tracks/data-science/capstone/milestones/m01-…md` … `m07-…md`, `tracks/data-science/capstone/project/README.md` (khung thư mục cho người học)
- Modify: `tracks/data-science/track.json` (thêm khoá `capstone`)

**Interfaces:**
- Consumes: nội dung các module 03, 06, 07, 09, 11, 12, 14, 15 (để dẫn chiếu); định nghĩa dùng chung về Olist.
- Produces: `capstone` trong `track.json` đúng format của track DE: `title`, `readme`, `milestones[{id, title, after, doc}]`.

Milestone (thứ tự và `after` đã chốt, mỗi milestone chỉ cần kiến thức của các module trước nó):

| id | Tiêu đề | after |
| --- | --- | --- |
| m01 | EDA và định nghĩa metric | `09-eda-storytelling` |
| m02 | Dự báo nhu cầu theo ngày | `07-time-series` |
| m03 | Model dự đoán đơn có nguy cơ review xấu | `11-classic-ml` |
| m04 | Phân tích nhân quả: giao trễ ảnh hưởng review bao nhiêu | `06-causal-inference` |
| m05 | Thiết kế A/B test cho can thiệp với đơn rủi ro | `04-advanced-experimentation` |
| m06 | Đóng gói model bằng MLflow, serve qua FastAPI | `14-mlops-for-ds` |
| m07 | Memo trình bày cho stakeholder | `15-ml-system-design` |

- [ ] **Step 1:** Viết từng milestone theo `CONTENT_SPEC.md` (mục tiêu, việc cần làm, kết quả nộp, tiêu chí đạt). Milestone dẫn chiếu các bài liên quan, ví dụ m05 dẫn tới module 03 bài Advanced 02.
- [ ] **Step 2:** Viết `capstone/README.md`: bức tranh tổng thể, sơ đồ mermaid các milestone, cấu trúc thư mục `capstone/project/`.
- [ ] **Step 3:** Thêm `capstone` vào `track.json`. Kiểm: `cd app && pnpm -s build`; render mọi tệp `.md` capstone qua KaTeX (0 lỗi); mở app ở trang milestone (chụp màn hình headless) để thấy đủ 7 milestone.
- [ ] **Step 4:** Commit: `Capstone Olist Customer Experience`.

### Task 17: Kiểm tổng track

- [ ] **Step 1:** `uv run pytest tests -q` PASS; `uv run pytest tracks/data-science -q` chỉ FAIL/SKIP, 0 error; `SOLUTION=1 uv run pytest tracks/data-science -q` PASS (SKIP chỉ ở Advanced và test dữ liệu thật chưa tải); `SOLUTION=1 uv run pytest tracks/data-engineer -q` = 529 pass như trước.
- [ ] **Step 2:** `cd app && pnpm -s build`; render KaTeX toàn bộ `tracks/data-science/**/*.md` (0 lỗi); chụp màn hình headless trang track và 3 module ngẫu nhiên.
- [ ] **Step 3:** Cập nhật `tracks/data-science/README.md` nếu thứ tự hoặc nội dung module lệch so với bảng hiện có. Commit.
