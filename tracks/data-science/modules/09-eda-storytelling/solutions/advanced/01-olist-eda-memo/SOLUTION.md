# Hướng làm: notebook EDA và memo một trang

Bài Advanced không có một đáp án duy nhất. Dưới đây là hướng làm, các con số tham chiếu trên Olist
thật, các quyết định cần cân nhắc và rubric chấm.

## Các con số tham chiếu

| Con số | Giá trị |
| --- | --- |
| Đơn giao xong có review | 95 824 |
| Tỉ lệ trễ / review xấu toàn bộ | 7.99% / 12.81% |
| Review xấu ở đơn trễ / đúng hẹn | 54.1% / 9.2% |
| Review xấu tháng 5–10/2017 | 9.4–11.1% mỗi tháng |
| Tháng 1, 2, 3, 4/2018: review xấu | 13.7%, 19.4%, 21.2%, 11.8% |
| Tháng 1, 2, 3/2018: tỉ lệ trễ | 6.5%, 15.9%, 21.1% |
| Review xấu ở đơn đúng hẹn, tháng 1 → tháng 2/2018 | 10.3% → 10.7% |
| `decompose_change` tháng 1 → tháng 3/2018 | total +7.47, mix +7.69, rate −0.22 điểm |
| Bang review xấu cao nhất (n ≥ 30) | AL 21.3% (394 đơn, trễ 23.4%), MA 19.9% (712 đơn, trễ 19.2%) |
| Bang thấp nhất | AP 6.1% trên 66 đơn, khoảng Wilson 2.4–14.6% |

Câu chuyện chính: **gần như toàn bộ đợt tăng review xấu đầu 2018 đi cùng giao trễ** (mô tả qua
tách mix/rate, chưa phải ước lượng nhân quả). Giữ tỉ lệ trễ
của tháng 1, review xấu tháng 3 chỉ còn khoảng 13.6%.

## Các quyết định cần cân nhắc

- **Phạm vi thời gian**: bỏ đơn mua sau 2018-08-31 (chưa chín) và nói rõ; 2016 có quá ít đơn để so.
- **Định nghĩa**: dùng đúng định nghĩa chung (trễ so nguyên timestamp, review mới nhất); nếu đổi (trễ
  theo ngày) thì nêu và cho thấy kết luận có nhạy không.
- **Mix hay rate**: tách bằng `decompose_change`. Phần rate âm nhẹ: đơn trễ tháng 3 không bị chấm tệ
  hơn đơn trễ tháng 1.
- **Đi tiếp vào trễ**: tuyến bang seller → bang khách, số ngày hẹn, category cồng kềnh, seller có
  nhiều đơn trễ vượt kỳ vọng. Dữ liệu không có hãng vận chuyển: đây là giới hạn cần nêu, kèm câu hỏi
  cụ thể cho đội logistics.
- **Xếp hạng có n**: bang hay seller nhỏ luôn ở hai đầu; dùng `rate_by` với CI, không xếp hạng trần.
- **Tương quan và nhân quả**: "đơn trễ có tỉ lệ review xấu cao gấp sáu lần" là mô tả; tác động nhân
  quả của trễ cần phương pháp ở module 06. Memo dùng động từ cẩn thận.
- **Đề xuất có chủ sở hữu và cách đo**: logistics rà soát nguyên nhân; A/B nhắn tin chủ động (module
  03); dashboard tỉ lệ trễ theo tuần đã chín (bài Advanced 02).

Một memo mẫu đạt rubric dài khoảng 450 từ: tiêu đề "Review xấu lên 21% trong tháng 3/2018 đi cùng giao trễ, không thấy ở đơn
đúng hẹn"; ba bằng chứng là bảng tách mix/rate, review xấu ở đơn
đúng hẹn gần như không đổi, và chênh lệch đơn trễ/đúng hẹn ổn định qua các tháng.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Bảng phân tích và chất lượng dữ liệu | 15 | Ghi số dòng mất ở mỗi bước lọc; bỏ tháng chưa chín có lý do; định nghĩa thống nhất với track |
| Hiện tượng được xác nhận đúng | 10 | Có số theo tháng, có mức nền, không nhầm tháng chưa chín thành "giảm" |
| Phân tích nguyên nhân | 25 | Tách mix/rate, kiểm tra đơn đúng hẹn, đi tiếp vào giao trễ ít nhất một tầng (tuyến, ngày hẹn, category hoặc seller) |
| Trung thực thống kê | 15 | Có n và CI khi xếp hạng; nhận ra nhóm nhỏ; phân biệt tương quan và nhân quả; nhắc Simpson khi phù hợp |
| Biểu đồ | 10 | 2–3 biểu đồ đúng loại (bar sắp xếp, line theo tháng có tháng trống/chưa chín được xử lý), tiêu đề là kết luận, mẫu số ghi rõ |
| Memo | 20 | Kết luận trong câu đầu; SCQA rõ; ba lý lẽ có số; đề xuất có người làm và cách đo; mục giới hạn cụ thể |
| Ngắn gọn | 5 | Một trang; không kể quá trình làm; chi tiết kỹ thuật để trong notebook |

Đạt từ 70 điểm trở lên là đủ gửi cho lãnh đạo ở một công ty có văn hoá dữ liệu tốt.

## Sai lầm hay gặp

- Mở memo bằng "Tôi đã làm sạch dữ liệu và phân tích 9 bảng…".
- Đặt tiêu đề mô tả ("Phân tích review Olist") thay vì kết luận.
- Kết luận "AP có dịch vụ tốt nhất" từ 66 đơn.
- Đề xuất chung chung ("cải thiện giao hàng") không có người chịu trách nhiệm và cách đo.
