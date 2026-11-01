---
title: Trợ lý CSKH có guardrail - PII, injection, moderation, rate limit, đo chặn đúng và chặn oan (portfolio)
level: advanced
services: []
files:
  - path: starter/assistant.ipynb
    note: 3 hàm có test, ghép thành phần thật
  - path: starter/REPORT.md
    note: Báo cáo vận hành
  - path: tests/test_assistant.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py prompt-injections
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/19-ai-safety-security/exercises/advanced/02-guarded-assistant/starter/assistant.ipynb
  - uv run pytest tracks/ai-engineer/modules/19-ai-safety-security/exercises/advanced/02-guarded-assistant -q
---

## Mục tiêu

Ghép mọi mảnh của module thành một trợ lý chăm sóc khách hàng ngân hàng mà bạn dám cho khách thật dùng thử: định danh
người dùng không lộ danh tính, rate limit và cấm có leo thang, chặn injection, giả danh hoá PII trước **mọi** lời gọi
model, moderation hai đầu với nhánh hỗ trợ cho tin nhắn tự hại, lọc link ở output, khôi phục PII cho người dùng. Rồi đo
nó như một kỹ sư vận hành: mỗi loại tin nhắn được xử lý thế nào, bao nhiêu giá trị PII lọt tới model, chặn oan bao
nhiêu khách, mỗi lớp tốn bao nhiêu mili giây, và hệ thống hỏng ở đâu.

## Đề bài

**Phần cứng:** CPU · ~300 phút

Thời gian trên là thời gian làm bài. Model là `qwen2.5:3b` cho cả trả lời lẫn moderation; 48 tin nhắn cần 80 tới 100
lượt gọi tuỳ số tin bị chặn sớm (bản tham chiếu: 83 lượt, khoảng 2 phút trên PC của track). Không gửi dữ liệu (dù là dữ liệu sinh) cho API bên ngoài trong bài này.

1. Trong `starter/assistant.ipynb`, cell có test: `handle(c, user_id, text)` theo đúng thứ tự lớp mô tả trong notebook,
   `traffic_report`, `stage_latency`.
2. Ghép thành phần thật trong các cell `explore`:
   - code của bạn ở ba bài Basic: `pii.py` (`Pseudonymizer`), `guard.py` (`find_denied`, `sanitize_links`), `abuse.py`
     (`user_key`, `TokenBucket`, `AbuseTracker`), nạp từ `starter/` của từng bài;
   - `injection_check`: danh sách chặn sau chuẩn hoá cộng classifier TF-IDF char của bài Intermediate 01;
   - `moderate`: `qwen2.5:3b` với chính sách của bạn (nhóm vi phạm, định nghĩa từng nhóm, phàn nàn gay gắt không phải vi
     phạm) qua JSON schema; JSON hỏng là một cờ riêng, không phải "sạch";
   - system prompt cho trợ lý: chỉ trả lời về ngân hàng, giữ nguyên token PII, không đoán giá trị thật;
   - câu trả lời hỗ trợ cho nhánh tự hại: thông cảm, khuyến khích liên hệ người thân và dịch vụ khẩn cấp, chuyển tới nhân
     viên (kiểm lại các số đường dây nóng hiện hành trước khi ghi vào câu trả lời).
3. Chạy 40 tin nhắn có nhãn `TRAFFIC` (bình thường, có PII, injection, xúc phạm, tự hại, ngoài phạm vi) và 8 tin liên
   tiếp của một người dùng để thử rate limit. In `traffic_report`, `stage_latency`, đếm giá trị PII thô có trong mọi
   prompt đã gửi tới model, và đọc tận mắt câu trả lời có token PII.
4. Viết `starter/REPORT.md`, rồi làm phần trắc nghiệm của bài trong app.

**Một `REPORT.md` tốt**:

- Mở bằng bảng loại tin nhắn x trạng thái và ba con số: chặn oan trên tin bình thường và tin có PII, tấn công lọt qua,
  giá trị PII thô tới model.
- Phân tích **từng** tin bị xử lý sai (chặn oan, lọt qua, moderator gắn sai nhóm, model làm hỏng token PII): lớp nào
  quyết định, vì sao, sửa ở đâu.
- Bảng độ trễ theo lớp (p50, p95) và nhận xét lớp nào đáng tối ưu (chạy song song, cache, classifier nhỏ thay LLM).
- Quyết định vận hành: fail open hay fail closed cho từng lớp; ngưỡng cấm; dữ liệu nào được ghi log.
- Giới hạn: 48 tin nhắn tự viết, một model, moderator chưa được hiệu chỉnh trên dữ liệu thật.

## Tiêu chí đạt

- Test của `handle`, `traffic_report`, `stage_latency` pass: đúng thứ tự lớp, người bị cấm không tiêu rate limit, chặn
  injection trước mọi lời gọi model, moderator và LLM chỉ thấy văn bản đã che, nhánh tự hại không gọi LLM và không phạt
  người dùng, lọc output trước moderation output, khôi phục PII cho người dùng, bảng đếm và bảng độ trễ đúng.
- Lần chạy thật: 0 giá trị PII thô trong prompt gửi tới model.
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Một hàm nhỏ `timed(name, fn, *args)` ghi thời gian vào `stages` và trả kết quả giúp `handle` gọn và không quên đo lớp
nào. Trả kết quả qua một hàm `result(status, reply, flags)` dùng chung để mọi nhánh có cùng cấu trúc.

### Gợi ý 2

Đặt bước giả danh hoá **trước** moderation input: moderator cũng là một model, và nếu sau này bạn đổi sang moderation API
của bên thứ ba thì nó cũng là nơi dữ liệu đi tới. Nạp code Basic bằng `importlib.util.spec_from_file_location(tên,
đường_dẫn)` rồi `spec.loader.exec_module(module)`; đường dẫn tính từ gốc repo.
