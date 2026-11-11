# Lời giải: chính sách error budget và on-call

Bài Advanced không có một đáp án duy nhất. `POLICY.md`, `policy.yaml`, `oncall.yaml` ở đây là một lời giải qua test; rubric bên dưới
chấm nội dung.

## Hướng làm

- **Budget**: 0,1% nhân 28 ngày nhân 1440 phút là 40,32 phút.
- **Ngưỡng**: 50%, 25%, 0 là mức phổ biến. Quan trọng hơn con số là hành động đi kèm phải cụ thể (canary bắt buộc, sprint độ tin cậy)
  và luôn để đường cho vá bảo mật và rollback: đóng băng mà cấm cả rollback thì chính sách làm sự cố dài thêm.
- **Lịch trực**: một lời giải là An + Hà, Bình + Chi, Dũng + Hà, Giang + An. Đặt Hà vào hai tuần không liền nhau làm secondary (học qua
  hai ca), Giang vào tuần cuối, rồi lấp phần còn lại sao cho không ai trực hai tuần liền.
- **Leo thang** 0, 10, 25 phút: đủ thời gian để người trực ack từ điện thoại, không quá lâu để sự cố SEV1 nằm một mình.
- **Page budget** 10 mỗi tuần, 2 ban đêm theo khuyến nghị của Google SRE (tối đa khoảng 2 sự cố mỗi ca 12 giờ); vượt là tín hiệu alert
  có vấn đề, không phải người trực yếu.

## Rubric (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| SLI đo ở chỗ thấy được trải nghiệm khách, có phạm vi rõ (cái gì không thuộc SLO) | 1 |
| Ngưỡng và hành động cụ thể, kiểm được; luôn cho phép rollback và vá bảo mật | 2 |
| Ngoại lệ có người duyệt, giới hạn số lần, ghi lại lý do; xử lý riêng sự cố do bên ngoài | 1 |
| On-call bền vững: không trực liền, người mới được kèm, page budget kèm hệ quả khi vượt, có chế độ bù | 2 |
| Quy trình sự cố: SEV có tiêu chí khách quan, vai trò IC tách khỏi người sửa, liên lạc định kỳ | 2 |
| Vòng cải tiến: họp định kỳ, toil có trần, xem lại SLO và chính sách định kỳ, game day | 1 |
| Viết cho người đọc lúc 3 giờ sáng: ngắn, quyết định được ngay, không mơ hồ | 1 |

Trừ điểm: chính sách chỉ phạt (đóng băng) mà không có đường hồi phục; on-call một người suốt tuần không secondary; "dừng mọi release"
mà không định nghĩa release là gì.

## Câu hỏi kèm theo

- **Ký trước sự cố**: lúc đang mất tiền, mọi người thiên về quyết định cảm tính (đổ lỗi, đóng băng quá tay hay bỏ qua). Thống nhất từ
  trước biến quyết định thành tra bảng và bảo vệ cả team kỹ thuật lẫn product.
- **Cổng thanh toán sập**: budget vẫn tiêu (khách vẫn không đặt được hàng), nhưng đóng băng release của team không làm cổng thanh toán
  tốt hơn. Action item chuyển sang timeout, retry, fallback, hợp đồng SLA với đối tác.
- **Page budget vượt ba tuần liền**: dừng feature để dọn alert (xoá alert không cần hành động, chuyển thành ticket, gộp alert trùng),
  xem lại ngưỡng burn rate, và kiểm tra người trực có bị kiệt sức không.
