---
title: RFM segmentation bằng luật nghiệp vụ và bảng hành động cho CRM
level: intermediate
services: []
files:
  - path: starter/rfm_segments.ipynb
    note: 4 hàm TODO + đọc bảng segment
  - path: tests/test_rfm_segments.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run jupyter lab tracks/data-analyst/modules/12-product-customer-analytics/exercises/intermediate/01-rfm-segments/starter/rfm_segments.ipynb
  - uv run pytest tracks/data-analyst/modules/12-product-customer-analytics/exercises/intermediate/01-rfm-segments -q
---

## Mục tiêu

Tính RFM tại một ngày chốt, chấm điểm bằng ngưỡng nghiệp vụ (R, F) và quintile (M), gom thành segment có tên bằng
bảng luật, rồi đọc bảng segment như đội CRM: ai mang lại doanh thu, ai đáng giữ, ai đáng bỏ qua, và định nghĩa nào
cần ghi chú trước khi gửi.

## Đề bài

Head of CRM hỏi: **"Quý tới có ngân sách cho ba chiến dịch. Nên nói chuyện với nhóm khách nào?"**. Dữ liệu: bộ
`online-retail-ii` (UCI, CC BY 4.0), sheet `Year 2010-2011`, dòng hợp lệ theo định nghĩa dùng chung (`clean_sales`
viết sẵn), ngày chốt 10/12/2011. Track Data Science đã làm RFM bằng k-means trên Olist; bài này làm RFM bằng luật,
cách CRM dùng hằng ngày. Mở `starter/rfm_segments.ipynb`:

1. `rfm_table(sales, snapshot)`: `recency` (ngày, bỏ phần giờ), `frequency` (số hoá đơn), `monetary` (tổng
   `revenue`) cho mỗi khách có mã.
2. `score_rfm(rfm, r_edges, f_edges)`: R và F theo ngưỡng (≤ 14, 30, 90, 180 ngày; 1, 2, 3-4, 5-9, từ 10 đơn), M theo
   quintile của hạng `method="first"`.
3. `assign_segment(scores, rules)`: luật đầu tiên khớp thắng, không khớp là `"other"`. Bảng `SEGMENTS` có sẵn.
4. `segment_summary(rfm, segment)`: số khách, doanh thu, trung vị R và F, tỉ trọng khách và doanh thu.
5. Chạy các cell vẽ và kiểm định nghĩa: lưới R × F, % khách vs % doanh thu, "new" có thật mới không, at_risk giá trị
   cao, độ tập trung của Monetary. Đọc theo câu hỏi cuối notebook. Báo cáo bài học: làm phần trắc nghiệm trong app
   sau khi chạy notebook.

Các hàm không được sửa dữ liệu đầu vào.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ pass: recency theo ngày, F đếm hoá đơn chứ không đếm dòng, ngưỡng đúng ở biên (14 là 5, 15 là
  4), M chia đều khi giá trị trùng, luật đầu tiên khớp thắng.
- Trên bộ thật: 4 338 khách; champions 507 khách, 46.8% doanh thu; hibernating 1 164 khách; at_risk 278 khách, 142
  khách có M từ 4.
- Trắc nghiệm trong app: đúng ít nhất 6/8 câu.

## Gợi ý

### Gợi ý 1

`g = known.groupby("Customer ID")`; recency là `(snapshot - g.InvoiceDate.max().dt.normalize()).dt.days`.
`np.searchsorted([14, 30, 90, 180], recency, side="left")` cho số mốc mà giá trị **vượt**: 0 khi ≤ 14, 4 khi > 180,
nên `R = 5 - ...`; với F thì `F = 1 + ...`.

### Gợi ý 2

`pd.qcut(rfm.monetary.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)`: xếp hạng trước để giá trị trùng
không làm `qcut` lỗi. Luật đầu tiên khớp: `next((name for name, rs, fs in rules if r in rs and f in fs), "other")`.
