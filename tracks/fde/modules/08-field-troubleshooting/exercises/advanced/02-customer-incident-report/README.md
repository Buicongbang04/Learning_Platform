---
title: "Báo cáo sự cố gửi khách"
level: advanced
services: []
files:
  - path: case-notes.md
    note: Ghi chép thô của bạn trong buổi xử lý sự cố
  - path: starter/incident-report.md
    note: Khung báo cáo; bạn viết vào đây
run: []
---

## Mục tiêu

Sự cố đã hết, khách đã dùng lại được. Hai ngày sau, trưởng IT công ty luật cần một báo cáo để gửi ban giám đốc và giữ
trong hồ sơ nhà cung cấp. Báo cáo này quyết định khách còn tin bạn hay không: nó phải nói thẳng chuyện gì đã xảy ra, kể
cả khi nguyên nhân nằm ở phía khách, mà không đổ lỗi cho ai; nói rõ ảnh hưởng; và cam kết những việc phòng ngừa mà người
cam kết thực sự làm được.

## Đề bài

Đọc `case-notes.md` (ghi chép thô của bạn trong buổi sáng thứ Hai, có cả thứ không được đưa ra ngoài) rồi viết
`starter/incident-report.md` gửi trưởng IT công ty luật. Người đọc cuối là ban giám đốc: không kỹ thuật, đọc phần tóm tắt
và ảnh hưởng; IT đọc phần còn lại. Độ dài ~500–800 từ. Không có test tự động; tự chấm theo rubric dưới đây, bài mẫu và
rubric chi tiết ở `solutions/`.

## Tiêu chí đạt

Rubric 20 điểm, đạt khi ≥ 15 và **không** có lỗi loại trừ:

| Tiêu chí | Điểm |
| --- | --- |
| Tóm tắt 3–5 câu cho người không kỹ thuật: chuyện gì, bao lâu, ai bị ảnh hưởng, đã ổn chưa, dữ liệu có mất không | 3 |
| Ảnh hưởng định lượng từ dữ liệu (số người, khoảng thời gian, chức năng nào hỏng và chức năng nào vẫn chạy) | 3 |
| Timeline theo giờ của khách, từ lúc bắt đầu ảnh hưởng tới lúc xác nhận khắc phục, có mốc phát hiện và mốc quyết định | 3 |
| Nguyên nhân gốc và yếu tố góp phần nói thẳng, đúng với bằng chứng, giọng không đổ lỗi (mô tả hệ thống và quy trình, không gọi tên người) | 4 |
| Việc phòng ngừa: mỗi việc có bên chịu trách nhiệm (khách / nhà cung cấp) và hạn, chỉ cam kết thứ bên đó kiểm soát | 4 |
| Tách rõ điều đã chứng minh và điều chưa biết; không suy đoán thành kết luận | 2 |
| Rõ ràng, chuyên nghiệp: không thuật ngữ không giải thích ở phần tóm tắt, không xin lỗi chung chung thay cho nội dung | 1 |

Lỗi loại trừ: có secret hay mảnh secret (kể cả "token bắt đầu bằng …"); có tên, email của nhân viên khách; nêu tên cá
nhân như nguyên nhân; hứa thay đội sản phẩm một tính năng hay mốc phát hành; khẳng định điều ghi chép nói là chưa kiểm
như sự thật.

## Gợi ý

### Gợi ý 1

Viết phần tóm tắt cuối cùng, sau khi đã viết timeline và nguyên nhân: lúc đó bạn mới biết chắc điều gì đáng nói trong
bốn câu.

### Gợi ý 2

Với mỗi câu trong phần nguyên nhân, chỉ được dòng nào trong ghi chép là bằng chứng của nó. Câu nào không chỉ được thì
chuyển xuống phần "chưa biết", hoặc bỏ.

### Gợi ý 3

"Không đổ lỗi" không có nghĩa là né nguyên nhân: viết về điều kiện (nguồn giờ cũ đã tắt, máy chuyển sang host khác, không
có cảnh báo) thay vì về người đã làm thao tác.
