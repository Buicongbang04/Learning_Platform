---
title: Từ notebook rối "Untitled_final_v3" tới project phân tích tái lập được
level: advanced
services: []
files:
  - path: starter/project/README.md
    note: README project, 6 mục
  - path: starter/project/src/retail_report/clean.py
    note: 1 hàm TODO
  - path: starter/project/src/retail_report/metrics.py
    note: 1 hàm TODO
  - path: starter/project/src/retail_report/pipeline.py
    note: 1 hàm TODO (raw -> processed)
  - path: tests/test_project.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run pytest tracks/data-analyst/modules/04-python-for-analysts/exercises/advanced/01-messy-notebook-to-project -q
---

## Mục tiêu

Nhận một notebook "bản cuối, đừng sửa!!" của người đã nghỉ việc, tìm các lỗi làm sai con số, và tổ chức lại thành một
project mà người khác clone về, đặt dữ liệu vào `data/raw`, chạy một lệnh là ra đúng bảng báo cáo: quy tắc làm sạch và
metric ở một chỗ có test, dữ liệu gốc không bị sửa, notebook không output, README đủ để tự chạy.

## Đề bài

Head of Sales cần báo cáo tháng "doanh thu, số đơn, số khách theo quốc gia và tháng" chạy lại được mỗi tháng. Bản duy
nhất là `starter/messy/Untitled_final_v3.ipynb` (có trong danh sách tệp của Workspace ở dạng JSON chỉ đọc; mở bằng Jupyter hoặc VS Code để xem như notebook) (Online Retail II, sheet `Year 2010-2011`, CC BY 4.0). Đọc kỹ notebook
đó (có thể chép code ra để chạy thử trên dữ liệu thật), rồi dựng `starter/project/`:

```
project/
├── README.md               # 6 mục: Câu hỏi, Dữ liệu, Cách chạy, Cấu trúc, Kết quả, Thay đổi so với notebook cũ
├── .gitignore              # bỏ qua data/raw, data/processed, .ipynb_checkpoints (và .env, __pycache__)
├── data/raw/               # tệp gốc online_retail_II.xlsx đặt ở đây, không commit
├── data/processed/         # build() ghi CSV vào đây
├── notebooks/              # ít nhất 1 notebook: import từ retail_report, không output, không đường dẫn tuyệt đối
├── src/retail_report/
│   ├── clean.py            # clean_transactions(tx)
│   ├── metrics.py          # monthly_country_revenue(sales)
│   └── pipeline.py         # build(raw_path, out_dir, sheet) -> Path
└── tests/                  # ít nhất 3 hàm test_*, chạy được bằng pytest
```

1. Điền ba hàm trong `src/retail_report/` theo docstring (định nghĩa làm sạch dùng chung của track; tháng là **tháng của
   năm**, không phải số tháng 1–12).
2. Tạo `.gitignore`, hai thư mục dữ liệu (thêm `.gitkeep` để git giữ thư mục rỗng), `notebooks/` và `tests/`. Đặt
   `tests/conftest.py` thêm `../src` vào `sys.path` để `import retail_report` chạy được khi pytest gom test từ thư mục
   bài. Nếu dùng git cho project riêng, cài nbstripout (phần 6 lý thuyết).
3. Viết README. Mục "Thay đổi so với notebook cũ" liệt kê **ít nhất 4** lỗi bạn tìm được trong notebook cũ, mỗi lỗi:
   ảnh hưởng gì, sửa thế nào, con số trước/sau trên dữ liệu thật.

Bộ test kiểm cấu trúc và ba hàm trên dữ liệu nhỏ. Phần còn lại (chất lượng README, độ đầy đủ của danh sách lỗi, notebook
có đọc được không) chấm theo rubric trong `SOLUTION.md`.

## Tiêu chí đạt

- Đủ cấu trúc; `.gitignore` bỏ qua `data/raw`, `data/processed`, `.ipynb_checkpoints`; README đủ 6 mục theo thứ tự, ghi
  giấy phép CC BY 4.0, không còn TODO, mục thay đổi có ít nhất 4 gạch đầu dòng và có con số.
- Notebook trong `notebooks/` không có output, `execution_count`, đường dẫn tuyệt đối, import từ `retail_report` và không
  tự viết lại quy tắc làm sạch.
- `clean_transactions`, `monthly_country_revenue` đúng trên dữ liệu nhỏ (kể cả 12/2010 khác 12/2011); `build` tạo thư mục
  đích, ghi `monthly_country_revenue.csv`, chạy hai lần ra tệp giống hệt, không ghi gì vào thư mục dữ liệu gốc.
- `project/tests` có ít nhất 3 test và pass.
- Đạt từ 70/100 điểm theo rubric.

## Gợi ý

### Gợi ý 1

Đọc notebook cũ theo thứ tự **thực thi**, không theo thứ tự trên màn hình: dòng chú thích ở đầu nói gì về cell 7 và 8?
Với mỗi cell, hỏi: nó đọc gì, sửa gì tại chỗ, phụ thuộc biến nào, và nếu chạy "Restart and run all" thì có chạy không.
Tiêu đề chart "Dec is best month!!" có đúng không khi dữ liệu có hai tháng 12?

### Gợi ý 2

Để `build` cho ra tệp giống hệt khi chạy lại: sắp dòng theo khoá cố định, ghi CSV với `index=False`, định dạng ngày và
số cố định (`date_format`, `float_format`), không ghi thời điểm chạy vào tệp. Tháng: `dt.to_period("M").dt.to_timestamp()`.
