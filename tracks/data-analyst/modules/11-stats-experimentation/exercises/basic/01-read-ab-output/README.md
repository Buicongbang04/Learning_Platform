---
title: Đọc output A/B và chọn kiểm định, chọn công cụ theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Luyện phản xạ của DA khi nhận một bảng kết quả thí nghiệm hoặc một câu hỏi "có khác nhau không": chọn
kiểm định theo **loại metric và cách lấy mẫu**, đọc p-value và khoảng tin cậy đúng nghĩa, kiểm độ tin cậy
(SRM, guardrail, peeking, novelty) **trước** khi đọc hiệu ứng, và chọn công cụ theo tần suất chạy thí
nghiệm của công ty.

## Đề bài

Bài này không có code. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới):

- 3 câu **tình huống → kiểm định**: metric tỉ lệ, metric trung bình lệch phải, so trước/sau trên cùng đơn vị.
- 7 câu **đọc output**: p-value, khoảng tin cậy so với MDE, SRM, guardrail, peeking, novelty effect, lift
  tương đối và tuyệt đối, phân khúc sau thí nghiệm.
- 2 câu **tình huống → công cụ**: notebook Python, spreadsheet/calculator, nền tảng experimentation.

Các con số trong câu hỏi là **ví dụ giả định**, đặt cho tròn để bạn tập trung vào cách đọc; các bài notebook
của module làm lại từng bước trên dữ liệu thật (Online Retail II, `marketing-ab`, Bike Sharing).

Với mỗi câu, trước khi chọn hãy tự trả lời theo thứ tự ở phần 4 của lý thuyết: dữ liệu có đáng tin không
(SRM, guardrail, thời lượng) → hiệu ứng lớn bao nhiêu, khoảng tin cậy ra sao → so với MDE thì quyết định gì.

## Tiêu chí đạt

- Trả lời đúng ít nhất 9/12 câu.
- Với mỗi câu sai, nói lại được bước nào trong quy trình đọc kết quả dẫn tới đáp án đúng.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Chọn kiểm định theo ba câu hỏi: metric là tỉ lệ (0/1) hay số liên tục? Hai nhóm độc lập hay cùng một đơn vị
đo hai lần? Câu hỏi business là về **trung bình** (doanh thu tổng = trung bình × số người) hay về "phần lớn
khách"? Kiểm định trả lời câu hỏi khác với câu stakeholder hỏi là sai dù p-value đẹp.

### Gợi ý 2

p-value không phải xác suất "B tốt hơn A", và "không có ý nghĩa" không có nghĩa "không có hiệu ứng". Đọc
khoảng tin cậy: nó chứa 0 không? Nó nằm trên hay dưới MDE? Trước mọi thứ đó, tỉ lệ chia nhóm có đúng thiết kế
không: SRM thì không có kết luận nào đáng tin.
