---
title: LTV theo cohort, CAC payback và bảng CAC tối đa với giả định ghi rõ
level: intermediate
services: []
files:
  - path: starter/ltv_payback.ipynb
    note: 4 hàm TODO + đọc bảng kịch bản
  - path: tests/test_ltv_payback.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/12-product-customer-analytics/exercises/intermediate/03-cohort-ltv-payback/starter/ltv_payback.ipynb
  - uv run pytest tracks/data-analyst/modules/12-product-customer-analytics/exercises/intermediate/03-cohort-ltv-payback -q
---

## Mục tiêu

Tính LTV bằng công thức đơn giản và bằng cohort, giải thích vì sao hai con số lệch nhau, rồi trả lời "được chi bao
nhiêu để có một khách" khi không có số chi phí: payback theo cohort và bảng CAC tối đa theo biên và thời gian hoàn vốn,
mọi giả định ghi rõ.

## Đề bài

CMO hỏi: **"Một khách mới đáng bao nhiêu, và được chi tối đa bao nhiêu để có một khách?"**. Dữ liệu: bộ
`online-retail-ii` (UCI, CC BY 4.0), cả hai sheet, bỏ phần trùng 01-09/12/2010, dòng hợp lệ theo định nghĩa dùng chung
(`clean_sales`, `cohort_sizes` viết sẵn); tháng cuối 11/2011. Bộ dữ liệu không có giá vốn và chi phí marketing: mọi
biên lợi nhuận và CAC là **ví dụ giả định**. Mở `starter/ltv_payback.ipynb`:

1. `simple_ltv(aov, orders_per_year, margin, retention)`: công thức LTV đơn giản; `ValueError` khi retention ngoài
   `[0, 1)`.
2. `cohort_ltv(sales, last)`: doanh thu luỹ kế mỗi khách theo cohort × tuổi `k`, đủ mọi cột `k`, `NaN` ở ô chưa quan
   sát được.
3. `payback_month(ltv, cac, margin)`: tháng đầu tiên lợi nhuận gộp luỹ kế mỗi khách đạt CAC, `<NA>` nếu chưa đạt.
4. `max_cac_table(ltv, sizes, margins, horizons)`: CAC tối đa để hoàn vốn trong `h` tháng, theo biên, trung bình có
   trọng số cỡ cohort.
5. Chạy các cell khám phá: LTV đơn giản, LTV theo cohort, doanh thu 12 tháng đầu của khách mới 2010, đường LTV với
   ngưỡng CAC giả định, bảng kịch bản. Đọc theo câu hỏi cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong
   app sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: luỹ kế đúng kể cả tháng không ai mua, chia cỡ cohort, ô chưa quan sát được là `NaN`,
  payback `<NA>` khi chưa đạt, bảng CAC chỉ lấy cohort đã quan sát được và trọng số theo cỡ cohort.
- Trên bộ thật: LTV cohort 01/2010 là 423 GBP ở tháng 0 và 2 043 GBP sau 12 tháng; với CAC 200 và biên 35% (giả
  định), cohort 12/2010 hoàn vốn ở tháng 4; CAC tối đa để hoàn vốn trong 3, 6, 12 tháng là 235, 332, 502 GBP.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

Giống ma trận retention của bài Basic 02, nhưng cộng `revenue` thay vì đếm khách:
`groupby(["cohort", "k"]).revenue.sum().unstack(fill_value=0)`, `reindex` đủ cột `k`, rồi `cumsum(axis=1)` **trước**
khi che ô chưa quan sát được, và chia số khách của cohort.

### Gợi ý 2

Payback: lấy từng hàng, `dropna()`, tìm `k` đầu tiên có giá trị `>= cac / margin`; trả
`pd.Series(..., dtype="Int64")`. Bảng CAC: với `h`, cột là `ltv[h - 1].dropna()`; trọng số `sizes.reindex(col.index)`.
