# Hướng làm: ước lượng đúng từ một khảo sát bị lệch

## Con số trên Olist thật

Tổng thể: 95 824 đơn giao xong có review, tỉ lệ review xấu 12.81%, 8.0% là đơn trễ. Khảo sát mô phỏng
(đơn trễ chọn với xác suất 0.5, đúng hẹn 0.05, seed 0) lấy được 8 224 đơn, trong đó **46.7%** là đơn
trễ.

| Ước lượng | Tỉ lệ không hài lòng |
| --- | --- |
| Thô (trung bình mẫu) | 30.0% |
| Post-stratification theo trễ | 12.9%, CI 95% bootstrap phân tầng [12.1%, 13.7%] |
| IPW với xác suất chọn đã biết | 13.0% |
| Sự thật (toàn bộ tổng thể) | 12.8% |

Con số thô gấp hơn hai lần sự thật. Một báo cáo "30% khách không hài lòng" dẫn tới quyết định sai về
ngân sách CSKH.

## Vì sao hiệu chỉnh được, và khi nào không

Post-stratification đúng khi **trong mỗi tầng, người được chọn giống người không được chọn** (missing at
random theo biến tầng). Ở đây xác suất chọn chỉ phụ thuộc trạng thái trễ, nên trong tầng "trễ", mẫu là
mẫu ngẫu nhiên của mọi đơn trễ. Nếu người không hài lòng nghe máy nhiều hơn **ngay cả khi cùng trạng
thái trễ** (missing not at random), không biến quan sát nào cứu được: hiệu chỉnh theo trễ vẫn còn lệch
lên. Cách xử lý MNAR: thiết kế lại thu thập (gọi lại nhiều lần người không nghe máy, khuyến khích trả
lời), phân tích độ nhạy (giả định người không trả lời có tỉ lệ không hài lòng thấp hơn x điểm thì kết
luận đổi thế nào), hoặc dùng dữ liệu hành vi không phụ thuộc trả lời (mua lại, khiếu nại).

## Post-stratification vs IPW

- **IPW** cần biết xác suất chọn π_i của từng người. Trong khảo sát thật hiếm khi biết; phải ước lượng
  (mô hình propensity), và trọng số cực lớn khi π nhỏ làm variance tăng vọt. Kỹ thuật này là nền của
  causal inference (module 06).
- **Post-stratification** chỉ cần tỉ trọng tầng trong tổng thể (biết từ hệ thống), ổn định hơn, nhưng
  số tầng bị giới hạn: tầng nhiều chiều thì nhiều ô rỗng. Khi đó dùng raking (khớp lần lượt từng biên)
  hoặc MRP (multilevel regression + post-stratification).

## Các quyết định thiết kế cần cân nhắc

- **Chọn biến tầng.** Biến vừa ảnh hưởng xác suất trả lời vừa liên quan tới mức hài lòng (trễ, vùng,
  category, giá trị đơn). Thêm tầng không liên quan chỉ tăng variance.
- **CI.** Bootstrap phân tầng giữ đúng thiết kế (số quan sát mỗi tầng cố định). CI không tính bất
  định của tỉ trọng tổng thể; ở đây tỉ trọng lấy từ hệ thống nên coi là đã biết.
- **Thiết kế lần sau.** Stratified sampling chủ động (chọn theo quota mỗi tầng, oversample tầng nhỏ
  có chủ đích rồi tính trọng số), cỡ mẫu theo độ chính xác cần (với p ≈ 13%, sai số ±1 điểm cần khoảng
  4 300 phản hồi nếu chọn ngẫu nhiên đơn giản).

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Phát hiện bias | 15 | So tỉ trọng tầng giữa mẫu và tổng thể bằng số; chỉ ra cơ chế chọn mẫu |
| Hiệu chỉnh đúng | 20 | Post-stratification và IPW đúng, so với sự thật hoặc với nhau |
| Bất định | 15 | CI bootstrap phân tầng, giải thích vì sao phân tầng |
| Giới hạn (MNAR) | 25 | Mô phỏng hoặc lập luận rõ trường hợp hiệu chỉnh thất bại; có phân tích độ nhạy |
| Đề xuất thiết kế | 15 | Cách chọn mẫu lần sau, cỡ mẫu, theo dõi tỉ lệ phản hồi |
| Truyền đạt | 10 | Người không học thống kê đọc hiểu: con số chính, độ tin cậy, nên làm gì |

Từ 70 điểm trở lên: đủ để gửi Trưởng CSKH.
