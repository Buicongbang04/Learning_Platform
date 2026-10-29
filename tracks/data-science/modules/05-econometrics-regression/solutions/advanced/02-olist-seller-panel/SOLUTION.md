# Hướng làm: panel seller × tháng trên Olist

Bài Advanced không có đáp án duy nhất. Dưới đây là hướng làm, các số tham chiếu trên Olist thật, và
rubric.

## 1. Dựng panel

- Cùng định nghĩa với cả track: đơn giao xong, review trả lời muộn nhất mỗi đơn, review xấu là ≤ 2
  sao, trễ khi so nguyên timestamp.
- Đơn nhiều seller bị loại: không gán được trễ hay review cho một seller. Đó cũng là nhóm có review xấu
  cao nhất (README mục 5: OR 3.54), nên kết quả chỉ nói về đơn một seller.
- Thứ tự lọc quan trọng: lọc ô ít đơn **trước**, rồi mới đếm số tháng còn lại của mỗi seller. Làm
  ngược lại giữ cả seller chỉ có 1–2 ô đủ đơn.
- Kết quả với tham số mặc định: 3 322 ô, 313 seller, 20 tháng (01/2017 – 08/2018), trung vị 11 đơn
  mỗi ô.

## 2. Kết quả tham chiếu

| Spec | Hệ số `late_rate` | SE cluster seller |
| --- | --- | --- |
| Pooled | 0.536 | 0.022 |
| Seller FE | 0.509 | 0.023 |
| Two-way FE | 0.478 | 0.028 |
| Two-way FE, trọng số `n_orders` | 0.489 | 0.023 |
| Two-way FE, `min_orders=10` (1 507 ô, 146 seller) | 0.453 | 0.034 |
| Two-way FE, `min_orders=20` (612 ô, 60 seller) | 0.451 | 0.046 |
| Two-way FE + `late_rate` của ô trước đó (3 009 ô) | 0.463, lag 0.022 (SE 0.022) | |

Đọc:

- **Seller FE đổi hệ số ít** (0.536 → 0.509) vì phần lớn biến thiên của `late_rate` nằm **trong**
  seller: độ lệch chuẩn tổng 0.108, trong seller 0.100. Trễ chủ yếu là chuyện từng tháng (vận chuyển,
  mùa), không phải đặc tính cố định của seller.
- **Time FE đổi nhiều hơn** (0.509 → 0.478): tháng 11/2017 (Black Friday) và 02–03/2018 có tỉ lệ trễ
  trung bình 12%, 16%, 21% (các tháng khác phần lớn dưới 7%) và review xấu 14–20%. Những tháng đó khách
  khó chịu vì nhiều thứ cùng lúc.
- **Sai số đo lường**: lý thuyết nói `late_rate` của ô ít đơn nhiễu, kéo hệ số FE về 0, nên tăng
  `min_orders` phải làm hệ số tăng. Dữ liệu cho kết quả ngược lại (0.478 → 0.451), vì tăng
  `min_orders` cũng đổi **tổng thể** (chỉ còn seller lớn, có thể có quy trình xử lý khiếu nại tốt
  hơn). Bài viết tốt nêu được cả hai cơ chế và không khẳng định cơ chế nào thắng khi không tách được.
- **Lag**: trễ của tháng trước gần như không liên quan tới review xấu tháng này (0.022, SE 0.022):
  review phản ứng với đơn của chính nó, không phải với "danh tiếng" seller. Lưu ý "ô trước đó" có thể
  cách hơn một tháng vì panel không liên tục.

## 3. Các quyết định cần cân nhắc trong báo cáo

- **Đơn vị phân tích**: ô seller × tháng (tỉ lệ) hay đơn hàng (LPM với seller FE và month FE trên từng
  đơn). Mức đơn hàng dùng hết dữ liệu và không cần `min_orders`; mức ô dễ giải thích cho stakeholder.
  Cả hai đều bảo vệ được.
- **Trọng số**: không trọng số cho mỗi seller-tháng như nhau; trọng số `n_orders` gần với tác động
  trung bình trên đơn. Nói rõ chọn cái nào.
- **SE**: cluster theo seller (313 cluster, đủ). Cluster hai chiều (seller và tháng) đáng cân nhắc vì
  cú sốc theo tháng, nhưng chỉ có 20 tháng.
- **Nhân quả**: ít nhất các lý do: thay đổi trong seller theo thời gian (đổi đối tác vận chuyển),
  quan hệ hai chiều (hàng lỗi → đổi trả → giao lại trễ), selection (seller tồn tại đủ lâu), review tự
  nguyện (khách bực vì trễ có thể không viết review thay vì viết review xấu), review của đơn cuối
  08/2018 chưa đủ.
- **Con số cho stakeholder**: "trong cùng một seller, tháng có tỉ lệ trễ cao hơn 10 điểm phần trăm đi
  kèm review xấu cao hơn khoảng 4.8 điểm phần trăm". Không nói "giảm trễ 10 điểm sẽ giảm review xấu
  4.8 điểm" mà không có lời cảnh báo.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Panel đúng | 15 | Qua test; giải thích các bộ lọc và tổng thể chúng tạo ra |
| Ba spec và SE | 15 | Pooled / seller FE / two-way FE, cluster theo seller, ghi rõ |
| Diễn giải thay đổi qua các spec | 20 | Nói được mỗi FE loại confounder gì, dùng số (biến thiên trong seller, tháng cao điểm) |
| Phân tích thêm | 15 | Ít nhất hai kiểm tra độ vững (trọng số, `min_orders`, lag, mức đơn hàng…) và đọc đúng kết quả |
| Giới hạn | 20 | Ít nhất 3 lý do cụ thể cho dữ liệu này vì sao chưa phải nhân quả |
| Báo cáo cho stakeholder | 15 | Kết luận trước, con số có CI, không nói quá, có khuyến nghị hành động và hướng đo nhân quả |

Đạt từ 70 điểm là báo cáo đủ để đưa cho Head of Marketplace Quality.
