---
title: Trung bình của trung bình trên Rossmann - doanh số nửa cuối 2014 giảm 13% hay tăng 3%
level: intermediate
services: []
files:
  - path: starter/store_averages.ipynb
    note: 4 hàm TODO + trả lời CEO về hai con số mâu thuẫn
  - path: tests/test_store_averages.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py store-sales
  - uv run jupyter lab tracks/data-analyst/modules/07-descriptive-eda/exercises/intermediate/02-average-of-averages/starter/store_averages.ipynb
  - uv run pytest tracks/data-analyst/modules/07-descriptive-eda/exercises/intermediate/02-average-of-averages -q
---

## Mục tiêu

Gỡ hai con số mâu thuẫn trong một buổi họp bằng cách hỏi đúng hai câu: **trung bình của đơn vị nào** (dòng, cửa
hàng, khách) và **cùng tập đơn vị không** (balanced panel, mix). Viết được các hàm tính trung bình theo hai cách và
kiểm độ phủ dữ liệu trước khi so sánh hai kỳ.

## Đề bài

Họp quý chuỗi Rossmann: Finance báo *"doanh số nửa cuối 2014 giảm 13.2% so với cùng kỳ"*, Head of Ops báo
*"doanh số trung bình một cửa hàng mỗi ngày tăng 3.4%"*. CEO hỏi ai đúng, rồi hỏi thêm về cửa hàng loại b và doanh
số mỗi khách. Dữ liệu: bộ `store-sales` (`train.csv` 1 017 209 dòng cửa hàng-ngày, `store.csv` 1 115 cửa hàng). Mở
`starter/store_averages.ipynb`:

1. `open_days(train)`: bản sao các dòng `Open == 1` và `Sales > 0`.
2. `full_coverage_stores(train, start, end)`: danh sách cửa hàng (sắp tăng) có dòng cho **mọi ngày lịch** trong
   `[start, end]`; `Date` có thể là chuỗi hoặc datetime; dòng lặp không bù được ngày thiếu.
3. `mean_two_ways(df, by, value="Sales", unit="Store")`: cột `n_rows`, `n_units`, `row_mean` (mỗi dòng một phiếu),
   `unit_mean` (mean của mean từng đơn vị), index tên `by`.
4. `ratio_two_ways(df, by, num="Sales", den="Customers")`: cột `pooled` (tổng/tổng) và `mean_of_ratios`, chỉ
   dòng `den > 0`, index tên `by`.
5. Chạy các cell `explore`: độ phủ theo tháng, bốn cách so nửa cuối năm, chart doanh số tháng kèm số cửa hàng,
   bảng theo loại cửa hàng. Viết ra câu trả lời cho CEO và cách sửa dashboard. Báo cáo bài học: làm phần trắc
   nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa DataFrame đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: lọc ngày bán, độ phủ theo ngày lịch (không theo số dòng), hai cách
  lấy trung bình khi các đơn vị có số ngày khác nhau, bỏ dòng mẫu số 0.
- Trên bộ thật: 844 338 cửa hàng-ngày bán; 935 cửa hàng có đủ dữ liệu 07/2013–12/2014 (934 cho cả giai đoạn);
  doanh số TB/ngày nửa cuối 2014 so với cùng kỳ +3.41% trên mọi cửa hàng, +2.66% trên balanced panel; doanh số mỗi
  khách loại b 5.06 EUR, loại d 11.25 EUR.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Độ phủ: đếm **số ngày khác nhau** của mỗi cửa hàng trong cửa sổ (`nunique` trên ngày), so với
`len(pd.date_range(start, end))`. Đếm số dòng sẽ sai khi dữ liệu có dòng lặp.

### Gợi ý 2

`unit_mean`: `df.groupby([by, unit])[value].mean()` cho mean từng cửa hàng (MultiIndex), rồi
`.groupby(level=0).mean()` để lấy mean của chúng theo nhóm.
