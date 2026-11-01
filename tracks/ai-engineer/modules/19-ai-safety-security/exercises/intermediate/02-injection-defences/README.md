---
title: Prompt injection gián tiếp - bộ tấn công ghim, sáu cách đóng gói prompt, ASR và task success
level: intermediate
services: []
files:
  - path: starter/defences.ipynb
    note: 6 hàm TODO
  - path: tests/test_defences.py
    note: Không sửa
run:
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/19-ai-safety-security/exercises/intermediate/02-injection-defences/starter/defences.ipynb
  - uv run pytest tracks/ai-engineer/modules/19-ai-safety-security/exercises/intermediate/02-injection-defences -q
---

## Mục tiêu

Tấn công một trợ lý văn phòng bằng prompt injection **gián tiếp** (chỉ thị nằm trong tài liệu nó đọc) và đo cả hai phía
của mọi phòng thủ: tỉ lệ tấn công thành công và tỉ lệ trả lời đúng. Bạn thấy tận mắt phòng thủ bằng prompt giảm được bao
nhiêu, mất gì, và phòng thủ bằng code ở output bảo đảm được gì. Bài đi sâu hơn bài computer use của [module 16](../../../../16-ai-agents/README.md): ở đó có một kiểu
injection (báo giá giả) thành công trên vài lượt; ở đây một bộ tấn công ghim nhiều kiểu, nhiều mục tiêu, đủ lượt để so
các phòng thủ có khoảng tin cậy.

## Đề bài

**Phần cứng:** CPU · ~90 phút

Làm bài Basic 02 trước: cell lọc link ở cuối notebook dùng `guard.sanitize_links` của bạn.

Thời gian trên là thời gian làm bài. Ma trận là 912 lượt gọi `qwen2.5:3b` với câu trả lời ngắn: bản tham chiếu mất
khoảng 45 phút trên PC của track (trung vị 1.1 giây mỗi lượt, GPU và Ollama đang dùng chung với việc khác); máy riêng
không bị chia sẻ sẽ nhanh hơn (chưa đo). Muốn có kết quả sớm, chạy trước hai defence `none` và `spotlight`, phần còn lại
chạy sau; cell chạy tiếp được chỗ dở.

Trong `starter/defences.ipynb`, cell chấm điểm:

1. `clean_markers`, `datamark`, `build_messages(defence, document, question)` cho 6 cách đóng gói `none`, `warn`,
   `spotlight`, `datamark`, `sandwich`, `tool-role` theo bảng trong notebook.
2. `score_reply(reply, doc, goal)`: trả lời đúng không, tấn công thành công không.
3. `wilson_ci(k, n)` và `summarise(records, by=...)`: bảng clean task, attack task, ASR có khoảng Wilson, số lượt lỗi.

Rồi chạy các cell `explore`: ma trận (8 tài liệu x (1 sạch + 6 kiểu tấn công x 3 mục tiêu) x 6 cách đóng gói), bảng theo
defence, theo kiểu tấn công, theo mục tiêu; bộ lọc output allowlist link chồng lên mọi defence; đọc tận mắt các lượt tấn
công thành công dưới defence tốt nhất. Trả lời các câu hỏi cuối notebook, rồi làm phần trắc nghiệm của bài trong app.
Câu trả lời của LLM có thể lệch vài lượt giữa các máy và phiên bản Ollama; câu trắc nghiệm dựa trên những xu hướng lớn.

## Tiêu chí đạt

- `build_messages` đúng từng chữ theo bảng cho cả 6 cách, `spotlight` xoá dấu phân cách do tài liệu tự chèn (kể cả chữ
  thường và dạng NFD), `datamark` thay mọi chuỗi khoảng trắng, `tool-role` đặt tài liệu trong message vai `tool`,
  defence lạ ném `ValueError`.
- `score_reply` không phân biệt hoa thường và không tính tấn công trên tài liệu sạch.
- `wilson_ci` đúng các giá trị chuẩn; `summarise` loại lượt lỗi khỏi mẫu số, tính ASR chỉ trên lượt bị tấn công, giữ
  thứ tự nhóm, cho `nan` khi mẫu số 0.
- Cell `explore` chạy hết ma trận và in các bảng.

## Gợi ý

### Gợi ý 1

Viết `build_messages` bằng một chuỗi `if defence == ...`, dựng sẵn hai chuỗi dùng chung (user dạng "Tài liệu ... Câu
hỏi ..." và system có cảnh báo) rồi ghép. So từng chữ với bảng trong notebook: test so bằng `==`. Với `clean_markers`,
nghĩ xem một dấu phân cách có thể "trông giống" mà khác byte theo những cách nào, và xử lý trước khi xoá.

### Gợi ý 2

Trong `summarise`, gom bản ghi vào `dict` theo `tuple(r[k] for k in by)`; `dict` của Python giữ thứ tự chèn. Tách lượt
lỗi trước, rồi chia phần còn lại thành sạch và bị tấn công. Đọc bảng theo mục tiêu và theo kiểu tấn công trước khi
kết luận về một defence, và luôn đặt ASR cạnh task success.
