---
title: Chọn chart và công cụ theo tình huống của stakeholder
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Luyện phản xạ đầu tiên của một DA khi nhận yêu cầu: đọc câu hỏi của stakeholder, xếp nó vào một
trong sáu loại câu hỏi (so sánh, xu hướng, phân phối, thành phần, quan hệ, luồng) rồi chọn chart, và
chọn công cụ vẽ theo người xem, tần suất xem và nhu cầu tái lập.

## Đề bài

Bài này không có code. Làm 12 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới):

- 8 câu **tình huống → loại chart**, phủ đủ 8 loại chart của roadmap: bar, line, scatter, funnel,
  histogram, stacked, heatmap, pie. Các tình huống lấy từ công việc DA thường gặp (vận hành giao
  hàng, kênh bán, chăm sóc khách hàng, marketing), không phải từ bộ dữ liệu của module.
- 4 câu **tình huống → công cụ**: matplotlib/seaborn, plotly, Excel/Google Sheets, BI (Power BI,
  Tableau, Metabase...).

Với mỗi câu, trước khi chọn hãy tự viết câu hỏi của chart thành một câu có động từ so sánh, rồi đi
theo cây quyết định ở phần 2 của lý thuyết module. Với câu chọn công cụ, dùng bốn câu hỏi ở phần 7:
ai xem và xem bao nhiêu lần, người xem có cần tự cắt lát không, số có phải khớp số "chính thức"
không, có cần tái lập không.

Nộp xong, đọc lời giải: mỗi câu giải thích vì sao đáp án đúng và vì sao từng phương án sai không
hợp.

## Tiêu chí đạt

- Trả lời đúng ít nhất 10/12 câu.
- Với mỗi câu sai, nói lại được loại câu hỏi của tình huống và chart (hoặc công cụ) mà cây quyết
  định dẫn tới.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Hỏi theo thứ tự: có trục thời gian không? Có so giữa các nhóm không? Là phân phối của một biến số,
thành phần của một tổng, quan hệ giữa hai biến, hay các bước tuần tự? Chart "đẹp" nhất hiếm khi là
đáp án; chart mà người xem đọc **chính xác** nhất mới là đáp án (vị trí và độ dài trước, góc và màu
sau).

### Gợi ý 2

Với công cụ: xem một lần trong slide thì ảnh tĩnh sinh từ code (hoặc Excel nếu người nhận cần sửa
số); nhiều người xem hằng tuần và tự lọc thì BI; cần tương tác nhưng chưa có BI thì plotly xuất HTML.
Hệ sinh thái công ty đang dùng (Microsoft 365, Google Cloud) thường quyết định chọn BI nào.
