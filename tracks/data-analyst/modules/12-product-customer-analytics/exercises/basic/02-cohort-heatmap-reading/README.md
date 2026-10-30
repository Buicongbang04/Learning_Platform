---
title: Cohort retention heatmap trên Online Retail II, đọc theo hàng, cột và tháng lịch
level: basic
services: []
files:
  - path: starter/cohort_heatmap.ipynb
    note: 4 hàm TODO + đọc chart
  - path: tests/test_cohort_heatmap.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/12-product-customer-analytics/exercises/basic/02-cohort-heatmap-reading/starter/cohort_heatmap.ipynb
  - uv run pytest tracks/data-analyst/modules/12-product-customer-analytics/exercises/basic/02-cohort-heatmap-reading -q
---

## Mục tiêu

Dựng ma trận cohort retention bằng pandas với ô chưa quan sát được để trống, đổi nó sang tháng lịch để tách mùa
vụ khỏi chất lượng cohort, và vẽ đường retention trung bình có trọng số mà không bị đuôi ít cohort đánh lừa.

## Đề bài

Head of CRM hỏi: **"Khách mới có quay lại không, và khách mới năm nay có tốt hơn năm ngoái?"**. Dữ liệu: bộ
`online-retail-ii` (UCI, CC BY 4.0), cả hai sheet, bỏ phần trùng 01-09/12/2010, dòng hợp lệ theo định nghĩa dùng
chung (hàm `clean_sales` viết sẵn trong notebook). Tháng cuối dùng là 11/2011. Module 03 đã làm bảng cohort bằng
SQL; bài này không lặp lại phần SQL mà đi vào cách đọc. Mở `starter/cohort_heatmap.ipynb`:

1. `cohort_activity(sales, last)`: một dòng mỗi khách × tháng có mua, cột `customer_id`, `month`, `cohort`, `k`.
2. `retention_matrix(act, last)`: cohort × `k` (đủ mọi `k` từ 0 tới tuổi của cohort sớm nhất), `NaN` ở ô chưa quan
   sát được, `0.0` ở ô quan sát được mà không ai mua.
3. `calendar_view(matrix)`: bỏ `k = 0`, đổi cột sang tháng lịch `cohort + k`.
4. `retention_curve(matrix, sizes, min_cohorts=3)`: theo `k`, trung bình có trọng số cỡ cohort, trung bình đơn
   giản, số cohort; để trống điểm có ít hơn `min_cohorts` cohort.
5. Chạy các cell vẽ: heatmap cohort × `k`, calendar view, đường trung bình kèm số cohort, bảng so cohort cùng tháng
   hai năm. Đọc theo câu hỏi cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong app sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: một dòng mỗi khách × tháng, cohort tính trước khi cắt `last`, cột
  `k` đủ kể cả khi không ai mua, ô chưa quan sát được là `NaN` còn ô không ai mua là `0`, trọng số theo cỡ cohort.
- Trên bộ thật: 24 cohort, 5 850 khách, 300 ô quan sát được; m1 của cohort 01/2010 là 20.6%; đường có trọng số
  23.4% ở `k = 1`, 22.7% ở `k = 12`; điểm cuối có ít nhất 3 cohort là `k = 21`.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`known.InvoiceDate.dt.to_period("M")` cho tháng; `drop_duplicates()` trên cặp khách × tháng; cohort là
`groupby("customer_id").month.min()` tính **trước** khi lọc `month <= last`. Hiệu hai `Period` là một offset:
`(m - c).n` là số tháng.

### Gợi ý 2

`act.groupby(["cohort", "k"]).size().unstack(fill_value=0)` rồi `reindex(columns=range(...), fill_value=0)` và chia
cỡ cohort (`div(sizes, axis=0)`). Tuổi mỗi ô: `np.subtract.outer(tuổi_cohort, cột_k)`; `mask(tuổi < 0)` cho `NaN`.
Calendar view: `stack()` (giữ cả `NaN`, nên `dropna()`), thêm cột `cohort + k`, rồi `pivot`.
