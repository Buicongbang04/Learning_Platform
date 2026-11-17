---
title: "Thiết kế xử lý dữ liệu cá nhân trước khi index"
level: advanced
services: []
files:
  - path: starter/pii-design.md
    note: Khung tài liệu thiết kế; bạn viết
run: []
---

## Mục tiêu

Công ty luật muốn mở quillo cho cả phòng hành chính và thực tập sinh. Hợp đồng, biên bản, hồ sơ tranh tụng chứa số
CCCD, số điện thoại, tài khoản ngân hàng, địa chỉ, có khi cả thông tin sức khoẻ hay tiền án của đương sự. Phòng pháp chế
hỏi: "dữ liệu cá nhân có bị đưa vào hệ thống AI nguyên vẹn không, ai thấy được, xoá được không?". Bạn viết tài liệu thiết
kế cho bước xử lý dữ liệu cá nhân **trước khi** tài liệu được index, đủ cụ thể để một kỹ sư dựng được và phòng pháp chế
duyệt được.

## Đề bài

Viết `starter/pii-design.md` (khung 9 mục có sẵn, ~1 500–2 500 từ, có ít nhất một sơ đồ luồng dữ liệu bằng mermaid hoặc
ASCII). Bối cảnh cố định:

- Quillo 1.0.0 như ở các bài trước: connector file share → inbox → worker (trích văn bản, chunk, embedding) → Postgres;
  `/api/ask` đưa đoạn trích vào prompt của LLM local; ACL theo thư mục; bản gốc giữ ở `inbox/done/`; log JSON có tên tệp.
- Mọi thứ chạy trong mạng của khách, không có dịch vụ ngoài; máy chủ chỉ có CPU.
- Người dùng: luật sư (cần thấy đầy đủ hồ sơ mình phụ trách), hành chính và thực tập sinh (chỉ cần nội dung pháp lý, không
  cần danh tính đương sự).
- Khách áp dụng pháp luật Việt Nam về bảo vệ dữ liệu cá nhân (Luật Bảo vệ dữ liệu cá nhân 2025, có hiệu lực từ
  01/01/2026, và các văn bản hướng dẫn).

Không có test tự động; tự chấm theo rubric, bài mẫu ở `solutions/`.

## Tiêu chí đạt

Rubric 20 điểm, đạt khi ≥ 15 và không có lỗi loại trừ:

| Tiêu chí | Điểm |
| --- | --- |
| Luồng dữ liệu đầy đủ: chỉ ra **mọi** nơi dữ liệu cá nhân nằm lại (bản gốc, chunk, embedding, prompt, log, backup, bản export) và thiết kế xử lý từng nơi | 4 |
| Phát hiện phù hợp tiếng Việt và từng loại thực thể (mẫu có cấu trúc + kiểm tra hợp lệ; tên/địa chỉ bằng NER hoặc từ điển; ước lượng độ chính xác) | 4 |
| Biến đổi theo nhóm người dùng: hai "góc nhìn" (đầy đủ vs đã che) gắn với ACL hiện có, bí danh hoá nhất quán có khoá do khách giữ, lý do chọn | 4 |
| Đo chất lượng: bộ kiểm tra có nhãn, recall/precision của phát hiện, ảnh hưởng tới truy hồi và trả lời, ngưỡng chấp nhận | 3 |
| Vận hành và pháp lý: xoá theo yêu cầu, lưu giữ, quyền truy cập khoá, sự cố, ai quyết định gì | 3 |
| Trung thực về giới hạn: rủi ro còn lại, điểm cần khách quyết định | 2 |

Lỗi loại trừ: gửi tài liệu ra dịch vụ ngoài (API cloud) để phát hiện PII; khẳng định che bằng regex là đủ cho tên người
và địa chỉ; bỏ quên bản gốc trong `inbox/done/` hoặc log; bí danh hoá bằng hash không khoá (dò ngược được từ số CCCD).

## Gợi ý

### Gợi ý 1

Một số CCCD bị che trong chunk nhưng vẫn nằm trong bản gốc, trong log tên tệp, trong embedding của đoạn chưa che, và
trong bản sao lưu tuần trước. Vẽ luồng trước, chọn kỹ thuật sau.

### Gợi ý 2

"Che" có nhiều mức: xoá hẳn, thay bằng nhãn loại (`[CCCD]`), thay bằng bí danh nhất quán (`[NGƯỜI_7]`) để câu hỏi "ai ký
cả hai hợp đồng này" vẫn trả lời được. Mỗi mức hợp với ai?

### Gợi ý 3

Embedding của một đoạn có tên người không "che" được sau khi đã tính. Quyết định góc nhìn nào được index trước khi tính.
