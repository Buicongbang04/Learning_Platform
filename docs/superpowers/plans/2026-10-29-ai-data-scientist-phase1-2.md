# AI & Data Scientist track: hạ tầng + module mẫu 03 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bật track `data-science` ("AI & Data Scientist") trong app với hạ tầng notebook + dữ liệu thật, và một module mẫu hoàn chỉnh `03-ab-testing` để người học duyệt trước khi soạn hàng loạt.

**Architecture:** `testkit.Exercise` có thêm `notebook()` (exec các code cell không gắn tag `explore` vào một module, cùng cơ chế `SOLUTION=1` như `module()`) và `dataset()` (trả thư mục bộ dữ liệu thật trong `data/raw/<tên>/`, skip nếu chưa tải). Một script tải dữ liệu có registry dùng chung cho mọi bộ. Nội dung module viết theo `CONTENT_SPEC.md`, app không cần sửa.

**Tech Stack:** Python 3.12, uv, pytest, nbformat, jupyterlab, ipykernel, numpy, scipy, statsmodels, matplotlib, seaborn, pandas.

**Spec:** `docs/superpowers/specs/2026-10-29-ai-data-scientist-track-design.md`. Plan này chỉ phủ mục 9 bước 1–2 của spec; bước 3 (14 module còn lại + capstone milestones) có plan riêng sau khi người học duyệt module mẫu.

## Global Constraints

- Mọi nội dung đúng `CONTENT_SPEC.md` (cấu trúc thư mục, frontmatter, heading cho phép trong đề bài, `SOLUTION.md`).
- Tiếng Việt, giữ thuật ngữ tiếng Anh. Chuẩn: làm được thật trong doanh nghiệp, mức senior, có đánh đổi và lỗi hay gặp, không chỉ định nghĩa.
- Track id giữ `data-science`; tên hiển thị `AI & Data Scientist`; `source`: `https://roadmap.sh/ai-data-scientist`.
- Chỉ Python. Không R, Rust, Go.
- Dữ liệu thật cho notebook thực hành; dữ liệu sinh chỉ dùng trong test (fixtures nhỏ, kiểm tính chất toán học). Không sửa `data/generate_olist.py`. Không commit dữ liệu tải về (`data/raw/` đã trong `.gitignore`); không commit mẫu trích từ bộ có giấy phép chưa rõ (Cookie Cats, ab_data: Kaggle ghi "Unknown").
- Test không cần mạng, GPU hay bộ dữ liệu đầy đủ; phần cần bộ thật gọi `ex.dataset(...)` và tự skip.
- Notebook bài tập: **cell chấm điểm chỉ định nghĩa hàm/hằng**, không gọi tính toán ở top-level (để starter `raise NotImplementedError` vẫn import được và test FAIL chứ không ERROR). Mọi cell đọc dữ liệu thật, vẽ biểu đồ, gọi hàm để xem kết quả gắn tag `explore`.
- Track DE phải giữ nguyên hành vi: `SOLUTION=1 uv run pytest tracks/data-engineer -q` cho cùng kết quả trước và sau.

## Review Focus

1. Notebook starter có cell `explore` đọc `data/raw/...` chưa tải → test vẫn chạy được (cell `explore` bị bỏ qua khi chấm). Test trong Task 1.
2. Notebook có magic `%matplotlib inline` / `!pip install` → `notebook()` không lỗi cú pháp. Test trong Task 1.
3. Hai bài khác nhau cùng có `starter/analysis.ipynb` → không đụng cache module của nhau. Test trong Task 1.
4. Người học chưa có Kaggle token → `download_dataset.py` báo hướng dẫn rõ ràng, exit code ≠ 0, không traceback; bộ `hillstrom` vẫn tải được không cần token. Test trong Task 2.
5. Notebook mở bằng Jupyter để làm bài và lưu lại có output/biểu đồ lớn → chấm vẫn đúng vì chỉ đọc source của code cell. Test trong Task 1 (notebook fixture có output).

---

### Task 1: `Exercise.notebook()` và dependency

**Files:**
- Modify: `testkit.py` (class `Exercise`, docstring đầu tệp)
- Modify: `pyproject.toml` (dependencies)
- Create: `tests/test_testkit_notebook.py`, `tests/fixtures/nb_exercise/exercises/basic/01-demo/starter/analysis.ipynb`, `tests/fixtures/nb_exercise/exercises/basic/01-demo/tests/test_demo.py` (test giả để `Exercise(__file__)` định vị), `tests/fixtures/nb_exercise/solutions/basic/01-demo/analysis.ipynb`, cùng một bài thứ hai `02-demo` có `starter/analysis.ipynb` khác nội dung.

**Interfaces:**
- Produces: `Exercise.notebook(name: str) -> ModuleType`. Đọc `.ipynb` bằng `nbformat`, ghép source các code cell **không** có tag `explore` (theo `cell.metadata.tags`), bỏ các dòng bắt đầu bằng `%` hoặc `!` (sau khi strip đầu dòng), đặt `os.environ.setdefault("MPLBACKEND", "Agg")`, exec vào module mới. Tên module duy nhất và cache theo đường dẫn y như `module()`; dùng chung `path()` nên hưởng `SOLUTION=1` và skip Advanced. Tách phần dùng chung với `module()` thành một helper riêng tư; `module()` giữ nguyên hành vi.
- Produces: dependencies thêm vào `pyproject.toml`: `numpy`, `scipy>=1.13`, `statsmodels>=0.14`, `matplotlib>=3.9`, `seaborn>=0.13`, `nbformat>=5.10`, `ipykernel>=6.29`, `jupyterlab>=4.2`.

- [ ] **Step 1: Thêm dependency và cài**

Run: `uv add numpy "scipy>=1.13" "statsmodels>=0.14" "matplotlib>=3.9" "seaborn>=0.13" "nbformat>=5.10" "ipykernel>=6.29" "jupyterlab>=4.2"`
Expected: `uv.lock` cập nhật, `uv run python -c "import scipy, statsmodels, nbformat"` không lỗi.

- [ ] **Step 2: Viết fixture notebook và test thất bại**

Fixture `01-demo/starter/analysis.ipynb` gồm: cell markdown; cell code `%matplotlib inline\nimport math`; cell code `def area(r):\n    return math.pi * r * r` (có output lưu sẵn kiểu `execute_result`); cell tag `explore`: `import pandas as pd\npd.read_csv("data/raw/khong-ton-tai.csv")`; cell code `!pip install nothing\nANSWER = 42`. Lời giải `solutions/.../analysis.ipynb` định nghĩa `area` trả `-1.0`. `02-demo/starter/analysis.ipynb` định nghĩa `area` trả `0.0`.

```python
def test_notebook_exec_skips_explore_and_magics(): mod.area(1) == pytest.approx(math.pi); mod.ANSWER == 42
def test_notebook_solution_mode(monkeypatch): SOLUTION=1 → area(1) == -1.0
def test_two_exercises_same_filename_do_not_collide(): 01-demo area(1)≈pi, 02-demo area(1)==0.0
def test_module_still_works(): ex.module() trên một .py fixture vẫn import được
```

Trong test tạo `Exercise` bằng đường dẫn tệp `tests/test_demo.py` của fixture (không cần chạy tệp đó); dùng `monkeypatch.setenv("SOLUTION", "1")`.

- [ ] **Step 3: Chạy để thấy fail**

Run: `uv run pytest tests/test_testkit_notebook.py -q`
Expected: FAIL `AttributeError: 'Exercise' object has no attribute 'notebook'`.

- [ ] **Step 4: Cài `notebook()` trong `testkit.py`**, cập nhật docstring đầu tệp thêm dòng `analysis = ex.notebook("analysis.ipynb")`.

- [ ] **Step 5: Chạy test testkit và track DE**

Run: `uv run pytest tests -q && SOLUTION=1 uv run pytest tracks/data-engineer -q`
Expected: `tests` PASS; DE cùng số pass/skip như trước khi sửa (ghi lại con số trước Step 4).

- [ ] **Step 6: Commit**

```bash
git add testkit.py pyproject.toml uv.lock tests/
git commit -m "testkit: chấm bài notebook (.ipynb) và thêm thư viện cho track Data Science"
```

### Task 2: Tải bộ dữ liệu thật + `Exercise.dataset()`

**Files:**
- Create: `data/download_dataset.py`
- Modify: `testkit.py` (thêm `dataset()`), `data/README.md` (thêm mục "Bộ dữ liệu cho track AI & Data Scientist")
- Test: `tests/test_download_dataset.py`, thêm case vào `tests/test_testkit_notebook.py`

**Interfaces:**
- Consumes: `credentials()` từ `data/download_olist.py` (import, không chép lại). Người học dùng token Kaggle kiểu mới `KAGGLE_API_TOKEN` (tiền tố `KGAT_`) trong `setup/.env`, xác thực bằng header `Authorization: Bearer <token>` (đã kiểm: tải được). Sửa `download_olist.py`: đọc `setup/.env` (giống `testkit._load_env_file`, biến môi trường thật được ưu tiên), `credentials()` trả về auth cho `requests` — ưu tiên `KAGGLE_API_TOKEN` (Bearer), rồi mới tới `KAGGLE_USERNAME`/`KAGGLE_KEY` hoặc `kaggle.json` (Basic) như cũ. Cập nhật docstring hướng dẫn token.
- Produces: `data/download_dataset.py` CLI `uv run python data/download_dataset.py <tên> [--out DIR]`, mặc định ghi `data/raw/<tên>/`. Registry `DATASETS: dict[str, Dataset]` với `Dataset(source: Literal["kaggle", "url"], ref: str, files: list[str], license: str, homepage: str)`. Hàm `download(name: str, out: Path) -> list[Path]`.
- Produces: `Exercise.dataset(name: str) -> Path`: trả `ROOT / "data/raw" / name`; nếu thư mục không tồn tại hoặc rỗng thì `pytest.skip(f"Chưa tải bộ {name}. Chạy: uv run python data/download_dataset.py {name}")`.
- Registry ban đầu (chỉ những bộ module 03 dùng):
  - `cookie-cats`: kaggle `yufengsui/mobile-games-ab-testing`, file `cookie_cats.csv`.
  - `ab-data`: kaggle `zhangluyuan/ab-testing`, file `ab_data.csv`.
  - `hillstrom`: url `http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv`, lưu thành `hillstrom.csv`.
  - Tên file Kaggle phải kiểm lại khi tải lần đầu; sửa registry nếu khác.

- [ ] **Step 1: Test thất bại**

```python
def test_registry_entries_complete(): mọi Dataset có ref, files, license, homepage không rỗng
def test_missing_kaggle_credentials_exits_cleanly(monkeypatch, tmp_path, capsys):
    # HOME, KAGGLE_CONFIG_DIR trỏ tmp_path, xoá KAGGLE_USERNAME/KAGGLE_KEY
    # main(["cookie-cats", "--out", str(tmp_path)]) raise SystemExit với code != 0
    # stderr chứa "kaggle.json"
def test_url_download_writes_file(monkeypatch, tmp_path):
    # monkeypatch requests.get trả nội dung CSV giả; download("hillstrom", tmp_path) tạo tmp_path/"hillstrom.csv"
def test_dataset_skips_when_missing(): ex.dataset("khong-co") → pytest.skip (dùng pytest.raises(pytest.skip.Exception))
```

`main(argv: list[str] | None = None) -> None` để test gọi được.

- [ ] **Step 2: Chạy để thấy fail** — `uv run pytest tests -q`, Expected: FAIL (ImportError / AttributeError).

- [ ] **Step 3: Cài `download_dataset.py` và `Exercise.dataset()`**

Docstring đầu tệp theo phong cách `download_olist.py` (cách lấy token, cách chạy). Kaggle: gọi REST `https://www.kaggle.com/api/v1/datasets/download/<ref>` như `download_olist.py`, giải nén, chỉ giữ `files`. Kiểm tệp mong đợi tồn tại sau khi tải, thiếu thì báo lỗi rõ.

- [ ] **Step 4: Chạy test** — `uv run pytest tests -q`, Expected: PASS.

- [ ] **Step 5: Tải thật để kiểm** — `uv run python data/download_dataset.py hillstrom`, Expected: `data/raw/hillstrom/hillstrom.csv` có 64000 dòng dữ liệu, header `recency,history_segment,...,spend`. Nếu có Kaggle token thì tải thêm `cookie-cats` và kiểm 90189 dòng, cột `userid,version,sum_gamerounds,retention_1,retention_7`; không có token thì ghi chú lại để người học tự kiểm.

- [ ] **Step 6: Cập nhật `data/README.md`**: bảng tên bộ, nguồn, giấy phép, module dùng, lệnh tải.

- [ ] **Step 7: Commit** — `git commit -m "data: script tải bộ dữ liệu thật cho track Data Science"`

### Task 3: Khai báo track

**Files:**
- Modify: `tracks/data-science/track.json`
- Create: `tracks/data-science/README.md`

**Interfaces:**
- Produces: `track.json` với `status: "active"`, `order: 3` (giữ), `icon: "flask-conical"`, `description` một câu, `source`, và `modules` đủ 15 mục đúng id + tiêu đề ở bảng mục 4 của spec, mỗi mục có `summary` và `topics`. **Chưa** có khoá `capstone` (thêm ở plan giai đoạn 3 cùng milestone docs; module chưa có nội dung app tự hiện là chưa có nhờ `hasContent`).

- [ ] **Step 1: Viết `track.json`** theo spec mục 4.
- [ ] **Step 2: Viết `README.md` track**: đối tượng (người DE muốn bổ sung DS tới mức senior), cách học, chuẩn bị dữ liệu (Kaggle token, `download_dataset.py`), cách làm bài notebook (`uv run jupyter lab`, kernel của `.venv`, tag `explore`, cell chấm chỉ định nghĩa hàm), sơ đồ mermaid phụ thuộc 15 module, bảng module ↔ node roadmap gốc, phần "ngoài phạm vi" (MLOps sâu, LLM app, Rust/Go) theo spec mục 2.
- [ ] **Step 3: Kiểm app** — `cd app && pnpm typecheck && pnpm build`, Expected: thành công; chạy `pnpm dev` và mở track Data Science thấy 15 module, chỉ 03 có nội dung sau Task 4.
- [ ] **Step 4: Commit** — `git commit -m "Track AI & Data Scientist: khai báo 15 module"`

### Task 4: Lý thuyết + interview module 03

**Files:**
- Create: `tracks/data-science/modules/03-ab-testing/README.md`, `tracks/data-science/modules/03-ab-testing/interview.md`

- [ ] **Step 1: `README.md`** — 8 phần `## `:
  1. Vì sao doanh nghiệp chạy thí nghiệm (correlation vs causation, khi nào không A/B được)
  2. Hypothesis testing cho thí nghiệm (H0/H1, p-value hiểu đúng, Type I/II, z-test tỉ lệ, Welch t-test, chi-square, non-parametric, bootstrap)
  3. Thiết kế thí nghiệm (randomization unit, OEC, guardrail metrics, phân bổ traffic, thời lượng và chu kỳ tuần)
  4. Power, MDE và sample size (công thức, đánh đổi MDE ↔ thời gian chạy, baseline variance)
  5. Phân tích và ra quyết định (CI, practical vs statistical significance, ma trận quyết định ship/không ship)
  6. Bẫy thường gặp: SRM, peeking & sequential testing, multiple testing, novelty/primacy (giới thiệu, chi tiết ở module 04)
  7. Quy trình thí nghiệm ở doanh nghiệp (pre-registration, experiment review, experimentation platform, văn hoá)
  8. Tài liệu tham khảo (gồm các link mục Statistics trong PDF roadmap + Kohavi "Trustworthy Online Controlled Experiments")
  ≥2 sơ đồ mermaid (vòng đời thí nghiệm; cây quyết định chọn kiểm định). Code mẫu chạy được bằng scipy/statsmodels. Ví dụ dùng Cookie Cats, Hillstrom, Olist (baseline tỉ lệ review xấu).
- [ ] **Step 2: `interview.md`** — ≥14 câu, gồm: giải thích p-value cho PM; power và MDE; khi nào dùng t-test vs bootstrap; SRM là gì, xử lý thế nào; peeking; multiple metrics; network effect / chọn randomization unit; kết quả có ý nghĩa thống kê nhưng âm guardrail; ≥3 câu case/product sense (ví dụ "Cookie Cats nên đặt gate ở level 30 hay 40", "thiết kế A/B cho tính năng giảm giao trễ của Olist", "metric tăng nhưng doanh thu giảm").
- [ ] **Step 3: Kiểm** — mọi khối ` ```python ` trong README chạy được: tách ra chạy bằng `uv run python` (khối cần dữ liệu thật thì chạy sau khi tải). Đếm `## ` của interview ≥ 14.
- [ ] **Step 4: Commit** — `git commit -m "Module 03 A/B testing: lý thuyết và câu hỏi phỏng vấn"`

### Task 5: Bài Basic (3 bài, `.py`)

Thư mục gốc: `tracks/data-science/modules/03-ab-testing/`. Mỗi bài: `exercises/basic/<slug>/{README.md, starter/<file>.py, tests/test_*.py}` và `solutions/basic/<slug>/{SOLUTION.md, <file>.py}`. Starter: thân hàm `# TODO` + `raise NotImplementedError`.

**Bài `01-two-sample-tests`, tệp `stat_tests.py`:**
- `two_proportion_ztest(x_a: int, n_a: int, x_b: int, n_b: int) -> tuple[float, float]` — pooled z-test hai phía, trả `(z, p_value)`, z theo hướng `p_b - p_a`.
- `diff_proportion_ci(x_a, n_a, x_b, n_b, alpha: float = 0.05) -> tuple[float, float]` — Wald không pooled cho `p_b - p_a`.
- `welch_ttest(a: np.ndarray, b: np.ndarray) -> tuple[float, float]`.
- Test: so với `statsmodels.stats.proportion.proportions_ztest` (`count=[x_b, x_a]`), `confint_proportions_2indep(x_b, n_b, x_a, n_a, method="wald", compare="diff")`, `scipy.stats.ttest_ind(b, a, equal_var=False)`, `abs=1e-9`, trên 3 bộ số khác nhau; cấm import statsmodels/scipy.stats trong starter là **không** bắt buộc (ghi trong README là được dùng `scipy.stats.norm`, không dùng hàm kiểm định dựng sẵn).

**Bài `02-power-sample-size`, tệp `power.py`:**
- `sample_size_proportions(p_baseline: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int` — mỗi nhóm, hai phía, công thức xấp xỉ normal không pooled, `math.ceil`.
- `mde_proportions(p_baseline: float, n_per_group: int, alpha: float = 0.05, power: float = 0.8) -> float` — nghịch đảo của hàm trên (giải số, ví dụ `scipy.optimize.brentq`).
- `sample_size_means(sigma: float, mde_abs: float, alpha: float = 0.05, power: float = 0.8) -> int`.
- Test: `sample_size_proportions(0.10, 0.01) == 14749`; `sample_size_proportions(p, mde)` giảm khi `mde` tăng; `mde_proportions(0.10, sample_size_proportions(0.10, 0.02))` ≈ `0.02` (`rel=0.01`); mô phỏng 3000 lần z-test tại `n = sample_size_proportions(0.2, 0.03)` cho tỉ lệ bác bỏ trong `[0.77, 0.83]` (seed cố định); `sample_size_means(10, 1)` lệch ≤ 2% so với `TTestIndPower().solve_power(effect_size=0.1, alpha=0.05, power=0.8)`.

**Bài `03-srm-check`, tệp `srm.py`:**
- `srm_pvalue(counts: Sequence[int], expected_ratios: Sequence[float]) -> float` — chi-square goodness-of-fit, ratios được chuẩn hoá.
- `has_srm(counts, expected_ratios, threshold: float = 0.001) -> bool`.
- Test: `srm_pvalue([50000, 50000], [1, 1]) == pytest.approx(1.0)`; `srm_pvalue([44700, 45489], [0.5, 0.5]) == pytest.approx(0.008608, abs=1e-5)` và `has_srm(...)` là `False` ở ngưỡng 0.001 nhưng `True` ở ngưỡng 0.01 (bài học: chọn ngưỡng trước); ba nhóm `[3300, 3300, 3400]` với ratios `[1, 1, 1]` không SRM; `[5000, 4500]` có SRM; mô phỏng A/A 2000 lần chia đều → tỉ lệ `has_srm(threshold=0.05)` trong `[0.035, 0.065]`.
- Bài có test tuỳ chọn trên dữ liệu thật: `ex.dataset("cookie-cats")` → đếm theo `version` cho p-value như trên.

- [ ] **Step 1: Viết README + starter + test cho cả 3 bài**
- [ ] **Step 2: Chạy trên starter** — `uv run pytest tracks/data-science/modules/03-ab-testing/exercises/basic -q`, Expected: mọi test FAIL (NotImplementedError) hoặc SKIP (dữ liệu thật), không ERROR khi collect.
- [ ] **Step 3: Viết lời giải + `SOLUTION.md`** (giải thích cách làm, vì sao, đánh đổi, như mẫu `SOLUTION.md` của track DE)
- [ ] **Step 4: Chạy lời giải** — `SOLUTION=1 uv run pytest tracks/data-science/modules/03-ab-testing/exercises/basic -q`, Expected: PASS (SKIP chỉ ở test cần dữ liệu thật chưa tải).
- [ ] **Step 5: Commit** — `git commit -m "Module 03: bài tập Basic"`

### Task 6: Bài Intermediate (3 bài, 2 notebook)

**Bài `01-cookie-cats-retention`, tệp `starter/analysis.ipynb`** (notebook; các cell `explore` đọc `data/raw/cookie-cats/cookie_cats.csv`, EDA phân phối `sum_gamerounds`, xử lý outlier):
- `retention_summary(df: pd.DataFrame) -> pd.DataFrame` — index `version`, cột `n`, `retention_1`, `retention_7`.
- `bootstrap_diff_ci(df: pd.DataFrame, metric: str, n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> tuple[float, float, float]` — `(diff, lo, hi)` với `diff = mean(gate_40) - mean(gate_30)`.
- `decision(df: pd.DataFrame, metric: str = "retention_7") -> str` — `"ship_gate_40"` nếu CI > 0, `"keep_gate_30"` nếu CI < 0, ngược lại `"inconclusive"`.
- Test fixtures sinh trong test (cột `userid, version, sum_gamerounds, retention_1, retention_7`): summary đúng từng số; CI chứa diff thật ở dữ liệu lớn có effect rõ và `decision` đúng cả 3 nhánh; seed giống → kết quả giống. Test dữ liệu thật (skip nếu chưa tải): `n` là 44700 / 45489, `retention_7` ≈ 0.1902 / 0.1820 (`abs=5e-4`), `decision == "keep_gate_30"`.

**Bài `02-multiple-testing`, tệp `multiple.py`:**
- `bonferroni(pvals: Sequence[float], alpha: float = 0.05) -> list[bool]`, `holm(...)`, `benjamini_hochberg(...)` cùng chữ ký.
- Test: khớp `statsmodels.stats.multitest.multipletests` (method `bonferroni`, `holm`, `fdr_bh`) trên 5 vector p-value, gồm vector có p trùng nhau và thứ tự lộn xộn; mô phỏng 2000 lần 10 kiểm định dưới global null: FWER của `holm` ≤ 0.06, của "không hiệu chỉnh" > 0.3.

**Bài `03-peeking`, tệp `starter/peeking.ipynb`:**
- `peeking_fpr(n_per_group: int, n_looks: int, n_sims: int, alpha: float = 0.05, seed: int = 0) -> float` — A/A dữ liệu normal, nhìn ở `n_looks` mốc cách đều, bác bỏ nếu bất kỳ lần nào `p < alpha`.
- `obf_fpr(c: float, n_per_group: int, n_looks: int, n_sims: int, seed: int = 0) -> float` — biên O'Brien-Fleming `|z_k| > c * sqrt(n_looks / k)`.
- `calibrate_obf_constant(n_looks: int, alpha: float = 0.05, n_sims: int = 20000, seed: int = 0) -> float` — tìm `c` sao cho `obf_fpr ≈ alpha`.
- Test: `peeking_fpr(n_looks=1)` trong `[0.04, 0.06]`; `peeking_fpr(n_looks=10)` > 0.12; `calibrate_obf_constant(5)` trong `[1.99, 2.09]` (giá trị sách 2.040); `obf_fpr(calibrated)` trong `[0.04, 0.06]`. Dùng `n_per_group` nhỏ và vector hoá numpy để cả bài chạy < 20 giây.
- Cell `explore`: vẽ đường p-value theo thời gian của một A/A để thấy "chạm 0.05 rồi quay lại".

- [ ] **Step 1: Viết README + starter (notebook có cell markdown hướng dẫn, cell chấm chỉ `def`, cell `explore` có tag) + test**
- [ ] **Step 2: Chạy trên starter** — `uv run pytest tracks/data-science/modules/03-ab-testing/exercises/intermediate -q`, Expected: FAIL/SKIP, không ERROR.
- [ ] **Step 3: Viết lời giải** (notebook lời giải chạy được toàn bộ kể cả `explore` khi đã tải dữ liệu) + `SOLUTION.md`
- [ ] **Step 4: Chạy lời giải** — `SOLUTION=1 uv run pytest tracks/data-science/modules/03-ab-testing/exercises/intermediate -q`, Expected: PASS (SKIP chỉ ở test dữ liệu thật). Thêm: `uv run jupyter nbconvert --to notebook --execute --stdout tracks/data-science/modules/03-ab-testing/solutions/intermediate/01-cookie-cats-retention/analysis.ipynb > /dev/null` thành công khi đã có `cookie-cats` (ghi lại nếu không có token).
- [ ] **Step 5: Commit** — `git commit -m "Module 03: bài tập Intermediate"`

### Task 7: Bài Advanced (2 bài) + kiểm tổng module

**Bài `01-hillstrom-email-experiment`** (dữ liệu thật Hillstrom: 3 nhánh `Mens E-Mail`, `Womens E-Mail`, `No E-Mail`; metric `visit`, `conversion`, `spend`):
- Starter `analysis.ipynb` định nghĩa `effects_table(df: pd.DataFrame, control: str = "No E-Mail") -> pd.DataFrame` — mỗi dòng (arm, metric) với cột `diff`, `ci_low`, `ci_high`, `p_value`, `p_holm`; cùng `REPORT.md` khung (khuyến nghị cho stakeholder, phân tích theo segment `newbie`/`channel`, rủi ro, bước tiếp theo).
- Test (fixture sinh nhỏ): bảng có đủ 6 dòng, đúng cột, `ci_low <= diff <= ci_high`, `p_holm >= p_value`; test dữ liệu thật (skip nếu chưa tải): diff `visit` của `Womens E-Mail` dương và CI không chứa 0.
- `SOLUTION.md`: hướng làm, quyết định (metric chính, xử lý `spend` lệch phải, heterogeneous effect, multiple testing), rubric chấm.

**Bài `02-olist-experiment-design`** (thiết kế thí nghiệm trên baseline Olist thật, dẫn vào capstone milestone 5):
- Starter `design.py`: `baseline(orders: pd.DataFrame, reviews: pd.DataFrame) -> dict[str, float]` trả `bad_review_rate` (score ≤ 2, đơn `delivered`), `late_rate`, `n_delivered_per_week`; và `DESIGN.md` khung (giả thuyết, đơn vị randomization, OEC + guardrail, power/MDE/thời lượng tính từ `baseline`, kế hoạch phân tích, tiêu chí dừng).
- Test (fixture sinh nhỏ theo cột Olist): `baseline` đúng từng số; test dữ liệu thật dùng `ex.dataset`… Olist thật nằm ở `data/raw/` chứ không phải `data/raw/<tên>/` → bài này đọc bằng đường dẫn `data/raw/olist_orders_dataset.csv` và tự skip nếu thiếu (ghi rõ trong README là cần `download_olist.py`).
- `SOLUTION.md`: hướng làm + rubric.

- [ ] **Step 1: Viết README + starter + test + `SOLUTION.md` cho 2 bài**
- [ ] **Step 2: Kiểm toàn module**
  - `uv run pytest tracks/data-science -q` → chỉ FAIL/SKIP, không ERROR.
  - `SOLUTION=1 uv run pytest tracks/data-science -q` → PASS, SKIP chỉ ở Advanced và test dữ liệu thật.
  - `SOLUTION=1 uv run pytest tracks/data-engineer -q` → không đổi so với trước Task 1.
  - `uv run pytest tests -q` → PASS.
  - `cd app && pnpm build` → thành công; mở app, module 03 hiện đủ 8 phần lý thuyết, interview, 8 bài tập, nút chép lệnh `run`.
- [ ] **Step 3: Commit** — `git commit -m "Module 03: bài tập Advanced, hoàn thiện module mẫu"`
- [ ] **Step 4: Bàn giao cho người học duyệt**: liệt kê cần xem văn phong, độ khó, trải nghiệm notebook, và các bộ dữ liệu chưa kiểm được do thiếu Kaggle token.
