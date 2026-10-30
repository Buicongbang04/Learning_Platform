---
title: Thiết kế mart khách hàng cho câu hỏi của Marketing (win-back trước Giáng sinh)
level: advanced
services: []
files:
  - path: starter/customer_mart.sql
    note: Mart khách hàng theo ngày chốt
  - path: starter/DESIGN.md
    note: Tài liệu thiết kế 300-1500 từ
  - path: tests/test_customer_mart.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py online-retail-ii
  - uv run pytest tracks/data-analyst/modules/09-analytics-data-modeling/exercises/advanced/01-marketing-customer-mart -q
---

## Mục tiêu

Đi từ yêu cầu mơ hồ "cho Marketing một bảng khách hàng" tới một mart có grain rõ, định nghĩa cột rõ, có ngày chốt,
có test, và một tài liệu thiết kế mà Marketing đọc hiểu được. Đây là việc DA senior làm khi một team bắt đầu tự phục
vụ (self-serve) dữ liệu.

## Đề bài

Ngày 01/12/2011, Marketing Manager viết: *"Mình cần một bảng khách hàng để chạy chiến dịch Giáng sinh: gửi email
kéo khách cũ quay lại, xem khách mua lần đầu tháng nào thì quay lại tốt, và biết khách nước nào đáng tiền."*

1. **Hỏi lại và chốt câu hỏi** (ghi trong `DESIGN.md`): ba câu hỏi cụ thể và quyết định đi kèm. Câu win-back đã được
   chốt: *khách có ít nhất 2 đơn và không mua trong hơn 90 ngày tính tới ngày chốt*.
2. **`starter/customer_mart.sql`**: dựng `mart_customer` từ `fct_sales_line` (dòng hợp lệ: `line_id`, `invoice_no`,
   `invoiced_at`, `customer_id`, `country`, `revenue`) và bảng `params(snapshot_date)`. Grain: một khách có mã có giao
   dịch **trước** ngày chốt. Cột bắt buộc và quy tắc ghi trong tệp (recency, số đơn, AOV, số tháng có mua, quốc gia
   chính, cờ win-back); thêm cột khác tuỳ thiết kế. Chạy lại được.
3. **`DESIGN.md`** theo khung có sẵn: câu hỏi, grain và các bảng (ít nhất nêu bảng thứ hai cho retention theo cohort
   và vì sao tách), định nghĩa cột, data test (mức error/warn), quyết định và giới hạn, kết quả trên dữ liệu thật
   (sheet `Year 2010-2011`, ngày chốt 01/12/2011).

Không có lời giải duy nhất: test chỉ chấm phần bắt buộc của mart và khung tài liệu; thiết kế còn lại chấm theo rubric
trong `SOLUTION.md`.

## Tiêu chí đạt

- Test trên dữ liệu nhỏ sinh trong test pass: một dòng mỗi khách có mã, chỉ tính giao dịch trước ngày chốt (kỳ nửa
  mở), recency, số đơn, AOV, số tháng, quốc gia chính và quy tắc hoà, cờ win-back ở ngưỡng 90 ngày; đổi ngày chốt thì
  mart đổi theo; tệp chạy lại được.
- Trên dữ liệu thật, ngày chốt 01/12/2011: tổng doanh thu và số đơn của mart khớp fact của khách có mã trước ngày chốt.
- `DESIGN.md` 300-1500 từ, đủ mục, không còn TODO, mục kết quả có số liệu thật. Thiết kế chấm theo rubric (từ 70/100
  là đạt).

## Gợi ý

### Gợi ý 1

Viết mart thành các CTE: lọc dòng có mã trước ngày chốt → tổng hợp theo khách (`min`, `max`, `count(DISTINCT ...)`,
`sum`) → quốc gia chính bằng `row_number() OVER (PARTITION BY customer_id ORDER BY revenue DESC, country)` → nối lại.
`date_diff('day', last_purchase_date, snapshot_date)` cho recency.

### Gợi ý 2

Retention theo cohort cần grain **khách × tháng** (một dòng mỗi tháng khách có mua), không nhồi được vào bảng một dòng
mỗi khách mà không mất thông tin. Trong mục giới hạn, nghĩ tới: khách vãng lai (16.5% doanh thu) không có trong mart;
hoá đơn bị huỷ sau đó vẫn nằm trong doanh thu gộp; khách đầu tiên của dữ liệu (12/2010) chưa chắc là khách mới.
