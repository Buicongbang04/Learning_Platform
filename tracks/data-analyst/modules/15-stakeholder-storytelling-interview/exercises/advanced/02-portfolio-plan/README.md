---
title: Kế hoạch portfolio 90 ngày và công cụ tự kiểm repo dự án
level: advanced
services: []
files:
  - path: starter/PORTFOLIO_PLAN.md
    note: Kế hoạch portfolio, Kaggle, khoá học, networking
  - path: starter/portfolio_check.py
    note: 1 hàm TODO (audit_project)
  - path: tests/test_portfolio.py
    note: Không sửa
run:
  - uv run pytest tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/advanced/02-portfolio-plan -q
  - uv run python tracks/data-analyst/modules/15-stakeholder-storytelling-interview/exercises/advanced/02-portfolio-plan/starter/portfolio_check.py <đường dẫn repo dự án của bạn>
---

## Mục tiêu

Biến phần cuối của roadmap (build a portfolio, Kaggle competitions, online courses and certifications, stay updated and
network) thành một kế hoạch cá nhân có mốc kiểm được, gắn với tin tuyển dụng thật; và viết một công cụ nhỏ tự kiểm mọi
repo dự án trước khi công khai: README có câu hỏi, dữ liệu, kết quả, giới hạn; có giấy phép dữ liệu; có tệp dependency;
không có tệp quá lớn, tệp `.env` hay key trong code.

## Đề bài

1. **Đọc 5-10 tin tuyển dụng DA thật** cho vai trò bạn nhắm (ghi tên công ty hoặc loại công ty, không cần link). Đếm
   công cụ và kỹ năng xuất hiện nhiều nhất.
2. **`starter/portfolio_check.py`**, hàm `audit_project(path, max_mb=50) -> list[str]` trả danh sách vấn đề, **đã sắp xếp**
   (`sorted`), rỗng là đạt. `path` là `str` hoặc `Path`.
   - `README.md` ở gốc không có → `"missing-readme"` (khi đó bỏ qua hai kiểm tra kế tiếp).
   - Mỗi khoá của `REQUIRED_SECTIONS` cần ít nhất một heading **cấp 2** (`## `) của README chứa (không phân biệt hoa thường)
     một từ khoá của nó; thiếu → `"missing-section:<khoá>"`.
   - README không chứa `licen` hay `giấy phép` (không phân biệt hoa thường) → `"no-data-license"`.
   - Gốc repo không có tệp nào trong `DEPENDENCY_FILES` → `"no-dependencies"`.
   - Duyệt mọi tệp trong repo, bỏ thư mục trong `SKIP_DIRS` (ở bất kỳ cấp nào). Đường dẫn tương đối dạng posix (`data/raw/x.csv`):
     tệp lớn hơn `max_mb` MB (MB = 1024 × 1024 byte) → `"large-file:<đường dẫn>"`; tệp tên đúng `.env` → `"env-file:<đường dẫn>"`;
     tệp có đuôi trong `TEXT_SUFFIXES` khớp một mẫu trong `SECRET_PATTERNS` → `"secret:<đường dẫn>"` (mỗi tệp một lần).
3. **`starter/PORTFOLIO_PLAN.md`** theo khung sáu mục: vai trò mục tiêu (có số đếm từ tin tuyển dụng), ít nhất ba dự án (mỗi
   dự án một heading `###` có dòng `Câu hỏi:`, `Dữ liệu:` kèm link nguồn, `Giấy phép:`; nên gồm hai dự án roadmap gợi ý:
   predicting sales trends và customer segmentation), Kaggle, khoá học và chứng chỉ, networking, kế hoạch 90 ngày (ít nhất ba
   mốc, mỗi mốc một sản phẩm kiểm được). 400-1500 từ.
4. Chạy `portfolio_check.py` trên ít nhất một repo dự án của bạn (hoặc thư mục capstone của track), sửa đến khi đạt.

## Tiêu chí đạt

- `audit_project` qua test trên các repo mẫu tạo trong thư mục tạm: repo tốt không báo gì (kể cả code đọc key từ biến môi
  trường), phát hiện thiếu README, thiếu mục, thiếu giấy phép, thiếu dependency, tệp lớn, `.env`, key OpenAI/AWS và mật khẩu
  gán cứng, bỏ qua `.git`, chỉ tính heading cấp 2.
- `PORTFOLIO_PLAN.md` không còn TODO, đủ sáu mục theo thứ tự, ít nhất ba dự án đủ ba dòng và có link, kế hoạch 90 ngày có ít
  nhất ba mốc. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`Path(path).rglob("*")` duyệt mọi tệp; `f.relative_to(root).parts` cho biết tệp có nằm trong `.git` không;
`.as_posix()` cho đường dẫn dạng `a/b.csv` trên mọi hệ điều hành. Đọc tệp text bằng
`read_text(encoding="utf-8", errors="replace")` để không lỗi trên tệp mã hoá lạ.

### Gợi ý 2

Một dự án portfolio mạnh trả lời câu hỏi có **quyết định** phía sau, trên dữ liệu thật có giấy phép cho đăng công khai (bộ
Kaggle của competition thường cấm đăng lại dữ liệu: chỉ đăng code và kết quả). Mỗi mốc 90 ngày là một thứ người khác kiểm
được (repo công khai, notebook, dashboard, số đơn ứng tuyển), không phải "học xong Power BI".
