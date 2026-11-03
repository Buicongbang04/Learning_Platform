# Hướng làm và rubric: governance cho ba đội

`DESIGN.md` cạnh tệp này là một lời giải tham khảo, không phải đáp án duy nhất.

## Hướng làm

1. **Tầng theo hậu quả, không theo kích thước.** `credit-risk` (6 người) ở tầng cao vì thanh tra và tái lập 5 năm; `recsys` (12 người) trung bình; `research` thấp. Bảng ở phần 1 phải trả lời "vì sao" bằng một câu truy được về đề.
2. **Ma trận kiểm soát là sản phẩm chính.** Mỗi dòng nói **ai thực thi, bằng cơ chế nào**. Ví dụ "hai người duyệt" ở tầng cao chỉ có nghĩa nếu CI từ chối khi hai approver trùng nhau hay trùng người train; "quy ước trong wiki" không phải kiểm soát.
3. **Tách quyền trả lời sự cố có thật.** Việc `recsys` đổi alias nhầm của đội khác dẫn tới quyền theo prefix và alias production chỉ ghi qua CI. Break-glass có hạn giờ và để lại dòng audit log, nếu không thì sau cùng mọi người dùng nó.
4. **Audit log trả lời câu hỏi của kiểm toán.** Ai, lúc nào, từ version nào sang version nào, vì sao, dựa trên metric nào (liên kết tới run). Hash chain cộng anchor ngoài hệ thống; xem bài hash chain. Retention theo tầng; tầng cao 5 năm kéo theo giữ cả dữ liệu huấn luyện (DVC) và artifact, không chỉ log.
5. **Cái giá nói thẳng.** Duyệt hai người thêm 1 đến 2 ngày chờ; hai kỹ sư nền tảng là điểm nghẽn; lưu 5 năm tốn tiền; quyền theo prefix cần proxy hay IdP vì MLflow OSS không tự thực thi (module 04 và 17).
6. **Rollback không bị duyệt hai người.** Lúc sự cố, đường lùi nhanh quan trọng hơn thủ tục; ghi vào audit log sau.

## Rubric (tối đa 100 điểm)

| Mục | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Phân tầng và lý do | 15 | ba đội có tầng và lý do truy được về đề; hậu quả khi sai có cụ thể |
| Ma trận kiểm soát | 25 | mỗi dòng có cơ chế thực thi, tầng cao thật sự chặt hơn, tầng thấp không bị gánh nặng vô nghĩa |
| Tách quyền | 15 | người train khác người duyệt; ranh giới giữa đội; break-glass có kiểm soát |
| Audit và lưu giữ | 20 | trả lời được câu hỏi kiểm toán; chống sửa log; retention có con số và gắn với dữ liệu, không chỉ log |
| Luồng duyệt | 10 | sơ đồ khớp ma trận; có đường rollback |
| Chi phí, rủi ro, điều kiện đổi hướng | 15 | nói thẳng giá phải trả; có điều kiện cụ thể để đổi (số model, số người, dịch vụ quản lý) |

Trừ điểm: kiểm soát chỉ là "cần cẩn thận hơn" không có chủ hay cơ chế (-5); ba đội dùng cùng một mức kiểm soát (-15); audit log do chính người được audit ghi được mà không nhắc (-10); bỏ qua yêu cầu 5 năm (-10). Mức đạt: 70/100.
