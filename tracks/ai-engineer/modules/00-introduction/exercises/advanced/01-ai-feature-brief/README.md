---
title: Bản đánh giá khả thi tính năng hỏi đáp pháp luật, có số đo
level: advanced
services: []
files:
  - path: starter/brief.ipynb
    note: 2 hàm TODO + các cell đo trên Zalo Legal
  - path: starter/MEMO.md
    note: Bản đánh giá khả thi, 8 mục
  - path: tests/test_brief.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - uv run jupyter lab tracks/ai-engineer/modules/00-introduction/exercises/advanced/01-ai-feature-brief/starter/brief.ipynb
  - uv run pytest tracks/ai-engineer/modules/00-introduction/exercises/advanced/01-ai-feature-brief -q
---

## Mục tiêu

Làm việc đầu tiên AI Engineer làm với mọi tính năng mới: trước khi viết code, trả lời bằng số "làm được không, tốn bao
nhiêu, chậm bao nhiêu, dùng model nào, rủi ro gì". Bài ghép mọi phép tính của module (token, chi phí, độ trễ, model card)
trên dữ liệu thật thành một bản memo mà product manager đọc được và kỹ sư kiểm lại được. Đây cũng là bước 0 của capstone
Trợ lý pháp luật tiếng Việt.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Làm xong Basic 01, 02 và Intermediate 01, 02 trước: notebook nạp `cost.py`, `model_card.py` từ `starter/` của hai bài
Basic, và cần hệ số độ trễ bạn khớp ở Intermediate 02. Các cell `explore` chạy khoảng 30 giây (đếm token 300 câu hỏi và
khoảng 1 500 điều luật).

Tình huống: thêm tính năng **hỏi đáp pháp luật tiếng Việt có trích dẫn điều luật** cho khoảng 2 000 người dùng hoạt động,
mỗi người khoảng 5 câu mỗi ngày. Kiến trúc dự kiến là RAG (mục 3 lý thuyết): system prompt, câu hỏi, 5 điều luật tìm
được, câu trả lời khoảng 300 token.

1. Trong `starter/brief.ipynb`, viết hai hàm chấm điểm: `request_tokens(question, articles, encode, system_tokens=150,
   max_article_tokens=None, k=5)` (số token prompt của một request, có cắt từng điều) và `overflow_rate(tokens,
   max_new_tokens, context_window)` (tỉ lệ request tràn context). Đặc tả chi tiết trong notebook.
2. Chạy các cell `explore`: phân phối token mỗi request trên 300 câu hỏi ghim của Zalo Legal (như module 13) với ba mức
   cắt, chi phí tháng cho các phương án API và tự host, độ trễ dự đoán, bảng giấy phép model mở. Sửa giả định (giá GPU,
   hệ số độ trễ của bạn, mức cắt) và thêm phương án nếu muốn; ghi lý do.
3. Viết `starter/MEMO.md` đủ 8 mục có sẵn (Bài toán, Khối lượng và token, Phương án và chi phí, Độ trễ, Model và giấy
   phép, Vai trò, Rủi ro và đo lường, Khuyến nghị). Mọi con số lấy từ notebook hoặc các bài trước; giá API ghi ngày kiểm;
   giả định ghi rõ là giả định. Khuyến nghị phải nói rõ **điều kiện nào thì nó sai**.
4. Làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `request_tokens` và `overflow_rate` đúng trên fixture của test (cắt từng điều, chỉ lấy `k` điều đầu, ngưỡng "vừa khít"
  không tính là tràn).
- `MEMO.md` không còn TODO, đủ 8 mục, ít nhất 600 từ, ít nhất một bảng, có số đo và chi phí bằng USD.
- Nội dung chấm theo rubric trong `SOLUTION.md`: số liệu khớp notebook, phát hiện được vấn đề tràn context và vấn đề
  giấy phép, so sánh phương án có giả định rõ, khuyến nghị có điều kiện.

## Gợi ý

### Gợi ý 1

Trước khi viết memo, tự hỏi ba câu mà cell `explore` trả lời: request "điển hình" và request "xấu" (p95) dài bao nhiêu
token; với context mặc định 4 096 của Ollama, bao nhiêu phần trăm request bị cắt mà không ai biết; và phần nào của chi
phí là input, phần nào là output.

### Gợi ý 2

Đừng chỉ so giá: model rẻ nhất chỉ là phương án nếu nó **đạt chất lượng**, mà bạn chưa đo chất lượng. Memo tốt đề xuất
cách đo (bộ eval nào, ngưỡng nào) trước khi chọn model. Đọc lại bảng giấy phép: model bạn định dùng cho prototype có
được dùng cho sản phẩm thương mại không? So tự host với API bằng chi phí **cả tháng** (GPU thuê 24/7 vẫn tốn tiền lúc
không ai hỏi) và bằng độ trễ khi GPU bận.
