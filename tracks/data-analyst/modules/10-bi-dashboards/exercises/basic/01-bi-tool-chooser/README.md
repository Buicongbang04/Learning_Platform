---
title: Chọn công cụ BI và cách định nghĩa metric theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Luyện câu hỏi mà phỏng vấn DA nào cũng có: "công ty như thế này thì chọn công cụ BI nào, vì sao?". Làm xong bạn
chọn được giữa Metabase, Superset, Streamlit, Power BI, Tableau, Looker, Looker Studio theo người dùng, dữ liệu,
hệ sinh thái và người duy trì; và biết đặt logic tính toán đúng chỗ trong từng công cụ (measure DAX, LOD của
Tableau, LookML, question trên model của Metabase).

## Đề bài

Bài này không có code. Làm 11 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới):

- 6 câu **tình huống → công cụ**: ngân hàng nhiều chi nhánh cần phân quyền theo dòng, startup không có ngân
  sách license, team kỹ thuật cần nhiều loại chart và RLS, app what-if gọi model, marketing dùng GA4, công ty có
  ba định nghĩa "active user".
- 4 câu **khái niệm của từng công cụ**: measure hay calculated column trong Power BI, LOD của Tableau, question
  query builder hay native SQL trên Metabase, Looker và Looker Studio khác nhau thế nào.
- 1 câu **ad-hoc hay dashboard**.

Trước khi chọn, trả lời bốn câu hỏi ở phần 7 của lý thuyết: **ai dùng** (biết SQL không, bao nhiêu người, có
cần RLS), **dữ liệu ở đâu**, **công ty đang ở hệ sinh thái nào**, **ai duy trì và ngân sách bao nhiêu**. Câu khái
niệm đọc lại phần 2 và 3 (measure tính sau khi lọc, LOD, LookML) và phần 4 (Metabase).

Nộp xong, đọc lời giải: mỗi câu giải thích vì sao đáp án hợp nhất và vì sao từng phương án còn lại không hợp.

## Tiêu chí đạt

- Trả lời đúng ít nhất 9/11 câu.
- Với mỗi câu chọn công cụ, nói được tiêu chí quyết định (RLS, ngân sách, người dùng không viết SQL, logic tuỳ
  biến, semantic layer, nguồn Google) và một đánh đổi của công cụ đã chọn.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Gạch chân trong tình huống các chữ quyết định: "mỗi người chỉ thấy phần của mình" (RLS), "không có ngân sách"
(mã nguồn mở), "không viết SQL" (query builder), "kéo thanh trượt, gọi model" (code), "ba định nghĩa" (semantic
layer), "GA4, Google Sheet, miễn phí" (Looker Studio). Hệ sinh thái công ty đang dùng thường thắng sở thích cá
nhân.

### Gợi ý 2

Câu khái niệm: tỉ lệ phải tính **sau** khi lọc (tổng tử / tổng mẫu), nên là measure; LOD `FIXED` tính ở mức chi
tiết riêng, bất kể view; drill-through của Metabase chỉ có trên question dựng bằng query builder; Looker có
LookML, Looker Studio thì không.
