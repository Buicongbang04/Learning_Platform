---
title: Chọn cách xử lý và công cụ làm sạch theo tình huống
level: basic
services: []
files: []
run: []
---

## Mục tiêu

Ra quyết định làm sạch theo **mục đích và cơ chế**, không theo thói quen: phân biệt MCAR, MAR, MNAR; chọn bỏ, điền
hay giữ cho từng chỉ số; nhìn dòng trùng và outlier như câu hỏi về nguồn dữ liệu; chọn công cụ (Excel, OpenRefine,
pandas, SQL, dbt tests, dplyr) theo người dùng, tần suất và yêu cầu tái lập.

## Đề bài

Bài này không có code. Làm 10 câu trắc nghiệm trong app (card **Trắc nghiệm** bên dưới). Mỗi câu là một tình huống
DA gặp thật:

- Câu 1-4: dữ liệu thiếu (cơ chế, bỏ / điền / giữ cho báo cáo doanh thu và kế toán).
- Câu 5-7: dòng trùng, fuzzy duplicate, outlier nghiệp vụ.
- Câu 8-10: chọn công cụ làm sạch và kiểm chất lượng; đối chiếu một thao tác dplyr với pandas.

Trước khi chọn, trả lời ba câu hỏi ở phần 2 và phần 6 của lý thuyết: con số này dùng cho chỉ số nào, vì sao dữ liệu
thiếu / trùng / lạ (cơ chế), và việc làm sạch này lặp lại bao lâu một lần, ai review.

## Tiêu chí đạt

- Trả lời đúng ít nhất 8/10 câu.
- Với mỗi câu sai, nêu được câu hỏi nào trong ba câu trên đã bị bỏ qua.
- Nhấn **Đánh dấu hoàn thành** sau khi đã đọc lời giải.

## Gợi ý

### Gợi ý 1

Phương án sai trong các câu đều "làm được" về kỹ thuật. Chúng sai vì bịa số (điền trung bình cho tiền, chia đều phần
không rõ), làm mất dữ liệu thật (bỏ cả hai dòng trùng, bỏ đơn thiếu vùng khỏi tổng), hoặc xử lý triệu chứng thay vì
hỏi nguồn.

### Gợi ý 2

Công cụ: một lần, có người duyệt bằng mắt → OpenRefine hoặc Excel; lặp lại, cần review → code trong git (pandas,
SQL); kiểm mỗi lần nạp trong warehouse → test chạy cùng pipeline (dbt tests, pandera, Great Expectations).
