---
title: Review một PR notebook "thêm năm 2009-2010 để so YoY" - công cụ diff và con số trước/sau
level: advanced
services: []
files:
  - path: starter/nbreview.py
    note: 2 hàm TODO (strip_outputs, cell_diff)
  - path: starter/REVIEW.md
    note: Bản review gửi tác giả PR
  - path: tests/test_review.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/advanced/02-review-notebook-pr -q
---

## Mục tiêu

Review một PR phân tích như một DA senior: dựng công cụ nhỏ để thấy **thay đổi thật** trong notebook (bỏ output, so
source theo cell), chạy cả hai phiên bản trên dữ liệu thật để đo **con số đổi bao nhiêu**, tách vấn đề chặn merge khỏi
góp ý phong cách, và viết review mà tác giả sửa được ngay.

## Đề bài

Báo cáo doanh thu tháng của team (`starter/pr/before.ipynb`, Online Retail II, sheet `Year 2010-2011`, CC BY 4.0) đang
chạy trên main. Đồng nghiệp Minh mở PR *"Thêm năm 2009-2010 để so YoY"* (`starter/pr/after.ipynb`; hai notebook
chỉ để đọc, có trong danh sách tệp của Workspace ở dạng JSON chỉ đọc; mở bằng Jupyter hoặc VS Code để xem như
notebook) và nhờ bạn review
trước buổi họp tháng, nơi CEO sẽ xem bảng YoY.

1. Viết `starter/nbreview.py`:
   - `strip_outputs(nb)`: bản sao notebook không có output, `execution_count`, metadata nhiễu (việc nbstripout làm).
   - `cell_diff(old, new)`: so hai notebook theo cell, chỉ dựa trên `(cell_type, source)`, trả danh sách thay đổi
     `changed` / `added` / `removed` kèm unified diff. Docstring trong file ghi đủ quy tắc.
2. Dùng `cell_diff` đọc PR. Với mỗi thay đổi, hỏi: nó đổi **định nghĩa** (bộ lọc, cách đếm), **dữ liệu đầu vào** (nguồn,
   đường dẫn, ghép nguồn), hay chỉ phong cách? Kiểm từng lý do tác giả ghi trong comment bằng dữ liệu thật.
3. Chạy logic của cả hai phiên bản trên dữ liệu thật (sửa đường dẫn để chạy được, hoặc chép code ra script trong
   scratch) và so: doanh thu, số khách, YoY của vài tháng.
4. Viết `starter/REVIEW.md` theo khung năm mục, 250–1000 từ: ít nhất 3 vấn đề chặn merge, bảng con số trước/sau, kết
   luận "Request changes" hoặc "Approve".

## Tiêu chí đạt

- `strip_outputs` không sửa đầu vào, bỏ output và `execution_count`, giữ `tags`, chỉ giữ `kernelspec`/`language_info`,
  chạy hai lần như một lần.
- `cell_diff` bỏ qua output/metadata và dạng `source` (chuỗi hay list), nhận đúng `changed`, `added`, `removed`; trên PR
  thật ra 5 cell `changed` và 1 cell `added`, diff cell tổng hợp tháng có dòng `nunique` → `count`.
- `REVIEW.md` không còn TODO, đủ năm mục theo thứ tự, ít nhất 3 vấn đề chặn merge, mục ảnh hưởng có con số, kết luận rõ.
- Nội dung review chấm theo rubric trong `SOLUTION.md` (từ 70/100 là đạt).

## Gợi ý

### Gợi ý 1

`difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes()` với `a`, `b` là list tuple `(cell_type, source)` trả
các khối `equal`, `replace`, `delete`, `insert` kèm chỉ số. Notebook đọc bằng `json` có `source` là list dòng; nối
`"".join(...)` trước khi so, để notebook lưu bằng công cụ khác (source là chuỗi) không bị coi là đổi.

### Gợi ý 2

Đọc từng comment của tác giả như một giả thuyết cần kiểm: "hoá đơn C luôn có Quantity âm" (đúng ở cả hai sheet
không?), "giá <= 0 cũng hiếm" (hiếm theo số dòng hay theo số tiền?). Rồi nhìn vào chỗ hai sheet gặp nhau: sheet
`Year 2009-2010` kết thúc ngày nào, sheet `Year 2010-2011` bắt đầu ngày nào?
