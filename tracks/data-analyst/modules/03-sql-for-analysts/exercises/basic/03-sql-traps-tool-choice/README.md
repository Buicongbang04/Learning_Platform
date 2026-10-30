---
title: Đọc SQL đoán kết quả và chọn công cụ chạy SQL
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Đọc một câu SQL và đoán được kết quả **trước khi chạy**, nhất là ở những chỗ SQL hay "đúng cú pháp, sai ý
nghĩa": NULL, `LEFT JOIN` bị lọc thành `INNER JOIN`, đếm dòng thay vì đếm thực thể, khoảng thời gian. Và chọn
đúng nơi chạy SQL cho từng tình huống của DA: DuckDB trên file, warehouse của công ty, Postgres của ứng dụng,
spreadsheet hay pandas.

## Đề bài

Bài này không có code. Làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới):

- 6 câu "đoán kết quả": mỗi câu cho một bảng nhỏ và một câu SQL, chọn kết quả đúng. Tự chạy thử bằng DuckDB nếu
  muốn kiểm (`uv run python -c "import duckdb; print(duckdb.sql('...'))"`), nhưng hãy trả lời trước khi chạy.
- 4 câu "chọn công cụ": mỗi câu là một tình huống thật, chọn nơi chạy SQL hợp nhất theo bảng so sánh ở phần 7
  của lý thuyết.

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu sai, viết lại được một câu: quy tắc SQL nào (hoặc câu hỏi chọn công cụ nào) đã bị bỏ qua.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

NULL không bằng, không khác, không lớn hơn bất kỳ thứ gì, kể cả NULL: mọi so sánh với NULL cho `NULL`, và `WHERE`
chỉ giữ dòng `TRUE`. Hàm tổng hợp (`COUNT(col)`, `SUM`, `AVG`) bỏ qua NULL; `COUNT(*)` thì không.

### Gợi ý 2

Đưa tính toán tới gần dữ liệu: dữ liệu đã trong warehouse thì tổng hợp ở đó; file vài trăm MB trên máy thì
DuckDB đọc thẳng file; không chạy truy vấn phân tích nặng lên database đang phục vụ ứng dụng.
