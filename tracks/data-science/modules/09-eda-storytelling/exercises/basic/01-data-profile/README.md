---
title: Profiling một bảng dữ liệu
level: basic
services: []
files:
  - path: starter/profile.py
    note: 3 hàm TODO
  - path: tests/test_profile.py
    note: Không sửa
run:
  - uv run python data/download_olist.py
  - uv run pytest tracks/data-science/modules/09-eda-storytelling/exercises/basic/01-data-profile -q
---

## Mục tiêu

Viết bộ profiling tối thiểu bạn chạy trên mọi bảng mới trước khi phân tích: thiếu bao nhiêu, khoá
có thật là khoá không, giá trị nào nằm xa phần còn lại. Hiểu vì sao "outlier theo IQR" không đồng
nghĩa với "dữ liệu sai".

## Đề bài

Trong `starter/profile.py`, cài theo docstring:

1. `profile(df) -> DataFrame`: mỗi cột của `df` là một dòng (giữ đúng thứ tự cột), các cột kết quả
   đúng thứ tự `dtype, n_missing, missing_rate, n_unique, top_value, top_share`. `top_share` tính
   trên số ô **không thiếu**; cột toàn NaN có `n_unique = 0`, `top_value = None`, `top_share = NaN`.
2. `duplicate_report(df, key) -> dict`: `n_rows`, `n_unique_keys`, `n_rows_dup_key` (mọi dòng có key
   xuất hiện từ hai lần, đếm cả bản đầu), `n_exact_duplicates` (dòng trùng hoàn toàn với một dòng
   trước nó).
3. `iqr_outliers(s, k=1.5) -> Series[bool]`: True với giá trị ngoài
   $$[Q_1 - k\,\mathrm{IQR},\ Q_3 + k\,\mathrm{IQR}]$$, NaN thành False, giữ index của `s`.

Sau khi xong, chạy trên Olist thật và trả lời:

- `review_id` có phải khoá của `olist_order_reviews_dataset.csv` không? Cặp nào mới là khoá?
- `iqr_outliers` đánh dấu bao nhiêu phần trăm giá item (`price`) là outlier? Đó có phải lỗi dữ liệu
  không?

## Tiêu chí đạt

- `profile` đúng thứ tự dòng/cột, đúng `missing_rate`, `n_unique` không đếm NaN, `top_share` trên ô
  không thiếu, xử lý cột toàn NaN.
- `duplicate_report` đúng với khoá đơn và khoá ghép.
- `iqr_outliers` đúng ở cả hai đuôi, đúng với `k` khác 1.5, giữ index; trên phân phối chuẩn đánh dấu
  khoảng 0.7%.
- Trên Olist thật: `review_id` có 98 410 giá trị khác nhau trên 99 224 dòng, 1 603 dòng có key lặp,
  cặp `(review_id, order_id)` không lặp; nội dung review thiếu 58.7%; 8 427 giá item bị đánh dấu.

## Gợi ý

### Gợi ý 1

`s.value_counts(dropna=True)` sắp giảm dần theo tần suất: phần tử đầu là `top_value`, và tổng của nó
là số ô không thiếu. `df.duplicated(subset=key, keep=False)` đánh dấu mọi bản của key lặp.

### Gợi ý 2

`q1, q3 = s.quantile([0.25, 0.75])` tự bỏ NaN. So sánh với NaN cho False, nhưng hãy `fillna(False)`
và `astype(bool)` để kết quả chắc chắn là bool.
