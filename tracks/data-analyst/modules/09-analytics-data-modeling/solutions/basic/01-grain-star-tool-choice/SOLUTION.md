# Lời giải: grain, fact/dimension và chỗ đặt logic

## Cách làm

Mỗi câu đi qua cùng một chuỗi: viết câu "một dòng = ..." cho bảng → kiểm khoá (hoặc tin con số đã kiểm ở lý
thuyết) → xác định metric ở grain nào và có cộng được không → hỏi ai dùng định nghĩa này và ở đâu. Phương án
sai trong bài đều là lỗi thật DA hay mắc, không phải phương án vô lý.

## Đáp án từng câu

| Câu | Đáp án | Lý do ngắn |
| --- | --- | --- |
| `retail-grain` | c | Không cặp cột nghiệp vụ nào là khoá; chỉ số thứ tự dòng của hệ thống nguồn là duy nhất |
| `pair-key` | d. 9 566 | Cùng mặt hàng được ghi nhiều dòng trên một hoá đơn (20 068 dòng liên quan) |
| `aov-grain` | a. 534.40 GBP | Doanh thu 10 666 702.54 / 19 960 hoá đơn |
| `measure-type` | b. `unit_price` | Cộng giá vô nghĩa; giá trung bình phải có trọng số số lượng |
| `semi-additive` | d | Tồn kho cộng theo cửa hàng được, theo ngày thì không: lấy ngày cuối kỳ |
| `grocery-snowflake` | a | Star schema gộp chuỗi customers → cities → countries vào một `dim_customer` phẳng |
| `grocery-role` | c | `employees` là dimension nhân viên bán hàng, fact trỏ qua `SalesPersonID` |
| `scd-choice` | b. SCD type 2 | Báo cáo cần vùng **tại thời điểm bán**, số cũ không được đổi |
| `unknown-member` | d. khoảng 16.5% | 1 755 277 / 10 666 703 GBP là của khách không có mã |
| `fanout-signal` | b | Tổng không đổi, tổng theo nhóm tăng: join với dimension có khoá lặp |
| `tool-shared-definition` | c | Vấn đề là định nghĩa, không phải công cụ vẽ: đưa về một model/metric chung |
| `tool-small-team` | a | Một DA, một database, cần ngay: SQL view có chú thích là đủ; dbt khi lớn hơn |

## Giải thích thêm

- **`retail-grain`**: (b) là câu trả lời "trông đúng" nhất, nhưng 9 566 cặp `(Invoice, StockCode)` lặp, và ngay
  cả bốn cột `(Invoice, StockCode, Quantity, Price)` vẫn lặp vì có 5 226 dòng trùng y hệt. Dedupe theo cặp đó
  là âm thầm xoá doanh thu thật (hoặc giữ lại bản trùng do lỗi, nếu nghiệp vụ xác nhận đó là lỗi: quyết định
  phải ghi ra). (a) là grain của một bảng khác (header hoá đơn), (d) là grain của một mart tổng hợp.
- **`aov-grain`**: 20.12 GBP (b) là trung bình **dòng**; 541.11 (c) là trung bình của 13 AOV tháng (trung bình
  của trung bình); 820 516 (d) là doanh thu trung bình mỗi tháng. Ba con số đều tính được từ cùng bảng, chỉ một
  con số trả lời câu hỏi.
- **`measure-type`**: `revenue` và `quantity` additive; `invoice_no` là degenerate dimension, không phải measure.
- **`semi-additive`**: (a) cộng cùng một lượng hàng 31 lần; (b) là trung bình mỗi cửa hàng, không phải tồn của
  chuỗi; (c) là một ngày tuỳ ý.
- **`grocery-snowflake`**: (b) đúng chuẩn hoá nhưng mỗi dashboard phải viết hai join và dễ viết sai; (c) chép
  thuộc tính mô tả vào hàng triệu dòng fact, đổi tên thành phố phải sửa fact; (d) dimension không cần có số.
- **`grocery-role`**: một bảng nhân viên có thể đóng nhiều vai (người bán, người duyệt) và mỗi vai là một khoá
  ngoại riêng trong fact (role-playing dimension). Thiếu cột số không làm nó bớt là dimension.
- **`scd-choice`**: type 1 (a) viết lại lịch sử: doanh thu quý trước của nhân viên chuyển vùng sẽ nhảy sang vùng
  mới. Xoá và tạo lại (c) làm mất liên kết lịch sử của một người.
- **`unknown-member`**: 3.7% (b) là tỉ trọng doanh thu của 22 mã phí/điều chỉnh, một nhóm khác cũng hay bị lọc
  nhầm.
- **`fanout-signal`**: đơn đến muộn (a) làm tăng cả tổng; tỉ giá (c) và cache (d) cũng không tạo chênh lệch giữa
  tổng và tổng theo nhóm.
- **`tool-shared-definition`**: sửa tay (a) sẽ lệch lại sau vài tháng; wiki (b) mô tả nhưng không ép ai dùng;
  đổi BI tool (d) không giải quyết notebook và Excel.
- **`tool-small-team`**: Looker (b) đúng hướng "semantic layer" nhưng quá nặng và đắt cho 6 bảng; giữ nguyên (c)
  là vấn đề đang cần sửa; file Excel (d) tạo thêm một nguồn sự thật nữa. Khi số model lên vài chục và có thêm
  người sửa, chuyển view sang dbt để có test và review.
