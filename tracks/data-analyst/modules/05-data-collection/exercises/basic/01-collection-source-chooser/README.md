---
title: Chọn nguồn và cách thu thập - database, file, API hay scraping
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Chọn cách lấy dữ liệu theo **câu hỏi, nguồn và rủi ro**, không theo công cụ quen tay: khi nào truy vấn database,
khi nào xin file export, khi nào gọi API, khi nào scraping (và khi nào **không** được scraping), giữ API key và dữ
liệu cá nhân an toàn ra sao.

## Đề bài

Bài này không có code. Làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Mỗi câu là một tình huống
thật của DA khi cần dữ liệu:

- Chọn nguồn: read replica / warehouse, file export, API chính thức, scraping, nhờ Data Engineer dựng pipeline.
- Rủi ro khi đọc file và gọi API: control total, phân trang, rate limit, lỗi trả về trong HTTP 200.
- Đạo đức và pháp lý: `robots.txt`, điều khoản sử dụng, dữ liệu cá nhân (Luật Bảo vệ dữ liệu cá nhân 2025), API key.

Mọi phương án đều "lấy được dữ liệu" theo nghĩa kỹ thuật; đáp án là cách **hợp nhất** khi tính cả độ tin cậy của
số, chi phí lặp lại, rủi ro cho hệ thống nguồn và rủi ro pháp lý. Trước khi chọn, trả lời bốn câu hỏi ở phần 1 lý
thuyết cho tình huống đó.

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu sai, nêu được câu hỏi nào trong bốn câu chọn nguồn đã bị bỏ qua.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Thứ tự ưu tiên khi có nhiều cách: nguồn đã được định nghĩa và kiểm (warehouse, bảng của team data) → API chính thức →
file export có control total → scraping. Đi xuống một bậc là nhận thêm việc kiểm và thêm rủi ro.

### Gợi ý 2

Việc làm một lần khác việc làm hằng ngày. Một lần: đường ngắn nhất mà vẫn kiểm được số. Hằng ngày: ai bảo trì khi nguồn
đổi, chạy lại có trùng dữ liệu không, có log không. Câu hỏi về pháp lý không có đáp án "kỹ thuật": hỏi pháp chế.
