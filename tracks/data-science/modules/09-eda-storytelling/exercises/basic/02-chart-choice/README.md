---
title: Chọn biểu đồ theo câu hỏi và chuẩn bị dữ liệu cho bar chart
level: basic
services: []
files:
  - path: starter/charts.py
    note: 3 hàm TODO
  - path: tests/test_charts.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/basic/02-chart-choice -q
---

## Mục tiêu

Biến các quy tắc chọn biểu đồ thành code có thể kiểm thử: một hàm trả về "chart spec" (loại biểu
đồ, cách sắp xếp, trục có bắt buộc từ 0 không) và các hàm chuẩn bị dữ liệu cho bar chart (top N +
"Khác", không bỏ mất giá trị thiếu). Đây là cách các thư viện báo cáo tự động và công cụ BI làm.

## Đề bài

Trong `starter/charts.py`:

1. `choose_chart(goal, *, n_categories=1, n_points=None, ordered=False) -> dict` trả
   `{"chart", "sort", "zero_baseline"}` theo đúng bảng sau (xét từ trên xuống, dòng đầu khớp thì
   dùng):

   | goal | Điều kiện | chart | sort | zero_baseline |
   | --- | --- | --- | --- | --- |
   | `trend` | `n_categories > 5` | `small_multiples` | `natural` | False |
   | `trend` | còn lại | `line` | `natural` | False |
   | `comparison` | `n_categories > 7` | `barh` | `natural` nếu `ordered`, ngược lại `descending` | True |
   | `comparison` | còn lại | `bar` | như trên | True |
   | `distribution` | `n_points` biết và `< 30` | `strip` | None | False |
   | `distribution` | `n_categories > 1` | `box` | None | False |
   | `distribution` | còn lại | `histogram` | None | True |
   | `relationship` | `n_points` biết và `> 5000` | `hexbin` | None | False |
   | `relationship` | còn lại | `scatter` | None | False |
   | `composition` | `n_categories <= 5` | `stacked_bar_100` | None | True |
   | `composition` | còn lại | `barh` | `descending` | True |

   `goal` khác năm giá trị trên thì `raise ValueError`. Không có dòng nào trả `pie`.
2. `top_n_with_other(values, n, other_label="Khác") -> Series`: giữ n nhóm lớn nhất theo thứ tự giảm
   dần, cộng phần còn lại vào một dòng `other_label` **ở cuối** (kể cả khi nó lớn nhất). Không còn
   nhóm nào thì không thêm dòng đó. Giữ tên Series.
3. `category_share(df, col, n, other_label="Khác", missing_label="(thiếu)") -> DataFrame`: đếm số dòng
   theo giá trị của `col`, NaN thành nhóm `missing_label`, giữ top n + "Khác", cột `count` và
   `share` (cộng lại bằng 1).

Sau khi xong, chạy `category_share` trên `olist_products_dataset.csv` (cột `product_category_name`)
và trả lời: nếu dùng `value_counts()` mặc định thì 610 sản phẩm thiếu category đi đâu?

## Tiêu chí đạt

- `choose_chart` đúng mọi dòng của bảng, kể cả ranh giới (`n_points = 5000` là scatter, `n_categories
  = 5` của trend là line); bar luôn có `zero_baseline = True`; không bao giờ trả `pie`.
- `top_n_with_other` giữ tổng, "Khác" ở cuối, không thêm "Khác" rỗng.
- `category_share` đếm NaN thành nhóm riêng, `share` cộng lại bằng 1.
- Trên Olist thật: `cama_mesa_banho` dẫn đầu với 3 029 sản phẩm, top 5 + "Khác" (19 619) cộng lại
  32 951; nhóm `(thiếu)` có 610 sản phẩm.

## Gợi ý

### Gợi ý 1

Viết `choose_chart` như một chuỗi `if goal == ...: return ...` theo đúng thứ tự bảng. Đừng cố gom
gọn trước khi test xanh.

### Gợi ý 2

`sort_values(ascending=False, kind="stable")` rồi cắt `iloc[:n]` và `iloc[n:]`. `value_counts()`
mặc định `dropna=True`: dùng `fillna(missing_label)` trước khi đếm.
