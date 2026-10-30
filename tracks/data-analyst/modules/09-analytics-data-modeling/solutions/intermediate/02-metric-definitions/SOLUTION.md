# Lời giải: metric definitions YAML, hai báo cáo một con số

## Cách làm

1. **`metrics.yml`** (lời giải đầy đủ cùng thư mục):
   - `orders`: `count_distinct` trên `invoice_no`, `additive_over_time: true` (mỗi hoá đơn thuộc đúng một tháng và
     một quốc gia).
   - `active_customers`: `count_distinct` trên `customer_id` (NULL không được đếm, nên khách vãng lai tự loại),
     `additive_over_time: false`.
   - `new_customers`: `count_distinct` trên `customer_id` với `filters: [invoice_month = first_purchase_month]`,
     `additive_over_time: true`; caveat về tháng 12/2010.
   - `aov`: `ratio`, `numerator: revenue`, `denominator: orders`, `additive_over_time: false`.
   - Mỗi metric có `description` viết cho người không biết SQL, `owner` là người duyệt thay đổi, `caveats` là lưu ý
     thật của dữ liệu (không phải câu chung chung).
2. **`report`**: `query(..., by=[by])` cho chi tiết, `query(...)` không dimension cho dòng `Tổng`, nối lại.
3. **`finance_monthly`, `marketing_country`**: gọi `report` với danh sách metric của từng team; Marketing sắp phần
   chi tiết theo doanh thu rồi nối dòng `Tổng` ở cuối.

## Vì sao như vậy

- **Dòng Tổng tính lại, không cộng**: đây là chỗ báo cáo hay sai nhất. Cộng `active_customers` các quốc gia ra 4 346
  (8 khách mua từ hai nước bị đếm hai lần); cộng các tháng ra 13 054. Trung bình AOV các tháng ra 541.11 thay vì
  534.40. Một dòng Tổng tính lại từ định nghĩa luôn đúng, với mọi loại metric.
- **`additive_over_time` là thông tin cho người dùng, không chỉ cho máy**: người kéo metric vào BI tool cần biết
  có được bật "Sum" ở dòng tổng hay không. `new_customers` cộng được qua tháng (mỗi khách mới đúng một tháng) nhưng
  không chắc cộng được qua quốc gia (khách mua tháng đầu ở hai nước). Ghi điều này vào caveats nếu team hay xem theo
  quốc gia.
- **Owner**: người chịu trách nhiệm định nghĩa, duyệt mọi pull request đổi định nghĩa và trả lời "số này tính thế
  nào". Không có owner, định nghĩa trôi theo người sửa gần nhất.
- **Vì sao hai dashboard cũ lệch** (đọc `legacy_reports.sql`):
  - Finance cũ cộng **mọi dòng**, kể cả hoá đơn huỷ (số âm): tháng 11/2011 ra 1 461 756.25 = 1 509 496.33 −
    47 740.08 giá trị huỷ. Đó gần với doanh thu ròng, một metric hợp lệ khác, nhưng mang nhãn "doanh thu".
  - Marketing cũ lọc đúng dòng hợp lệ nhưng chỉ lấy khách có mã: 1 161 817.38 (mất 347 678.95 GBP của khách vãng
    lai), và "AOV" là `avg(Quantity * Price)`: trung bình **dòng hàng** (18.00 GBP), không phải trung bình đơn
    (AOV của khách có mã là 437.27 GBP, của mọi đơn là 545.14 GBP).
  - Tháng 12/2011: Finance cũ 433 686.01 so với gộp 638 810.68; chênh 205 124.67 là toàn bộ giá trị hoá đơn huỷ của
    tháng, trong đó riêng C581484 (huỷ hoá đơn 581483) là 168 469.60.
- Cách sửa đúng không phải chọn một con số thắng, mà đặt tên: `revenue` (gộp), một metric `net_revenue` nếu
  Finance cần (trừ huỷ), một metric `identified_revenue` cho CRM. Mỗi dashboard hiện tên metric nó dùng.

## Con số tham chiếu (bộ thật, sheet `Year 2010-2011`)

| Báo cáo | Giá trị |
| --- | --- |
| Finance 11/2011 | revenue 1 509 496.33; orders 2 769; aov 545.14 |
| Finance dòng Tổng | revenue 10 666 702.54; orders 19 960; aov 534.40 (trung bình 13 AOV tháng: 541.11) |
| Marketing United Kingdom | revenue 9 025 222.08; orders 18 019; active 3 920 |
| Marketing dòng Tổng | active 4 338; new 4 338; cộng các dòng quốc gia: active 4 346 |
| Finance cũ 11/2011, 12/2011 | 1 461 756.25; 433 686.01 |
| Marketing cũ 11/2011 | revenue 1 161 817.38; "aov" 18.00 |

## Đáp án trắc nghiệm

- `finance-gap` (b): giá trị hoá đơn huỷ tháng 11 là −47 740.08. Khách vãng lai (a) là phần lệch của Marketing;
  mã phí (c) có trong cả hai con số; dòng giá 0 (d) có doanh thu 0.
- `marketing-aov` (c): `avg(Quantity * Price)` trên dòng có mã khách.
- `total-active` (d) **4 346**. 13 054 (b) là tổng theo tháng; 3 920 (c) là riêng United Kingdom.
- `dec-legacy` (a): 168 470 trên 205 125 GBP chênh lệch là một hoá đơn bị huỷ 12 phút sau khi lập. Tháng chưa đủ
  (b) làm cả hai con số nhỏ như nhau, không tạo chênh lệch giữa chúng.
- `additive-new` (a). (c) sai: filter không làm `count distinct` cộng được; tính cộng được đến từ việc mỗi khách
  thoả filter ở đúng một tháng.
- `owner-role` (d).
