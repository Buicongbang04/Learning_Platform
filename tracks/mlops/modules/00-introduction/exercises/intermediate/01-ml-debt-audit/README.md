---
title: Máy quét nợ kỹ thuật ML trên một repo
level: intermediate
services: []
files:
  - path: starter/audit.py
    note: 9 hàm TODO
  - path: tests/test_audit.py
    note: Không sửa
run:
  - uv run pytest tracks/mlops/modules/00-introduction/exercises/intermediate/01-ml-debt-audit -q
---

## Mục tiêu

Biến vài dấu hiệu "hidden technical debt in ML" thành kiểm tra tự động chạy được trên một repo: model và dữ liệu bị commit,
đường dẫn cứng, ngẫu nhiên không seed, dependency không ghim, thiếu test, code chỉ có notebook.

## Đề bài

Trong `starter/audit.py`, `files` là dict `đường dẫn -> nội dung` (ảnh chụp repo). Cài:

1. 7 hàm kiểm tra, mỗi hàm trả danh sách đường dẫn vi phạm theo docstring: `model_artifact_in_git`, `data_in_git`,
   `hardcoded_path`, `unseeded_randomness`, `unpinned_dependency`, `no_tests`, `notebook_only_code`.
2. `audit(files)`: chạy mọi kiểm tra trong `CHECKS`, chỉ giữ khoá có kết quả, giá trị sắp xếp, không trùng.
3. `verdict(findings)`: `"block"` nếu có model/dữ liệu bị commit hoặc đường dẫn cứng (rủi ro lộ hoặc không tái lập ngay),
   `"warn"` nếu chỉ có phát hiện khác, `"ok"` nếu sạch.

Các ca biên test kiểm: đuôi tệp viết hoa (`raw.CSV`), thư mục `tests/` và `fixtures/` được phép chứa dữ liệu, `latests/`
không phải `tests/`, dòng bình luận không tính là đường dẫn cứng, URL chứa `/home/` không phải đường dẫn cứng, dòng
`-r base.txt` và bình luận trong requirements.

Dùng cho gì: chạy trong pre-commit hoặc CI để chặn nợ trước khi nó vào repo (xem module 01 và 08).

## Tiêu chí đạt

- Repo sạch trả `{}`; repo bẩn trả đúng tập phát hiện.
- Các ca biên ở trên đúng.
- `audit` sắp xếp và loại trùng; `verdict` đúng ba mức.

## Gợi ý

### Gợi ý 1

Duyệt `files.items()` và lọc theo `path.lower().endswith(tuple)`. Để biết có nằm dưới `tests/` hay không, tách `path.split("/")[:-1]`
rồi kiểm tra thành phần, không dùng `"tests" in path`.

### Gợi ý 2

Đường dẫn cứng: dùng `re.compile(r"(?<![\w.:/])(/home/|/Users/)|[A-Za-z]:\\")` để `https://x.com/home/` không khớp.
Ngẫu nhiên không seed: `re.findall(r"\b(Tên1|Tên2)\(([^)]*)\)", text)` rồi kiểm `"random_state" not in args`.
