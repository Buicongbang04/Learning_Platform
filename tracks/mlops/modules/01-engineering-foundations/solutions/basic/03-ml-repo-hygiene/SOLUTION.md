# Lời giải: Git, Makefile và pre-commit

## Cách làm

- `.gitignore` chặn `data/*` rồi bỏ chặn `README.md` và `.gitkeep` bằng `!`. Viết `data/` (kết thúc bằng `/`) sẽ chặn cả thư mục và các dòng `!data/...` không còn tác dụng, vì Git không đi vào thư mục đã bị loại.
- `.env.*` chặn `.env.production`, nhưng `!.env.example` giữ lại mẫu cho người mới.
- `Makefile` dùng `.DEFAULT_GOAL := help` và `##` trên mỗi target; `PYTHON ?=` cho phép test thay bằng `echo` để kiểm lệnh mà không train thật.
- `pre-commit` ghim `rev` bằng tag; `check-added-large-files --maxkb=500` chặn parquet và model lọt vào commit **trước khi** vào lịch sử (khi đã vào thì xoá cũng không làm repo nhẹ lại).

## Vì sao

Ba tệp chặn ba kiểu hỏng: `.gitignore` chặn nhầm lẫn thông thường, pre-commit chặn nhầm lẫn khi `.gitignore` bị quên hoặc dùng `git add -f`, `Makefile` làm cho "chạy thế nào" là một lệnh mà cả đội và CI cùng dùng. Data và model nằm ngoài Git vì Git không có delta tốt cho tệp nhị phân và mỗi lần `commit` tệp 300 MB thêm 300 MB vĩnh viễn vào `.git`; chúng được quản lý bởi DVC và registry ở module 03-04.

## Lỗi hay gặp

- Chặn `*.csv` toàn cục làm mất luôn CSV fixture của test.
- Quên `.env.*`: `.env.production` vẫn bị commit.
- Dùng `rev: main` cho pre-commit: kết quả hook đổi theo ngày, CI đỏ vô cớ.
- Makefile dùng dấu cách thay vì tab ở đầu dòng lệnh.
