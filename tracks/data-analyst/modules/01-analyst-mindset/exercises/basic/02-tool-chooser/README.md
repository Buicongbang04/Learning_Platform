---
title: Chọn công cụ theo tình huống - bản đồ công cụ của DA
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Dùng bản đồ công cụ ở phần 6 của lý thuyết để chọn công cụ theo **việc**, không theo thói quen: cỡ dữ liệu và
nơi dữ liệu nằm, ai dùng kết quả và bao lâu một lần, có cần tái lập không, công ty đang dùng hệ sinh thái nào.

## Đề bài

Bài này không có code. Làm 11 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Mỗi câu là một tình
huống thật của DA, chọn công cụ hợp nhất trong bốn phương án:

- Excel / Google Sheets, SQL trên warehouse, DuckDB trên file, Python notebook trong git, R.
- BI tự host (Metabase, Superset), BI thương mại (Power BI, Tableau, Looker).
- dbt / semantic layer, Streamlit, công cụ product analytics (Amplitude, Mixpanel).
- Một câu về cách dùng LLM an toàn khi phân tích.

Mọi phương án đều "làm được" theo nghĩa kỹ thuật; đáp án là công cụ **hợp nhất** khi tính cả người dùng, chi
phí, rủi ro và hệ sinh thái. Trước khi chọn, trả lời bốn câu hỏi ở cuối phần 6 lý thuyết cho tình huống đó.

## Tiêu chí đạt

- Trả lời đúng ít nhất 9/11 câu.
- Với mỗi câu sai, nêu được câu hỏi nào trong bốn câu chọn công cụ đã bị bỏ qua.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Đưa tính toán tới gần dữ liệu: dữ liệu đã nằm trong warehouse thì tổng hợp bằng SQL ở đó, chỉ kéo về phần đã
thu nhỏ. Dữ liệu là file vài trăm MB trên máy thì DuckDB chạy SQL thẳng trên file, không cần dựng database.

### Gợi ý 2

Câu hỏi lặp lại bởi nhiều người → BI; hai báo cáo ra hai con số khác nhau → vấn đề là **định nghĩa metric**,
không phải công cụ vẽ; người nhận cần tự sửa giả định → spreadsheet; cần logic tuỳ biến có tương tác →
Streamlit.
