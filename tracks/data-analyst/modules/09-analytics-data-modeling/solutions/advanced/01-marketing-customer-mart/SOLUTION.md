# Hướng làm: mart khách hàng cho Marketing

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm, các quyết định cần cân nhắc, con số tham chiếu
trên dữ liệu thật và rubric chấm.

## Hướng làm

1. **Chốt câu hỏi trước khi chọn cột.** Ba câu hỏi hợp lý và quyết định đi kèm:
   - Win-back: khách nào (≥ 2 đơn, > 90 ngày không mua) nhận email ưu đãi Giáng sinh? Quyết định: danh sách gửi và
     ngân sách voucher.
   - Retention theo cohort: khách mua lần đầu tháng nào quay lại tốt nhất? Quyết định: tháng nào nên tăng chi tiêu
     kéo khách mới.
   - Giá trị theo quốc gia: thị trường nào có giá trị mỗi khách cao? Quyết định: phân bổ ngân sách quảng cáo theo nước.
2. **Hai bảng, hai grain.**
   - `mart_customer`: một dòng = một khách có mã tại ngày chốt (trả lời win-back và giá trị theo quốc gia).
   - `mart_customer_month`: một dòng = một khách × một tháng có mua (trả lời retention: đếm khách theo
     `cohort_month` × số tháng kể từ cohort). Gộp vào một bảng sẽ phải lưu danh sách tháng trong một ô hoặc nhân bản
     cột khách, cả hai đều làm sai `SUM` khi Marketing kéo vào BI.
3. **SQL**: CTE lọc `customer_id IS NOT NULL AND invoiced_at < snapshot_date` → tổng hợp theo khách → quốc gia chính
   bằng `row_number()` → `date_diff` cho recency → cờ win-back. Ngày chốt là tham số (`params`), không viết cứng
   `current_date`: chạy lại cho ngày chốt cũ phải ra đúng danh sách đã gửi (tái lập, kiểm toán chiến dịch).

## Con số tham chiếu (sheet `Year 2010-2011`, ngày chốt 01/12/2011)

| Đại lượng | Giá trị |
| --- | --- |
| Khách trong mart | 4 297; doanh thu 8 393 215.11 GBP; 17 754 đơn (khớp fact của khách có mã trước ngày chốt) |
| Khách có ≥ 2 tháng mua | 2 605 |
| Khách mua đúng 1 đơn | 1 538, trong đó 864 đã hơn 90 ngày không mua (không thuộc win-back theo định nghĩa) |
| Mục tiêu win-back | **593 khách**, 656 129 GBP doanh thu lịch sử; trung vị 653 GBP/khách, 2 đơn; recency trung bình 174 ngày; 541 khách ở United Kingdom |
| Theo quốc gia chính | United Kingdom 3 886 khách, 6.84 triệu GBP (1 759 GBP/khách); Netherlands 9 khách, 273 718 GBP (30 413 GBP/khách); EIRE 3 khách, 258 567 GBP |
| Retention cohort (tháng +1, +3) | 12/2010 (885 khách): 36.6%, 38.4%; 01/2011 (417): 22.1%, 23.0%; 02/2011 (380): 18.7%, 28.4% |

Đọc số như một DA: cohort 12/2010 "giữ khách" tốt hơn hẳn các cohort sau (36.6% so với 15–24% ở tháng +1 của các cohort 01–10/2011), nhưng đó phần lớn là ảo giác dữ liệu:
cohort này gồm cả khách cũ đã mua từ trước 12/2010 (dữ liệu sheet bắt đầu từ đó). Netherlands và EIRE "đáng tiền" là
vài khách sỉ; báo số khách bên cạnh doanh thu, và đừng phân bổ ngân sách quảng cáo theo trung bình của 3 khách.

## Các quyết định cần cân nhắc

- **Ngày chốt và kỳ nửa mở**: `invoiced_at < snapshot_date` để giao dịch của chính ngày chốt không lọt vào nửa chừng.
- **Khách vãng lai**: không có mã, không gửi email được; 16.5% doanh thu không có trong mart. Ghi rõ để Marketing
  không đối chiếu tổng mart với doanh thu công ty.
- **Doanh thu gộp hay ròng**: khách có đơn lớn bị huỷ sau đó (ví dụ khách 16446 với hoá đơn 581483 ngày 09/12/2011)
  sẽ có `revenue` phình nếu ngày chốt sau ngày đó. Đề xuất cột `net_revenue` hoặc ghi caveat.
- **Ngưỡng 90 ngày**: là quyết định nghiệp vụ; nêu cách kiểm (phân phối khoảng cách giữa hai đơn liên tiếp của khách
  quay lại) và để ngưỡng là tham số.
- **Khách nhiều quốc gia**: `main_country` theo doanh thu, hoà theo tên; 8 khách bị ảnh hưởng. Không dùng
  `current_country` cho phân tích giá trị theo thị trường.
- **Cohort đầu dữ liệu**: dùng thêm sheet 2009-2010 làm lịch sử nếu cần retention đúng cho 12/2010.
- **Test**: `unique` + `not_null` trên `customer_id` (error); đối soát doanh thu và số đơn với fact (error);
  `recency_days >= 0`, `orders >= 1` (error); tỉ lệ khách win-back nhảy quá 50% so với lần chạy trước (warn).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Câu hỏi và quyết định | 15 | Ba câu hỏi cụ thể, mỗi câu gắn một quyết định của Marketing; nói được câu nào mart không trả lời |
| Grain | 20 | Mỗi bảng có câu "một dòng = ..."; tách bảng khách × tháng cho retention và giải thích vì sao không gộp |
| Định nghĩa cột | 15 | Mỗi cột: công thức, tính tới ngày nào, cộng được không; win-back định nghĩa đúng ngưỡng và kỳ nửa mở |
| SQL | 15 | Test pass; ngày chốt là tham số; không viết cứng ngày; chạy lại được |
| Data test | 10 | Khoá, đối soát với fact, khoảng hợp lý; phân biệt error/warn có lý do |
| Quyết định và giới hạn | 15 | Ít nhất ba trong: khách vãng lai, gộp/ròng và đơn bị huỷ, cohort đầu dữ liệu, ngưỡng 90 ngày, khách nhiều nước |
| Kết quả thật | 10 | Số khách, số khách win-back và doanh thu của nhóm đó khớp mart; một câu trả lời có số cho mỗi câu hỏi, có cảnh báo khi số dựa trên vài khách |

Từ 70 điểm: Marketing có thể dùng mart và tài liệu mà không cần hỏi lại DA.

## Sai lầm hay gặp

- Một bảng "khách 360" trộn grain khách và grain tháng, rồi Marketing `SUM` cột doanh thu tháng trên bảng khách.
- Dùng `current_date` thay cho ngày chốt: danh sách gửi hôm qua không tái lập được.
- Tính recency tới ngày cuối của dữ liệu (09/12/2011) trong khi chiến dịch chốt ngày 01/12.
- Báo "cohort 12/2010 retention tốt nhất" mà không nói cohort đó gồm cả khách cũ.
