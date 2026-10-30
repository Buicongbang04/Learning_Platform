# Lời giải: câu hỏi làm rõ, scoping và phân loại yêu cầu

## Cách làm

Mỗi câu đi qua cùng một phép thử: **câu trả lời có làm thay đổi việc mình sẽ làm không?** Câu hỏi làm rõ tốt
chặn một kiểu làm sai cụ thể (trả lời câu hỏi sai, so sánh sai, làm quá chính xác hoặc quá ít, làm việc không ai
dùng). Câu hỏi làm rõ tồi hỏi điều mình tự tra được, đẩy việc kỹ thuật sang người hỏi, hoặc chỉ về hình thức.

Với phân loại: self-serve (đã có số chính thức) → hỏi lại (không có quyết định) → dashboard (câu hỏi lặp lại) →
dự án (> nửa ngày) → ad-hoc.

## Đáp án từng câu

| Câu | Đáp án | Ý chính |
| --- | --- | --- |
| `revenue-by-country` | b | Hỏi quyết định phía sau |
| `dashboard-dropped` | c | Loại nhánh dữ liệu trước: kỳ chưa đủ |
| `customer-analysis` | a | Quyết định và nhóm khách cắt phạm vi |
| `if-result-x` | d | Không quyết định nào phụ thuộc kết quả |
| `bad-clarifying` | c | Câu kém: hỏi công cụ thay vì định nghĩa "tốt" |
| `draft-reply` | a | Trả lời kèm bản nháp để người bận chỉ cần xác nhận |
| `scope-creep` | c | Thương lượng lại mốc, để người hỏi chọn |
| `precision-needed` | b | Độ chính xác cần quyết định effort |
| `out-of-scope` | d | Ghi rõ điều không làm và lý do |
| `self-serve` | a | Đã có số chính thức: gửi link, cải thiện khả năng tự dùng |
| `quadrant` | c | Impact thấp, effort cao |
| `recurring-to-dashboard` | b | Câu ad-hoc lặp lại thành ticket dashboard |

### `revenue-by-country`: b

"Anh cần số này để quyết định việc gì?" mở ra mọi thứ còn lại: nếu là chọn thị trường năm sau thì cần 12 tháng
đủ, so cùng kỳ, kèm số khách; nếu chỉ để dán slide họp tuần thì mười phút là đủ. (a) là định dạng, hỏi sau cũng
được. (c) đẩy việc kỹ thuật sang người không biết schema. (d) tự tra được bằng một câu `MIN(order_date)`.

### `dashboard-dropped`: c

Ngày 3 của tháng, doanh thu "tháng này" chỉ có hai ngày dữ liệu; so với cả tháng trước là so sánh kỳ chưa đủ, lỗi
kinh điển của module 03 và 08. Kiểm cái rẻ nhất và hay đúng nhất trước, rồi trả lời COO trong vài phút: "so cùng 2
ngày đầu tháng trước thì giảm/tăng X%". (a) đẩy việc đọc số sang COO. (b) hỏi cách cắt khi chưa biết có vấn đề
thật không. (d) có thể mất một tuần cho một vấn đề không tồn tại.

### `customer-analysis`: a

"Phân tích khách hàng" có thể là mười dự án khác nhau. Biết chị ấy đang cân nhắc chương trình gì (loyalty,
win-back, ưu đãi khách sỉ) và cho nhóm nào thì phạm vi tự thu hẹp. (b) là lựa chọn phương pháp, việc của DA, và
chọn trước khi biết câu hỏi là đặt xe trước ngựa. (c) là hình thức. (d) mở rộng thay vì thu hẹp phạm vi.

### `if-result-x`: d

Đây đúng là mục đích của câu hỏi "nếu kết quả là X thì làm gì khác": khi mọi kết quả dẫn tới cùng hành động (chạy
tiếp vì hợp đồng đã ký), phân tích lớn không thay đổi quyết định năm nay. Làm một bản nhỏ cho đợt gia hạn hợp đồng
năm sau, hoặc dời lại. (a) dùng phân tích để thắng tranh luận chứ không để hỗ trợ quyết định. (b) sai: câu hỏi
vừa tiết kiệm cho bạn nhiều ngày. (c) đổi phương pháp không làm quyết định phụ thuộc kết quả.

### `bad-clarifying`: c

SQL hay Python là quyết định của DA, người hỏi không cần và thường không biết trả lời. Ba câu còn lại đều tốt: (a)
định nghĩa "tốt" thành metric; (b) hỏi có nhóm đối chứng tự nhiên không (quyết định phương pháp đo, module 11);
(d) hỏi quyết định phía sau.

### `draft-reply`: a

Người bận trả lời "đúng" hoặc sửa một chữ nhanh hơn rất nhiều so với trả lời năm câu hỏi mở (b). Bản nháp cũng cho
thấy bạn đã suy nghĩ, và nếu đoán sai thì sai được sửa ngay. (c) dẫn tới làm thừa và vẫn có thể trả lời sai câu
hỏi. (d) chậm cả tuần cho một việc có thể làm rõ bằng một tin nhắn.

### `scope-creep`: c

Scope creep không xấu; im lặng nhận nó mới xấu. Nói rõ chi phí (2 ngày) và đưa hai lựa chọn để người hỏi quyết
định cái gì quan trọng hơn: đúng hạn hay đầy đủ. (a) tạo thói quen ước lượng sai và kiệt sức. (b) cứng nhắc,
có thể phần chia theo kênh là thứ quan trọng nhất. (d) phá cam kết mà không báo.

### `precision-needed`: b

Một con số cho họp nội bộ (ước lượng đúng hướng, vài giờ) và một con số phải khớp sổ kế toán (đối soát từng
dòng, định nghĩa hoàn hàng theo ngày hoàn hay ngày bán, có thể vài ngày) khác nhau về effort gấp nhiều lần. (a),
(c), (d) là hình thức trình bày, không đổi effort.

### `out-of-scope`: d

Mục ngoài phạm vi chặn kỳ vọng sai: "phân tích khách quay lại" dễ bị hiểu là có cả dự báo và nhân quả. Ghi ra kèm
lý do (không có dữ liệu thí nghiệm, để vòng sau) để stakeholder đồng ý trước. (a) và (b) ngược mục đích. (c) là chi
tiết kỹ thuật, không phải phạm vi.

### `self-serve`: a

Số đã có trên dashboard chính thức: tự kéo lại bằng SQL (b) tốn thời gian mỗi tuần và có nguy cơ ra số lệch
dashboard, làm mất niềm tin vào cả hai. Gửi link kèm cách lọc giúp trưởng vùng tự làm từ tuần sau, và ghi lại câu
hỏi: nếu nhiều người không tìm ra bộ lọc, dashboard cần sửa. (c) tạo thêm một phiên bản số. (d) đúng tinh thần
self-serve nhưng sai cách: không ai học được gì từ một lời từ chối.

### `quadrant`: c

Không có quyết định đi kèm là impact thấp; 5 ngày là effort cao. Money pit: từ chối, hoặc đề xuất cách rẻ hơn (ví
dụ tính cho một quý mẫu nếu có câu hỏi cụ thể), hoặc hỏi lại xem có quyết định nào ẩn phía sau không.

### `recurring-to-dashboard`: b

Lần hỏi thứ hai bởi người khác là tín hiệu câu hỏi lặp lại và có nhiều người cần. Trả lời lần này (người hỏi đang
chờ), đồng thời mở ticket đưa metric vào dashboard có định nghĩa chính thức. (a) đúng cho hôm nay nhưng tuần sau
sẽ lại có người hỏi. (c) quá nặng cho một câu ad-hoc nhỏ. (d) vô lý: hai người khác nhau có quyền hỏi.
