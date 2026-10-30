---
title: Doanh thu bị nhân bản - kiểm grain và đo fan-out trên Online Retail II
level: basic
services: []
files:
  - path: starter/fanout_audit.ipynb
    note: 4 hàm TODO + đọc kết quả trên dữ liệu thật
  - path: tests/test_fanout_audit.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/09-analytics-data-modeling/exercises/basic/03-fanout-revenue-audit/starter/fanout_audit.ipynb
  - uv run pytest tracks/data-analyst/modules/09-analytics-data-modeling/exercises/basic/03-fanout-revenue-audit -q
---

## Mục tiêu

Tự tay định lượng hai lỗi grain hay gặp nhất trên dashboard: join với bảng có khoá lặp (fan-out) và tính metric
ở sai grain. Sau bài này bạn có bộ hàm kiểm khoá và đo fan-out dùng được trước mọi phép join trong công việc.

## Đề bài

Head of Merchandising thấy doanh thu theo sản phẩm cộng lại gần 12 triệu GBP trong khi Finance báo 10.67 triệu;
một analyst khác báo "giá trị đơn trung bình 20 GBP". Bộ `online-retail-ii`, sheet `Year 2010-2011`. Cell đầu
notebook tự tải bộ dữ liệu nếu chưa có và lưu cache parquet trong thư mục tạm. Mở `starter/fanout_audit.ipynb`:

1. `valid_lines(raw)` có sẵn (định nghĩa dòng hợp lệ chung của track, thêm cột `revenue`).
2. `key_profile(df, keys) -> dict`: `rows`, `distinct_keys`, `duplicated_keys`, `max_rows_per_key` (kiểu `int`),
   `is_unique` (kiểu `bool`); giá trị thiếu trong khoá tính là một giá trị khoá.
3. `join_inflation(left, right, on, measure) -> dict`: left join, so số dòng và tổng cột `measure` của `left`
   trước và sau; `inflation = after / before - 1`; cột trùng tên ở `right` nhận hậu tố `_right`.
4. `invoice_header(lines)`: một dòng mỗi hoá đơn (`Invoice`, `Customer ID`, `Country`, `invoiced_at` sớm nhất,
   `n_lines`, `invoice_total`), sắp theo `Invoice`, index `0..n-1`; `aov(lines)`: tổng doanh thu / số hoá đơn.
5. Chạy các cell `explore`: ba ứng viên khoá, fan-out của "bảng sản phẩm" theo quốc gia, tổng hoá đơn bị cộng
   lặp, AOV đúng và sai. Trả lời bốn câu hỏi cuối notebook, rồi làm phần trắc nghiệm trong app.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: đếm khoá lặp đúng (kể cả khoá thiếu), fan-out đo đúng số dòng và
  tổng, join many-to-one cho `inflation` bằng 0, header đúng grain, AOV là tổng chia số hoá đơn.
- Trên bộ thật: 9 566 cặp `(Invoice, StockCode)` lặp (nhiều nhất 20 dòng một cặp); `naive_dim` có 220 mã lặp, join
  ra 584 319 dòng và doanh thu tăng 12.27%; 19 960 hoá đơn, hoá đơn dài nhất 1 114 dòng; AOV 534.40 GBP; gắn
  tổng hoá đơn vào dòng rồi cộng ra gấp 68.25 lần.
- Trắc nghiệm trong app: đúng ít nhất 4/6 câu.

## Gợi ý

### Gợi ý 1

`sizes = df.groupby(keys, dropna=False).size()` cho số dòng mỗi khoá; `(sizes > 1).sum()` là số khoá lặp;
`len(sizes) == len(df)` là điều kiện unique. Ép `int(...)`, `bool(...)` để kết quả không mang kiểu numpy.

### Gợi ý 2

`invoice_header`: `groupby("Invoice", as_index=False).agg(**{"Customer ID": ("Customer ID", "first"), ...})`;
`"first"` bỏ qua giá trị thiếu, nên hoá đơn khách vãng lai vẫn ra `NaN`. Giờ hoá đơn lấy `"min"`: 42 hoá đơn có
dòng ghi lệch một phút.
