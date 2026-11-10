---
title: Kế hoạch tuần đầu tại khách
level: advanced
services: []
files:
  - path: starter/week-one-plan.md
    note: Khung kế hoạch, điền thành tài liệu gửi khách
run: []
---

## Mục tiêu

Viết kế hoạch tuần đầu cho một pilot tại khách sao cho cuối tuần có **kết quả đo được**, mọi thứ cần từ phía khách đã
được xin **trước** khi đến, và các rủi ro của môi trường đã biết có phương án chứ không phải lời hứa.

## Đề bài

Bạn là FDE được giao pilot `quillo` (trợ lý hỏi đáp tài liệu, xem phần 6 của lý thuyết) cho **Bệnh viện Đa khoa Sông
Hồng** (hư cấu). Thông tin sales và IT bệnh viện đã gửi trước:

- **Bài toán**: điều dưỡng trưởng các khoa mất nhiều thời gian tra quy trình nội bộ (khoảng 3 000 tệp PDF/DOCX, nhiều bản
  scan cũ). Mục tiêu pilot: trả lời câu hỏi về quy trình kèm trích dẫn đúng tài liệu gốc.
- **Người liên quan**: Phó giám đốc vận hành (sponsor, ký mở rộng), anh Tuấn, IT hạ tầng (chỉ rảnh chiều thứ Ba và thứ
  Năm), chị Lan, điều dưỡng trưởng khoa Nội (người dùng chính), phòng Pháp chế và An toàn thông tin (duyệt dữ liệu).
- **Máy**: một VM Ubuntu 20.04, đĩa 8 GB, 4 vCPU, 16 GB RAM, không GPU, Docker có sẵn nhưng không có plugin compose. Ra
  internet chỉ qua proxy của viện, proxy soi HTTPS. Bạn có tài khoản có `sudo` nhưng mọi thay đổi hệ thống phải làm
  trong **cửa sổ bảo trì tối thứ Năm 20:00–22:00**.
- **Dữ liệu**: tài liệu nội bộ không được rời bệnh viện; bạn chỉ làm việc trên máy của viện, tại chỗ.
- **Lời hứa của sales**: "chạy thử được trong tuần đầu".

Viết `starter/week-one-plan.md` thành tài liệu bạn sẽ gửi sponsor và anh Tuấn **thứ Sáu tuần trước khi đến**. Tối thiểu có:

1. **Mục tiêu tuần 1**: tối đa 3 mục, mỗi mục đo được (con số, tiêu chí đạt/không đạt).
2. **Cần khách chuẩn bị trước**: mỗi mục có người chịu trách nhiệm phía khách và hạn chót.
3. **Lịch thứ Hai → thứ Sáu**: mỗi ngày có việc chính, người cùng làm, đầu ra cuối ngày.
4. **Rủi ro và phương án**: ít nhất 4 rủi ro cụ thể của **môi trường và tổ chức này**, mỗi rủi ro có dấu hiệu nhận biết
   sớm và phương án nếu xảy ra.
5. **Báo cáo**: kênh, nhịp (cuối ngày, cuối tuần), ai nhận.
6. **Định nghĩa "xong tuần 1"** và việc bạn **không** làm trong tuần này (won't), kèm lý do.

Bài không có test; tự chấm theo rubric trong `SOLUTION.md` sau khi viết xong. Nếu được, nhờ một người khác đọc vai
sponsor và hỏi: "Thứ Sáu tôi sẽ thấy gì?"

## Tiêu chí đạt

- Mục tiêu đo được, khớp với lời hứa đã có của sales hoặc nói rõ phần nào của lời hứa cần điều chỉnh và vì sao.
- Mọi thứ phụ thuộc phía khách (quyền, dữ liệu, duyệt, lịch IT) được xin trước, có người và hạn.
- Lịch tôn trọng ràng buộc thật: lịch IT, cửa sổ bảo trì, dữ liệu không rời viện.
- Rủi ro cụ thể cho máy và tổ chức này, có phương án, không chung chung kiểu "có thể chậm tiến độ".
- Có cơ chế báo tin xấu sớm và danh sách việc không làm.

## Gợi ý

### Gợi ý 1

Đặt các việc phụ thuộc cửa sổ bảo trì và lịch của anh Tuấn lên lịch trước, rồi mới xếp phần còn lại quanh chúng.

### Gợi ý 2

So sánh từng dòng thông tin máy với những gì một bundle LLM + Postgres cần (đĩa, mạng, runtime). Chỗ nào lệch là một
rủi ro, và chỗ nào xin được trước khi đến thì đừng để tới thứ Hai.

### Gợi ý 3

"Chạy thử được" có thể nghĩa là "dịch vụ lên" hoặc "chị Lan hỏi được 20 câu thật và đúng 15". Chọn nghĩa nào là quyết
định của sponsor, không phải của bạn; kế hoạch phải đưa câu hỏi đó cho họ.
