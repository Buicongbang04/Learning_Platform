---
title: Data quality report cho bộ dữ liệu mới - Rossmann store sales trước khi lên dashboard
level: advanced
services: []
files:
  - path: starter/quality_checks.ipynb
    note: 2 hàm TODO + điều tra tự do
  - path: starter/REPORT.md
    note: Báo cáo chất lượng dữ liệu một trang
  - path: tests/test_quality_report.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/06-data-cleaning/exercises/advanced/01-store-sales-quality-report/starter/quality_checks.ipynb
  - uv run pytest tracks/data-analyst/modules/06-data-cleaning/exercises/advanced/01-store-sales-quality-report -q
---

## Mục tiêu

Làm việc DA thường làm đầu tiên với một nguồn dữ liệu mới: kiểm có hệ thống (khoá, thiếu, miền giá trị, quy tắc nghiệp
vụ, độ phủ, nhất quán giữa bảng), phân loại vấn đề theo mức độ và tác động lên chỉ số, rồi viết một báo cáo mà team BI
và quản lý đọc xong biết dữ liệu dùng được tới đâu và ai phải làm gì.

## Đề bài

Bộ `store-sales` (Rossmann): `train.csv` 1 017 209 dòng doanh số ngày của 1 115 cửa hàng, 01/01/2013 tới 31/07/2015, và
`store.csv` thông tin cửa hàng. Team BI sắp dựng dashboard doanh số tuần và hỏi "bộ này có vấn đề gì, cái nào chặn".
Mở `starter/quality_checks.ipynb`:

1. `run_checks(df, checks)`: chạy danh sách check khai báo (`not_null`, `unique`, `range`, `allowed`, `rule`), trả bảng
   `name`, `kind`, `severity`, `failed`, `failed_share`, `passed`.
2. `coverage_gaps(df, key, date_col)`: mỗi khoá thiếu bao nhiêu ngày so với lịch đầy đủ của cả bảng, ngày thiếu đầu và
   cuối.
3. Khai báo bộ check cho `train.csv` và `store.csv` (notebook có vài check mẫu, bạn bổ sung), chạy, điều tra các check
   không đạt: ai bị ảnh hưởng, tác động lên chỉ số nào, là lỗi dữ liệu, quy ước của nguồn hay sự thật nghiệp vụ.
4. Viết `starter/REPORT.md` theo khung có sẵn (300-900 từ, dòng đầu là headline có con số, đủ các mục).

## Tiêu chí đạt

- `run_checks` đúng trên dữ liệu nhỏ: `unique` tính mọi dòng của khoá trùng, `range` và `allowed` không tính ô thiếu,
  `rule` coi kết quả thiếu là hợp lệ, `severity` mặc định `error`, `kind` lạ báo `ValueError`.
- `coverage_gaps` đúng trên dữ liệu nhỏ và trên bộ thật: 181 cửa hàng thiếu ngày, 180 cửa hàng thiếu 184 ngày, cửa hàng
  988 thiếu đúng 01/01/2013; khoá `Store` + `Date` duy nhất; 54 dòng mở cửa mà doanh số 0.
- `REPORT.md` không còn TODO, đủ mục, headline có con số. Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Bắt đầu bằng câu hỏi "một dòng của bảng này là gì?" (grain: một cửa hàng một ngày). Từ grain suy ra check khoá và
check độ phủ. Check theo dòng không bao giờ thấy được dòng **vắng mặt**: hãy đếm số cửa hàng có dữ liệu mỗi ngày.

### Gợi ý 2

Với mỗi check không đạt, viết ba câu: bao nhiêu (dòng, cửa hàng, ngày), làm sai chỉ số nào trên dashboard và sai theo
hướng nào, ai biết câu trả lời (nguồn, vận hành, tài chính). Một vấn đề 0.005% số dòng có thể chỉ là ghi chú; một vấn đề
không có dòng lỗi nào có thể là vấn đề chặn.
