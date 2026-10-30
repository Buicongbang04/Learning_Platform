---
title: Spreadsheet hay SQL/Python - chọn công cụ và chọn hàm theo tình huống
level: intermediate
services: []
files: []
run: []
---

## Mục tiêu

Quyết định khi nào một việc nên làm trong spreadsheet, khi nào phải chuyển sang SQL/Python, và khi ở
lại spreadsheet thì chọn công cụ (Excel, Google Sheets, LibreOffice) và hàm nào để kết quả đúng và
người nhận dùng được.

## Đề bài

Bài này không có code. Làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Mỗi câu là
một tình huống của DA, dùng số liệu thật đã gặp trong module (Online Retail II, Bike Sharing) khi có:

- Chọn giữa spreadsheet, SQL (DuckDB, warehouse) và Python theo cỡ dữ liệu, tần suất, người dùng, nhu
  cầu giải trình.
- Chọn giữa Excel, Google Sheets, LibreOffice theo hệ sinh thái và tính năng (XLOOKUP, cộng tác, giới hạn ô).
- Chọn hàm/tính năng trong spreadsheet cho đúng việc (tra cứu, tổng hợp, pivot, kiểm tra).

Trước khi chọn, trả lời bốn câu hỏi của sơ đồ "Khi nào bỏ spreadsheet" ở phần 7 lý thuyết: dữ liệu
bao lớn, lặp lại bao lâu một lần, có cần giải trình/tái lập, người nhận có cần tự chỉnh không.

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu sai, nêu được tiêu chí nào (cỡ dữ liệu, tần suất, giải trình, người dùng, hệ sinh thái)
  đã bị bỏ qua.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Giới hạn cứng: Excel và LibreOffice 1 048 576 dòng mỗi sheet; Google Sheets 10 triệu ô mỗi file;
Online Retail II hai năm có 1 067 371 dòng. Giới hạn mềm đến sớm hơn nhiều: workbook vài trăm nghìn dòng
có SUMIFS tính lại rất chậm.

### Gợi ý 2

Spreadsheet thắng khi người nhận cần **tự sửa giả định** hoặc **tự lọc**, dữ liệu nhỏ, việc làm một
lần. Code thắng khi việc **lặp lại**, dữ liệu **lớn**, hoặc con số phải **giải trình** sau nhiều tháng.
Mẫu kết hợp hay gặp nhất: SQL/Python tính, Excel là đầu ra.
