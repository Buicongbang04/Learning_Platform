---
title: Trợ lý tài chính đa phương thức - hoá đơn, giọng nói, báo cáo tháng (portfolio)
level: advanced
services: []
files:
  - path: starter/assistant.ipynb
    note: 7 hàm TODO (1 dán từ Basic 02), pipeline của bạn
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_assistant.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py cord-v2
  - ollama pull qwen3-vl:2b
  - ollama pull qwen2.5:3b
  - uv run jupyter lab tracks/ai-engineer/modules/18-multimodal/exercises/advanced/01-finance-assistant/starter/assistant.ipynb
  - uv run pytest tracks/ai-engineer/modules/18-multimodal/exercises/advanced/01-finance-assistant -q
---

## Mục tiêu

Làm một sản phẩm đa phương thức hoàn chỉnh, chạy local, có số đo cho từng khối: chụp hoá đơn thành sổ chi tiêu, hỏi bằng
giọng nói và nghe câu trả lời có số đúng, nhận báo cáo tháng không có con số bịa. Đây là bài portfolio của module: người đọc
REPORT.md phải thấy bạn biết khối nào hỏng bao nhiêu và vì sao, không chỉ thấy một bản demo chạy được.

## Đề bài

**Phần cứng:** GPU 4GB · ~480 phút

Thời gian trên là thời gian làm bài. Phần máy chạy của bản tham chiếu (24 hoá đơn, 8 câu hỏi giọng nói, 3 lần sinh báo
cáo) mất khoảng 10 phút trên PC của track (xem `SOLUTION.md`); Whisper và TTS chạy CPU. Chỉ có CPU: thu nhỏ ảnh về cạnh dài
768 và dùng 12 hoá đơn (vision LLM trên CPU mất cỡ 20 giây tới vài phút mỗi ảnh, mục 2 lý thuyết).

**Dữ liệu cá nhân là giả lập, và phải giữ như vậy.** Dùng 24 hoá đơn đầu của split `validation` của `cord-v2` (split
`test` để dành cho bài Intermediate 01), gán ngày giả trong tháng 9 và 10/2026 và tên cửa hàng tự đặt. Số tiền là rupiah;
coi như đồng cho bài tập và ghi rõ điều đó trong báo cáo. Câu hỏi giọng nói do chính TTS đọc (không thu giọng ai). Đổi
sang MC-OCR (hoá đơn Việt Nam) theo mục 2 lý thuyết khi bạn có quyền truy cập.

1. Trong `starter/assistant.ipynb`, viết các hàm của cell chấm điểm (test kiểm trên dữ liệu nhỏ với `FakeLLM`):
   `parse_amount` (dán từ Basic 02), `expenses_from_receipt`, `categorize`, `monthly_summary`, `mask_pii`, `route`,
   `format_vnd`.
2. Dựng pipeline trong các cell `explore` của bạn:
   - **Hoá đơn → sổ chi tiêu**: vision LLM (cách gọi và parse của bài Intermediate 01), `expenses_from_receipt`, chấm độ
     đúng trích xuất bằng bộ chấm Basic 02, và **sai số tổng tháng** của sổ chi tiêu so với sổ dựng từ nhãn.
   - **Phân loại**: luật từ khoá của bạn trước, LLM sau; báo bao nhiêu dòng đi qua LLM.
   - **Hỏi bằng giọng nói**: ít nhất 8 câu hỏi tiếng Việt có nhãn ý định (tự viết, gồm câu ngoài phạm vi và một câu có
     số điện thoại), đọc bằng `mms-tts-vie`, nghe bằng Whisper, `mask_pii`, `route`, **code** tính câu trả lời (hàm `answer`
     của bạn, không chấm bằng test), chuẩn hoá số (bài Intermediate 02), TTS đọc lại. So độ đúng `route` khi hỏi bằng chữ và
     bằng giọng; đo thời gian từng khối.
   - **Báo cáo tháng**: một agent (LangGraph, module 17, hoặc vòng lặp tự viết) theo luồng: code tính số liệu, LLM viết đoạn
     văn chỉ từ số liệu đó, code **kiểm mọi con số** trong văn bản, sai thì cho viết lại một lần rồi dùng mẫu cố định. Chạy
     vài lần, đếm số lần phải viết lại hoặc dùng mẫu.
3. Viết `starter/REPORT.md` theo khung có sẵn, rồi làm phần trắc nghiệm của bài trong app.

**Một REPORT.md tốt**:

- Mở bằng **kiến trúc một hình** (mermaid) và **bảng số đo từng khối**: trích xuất (độ đúng tổng, F1 dòng hàng), sai số tổng
  tháng, CER của STT, độ đúng ý định chữ và giọng, số con số bị bắt trong báo cáo, độ trễ từng khối.
- Nói rõ **LLM làm gì và không làm gì**: hiểu câu hỏi và viết câu chữ, không cộng tiền.
- Có mục **riêng tư và an toàn**: PII nào đi qua đâu, cái gì được che, cái gì được lưu, ảnh có EXIF không, prompt injection
  qua ảnh xử lý thế nào (mục 2 lý thuyết), giấy phép của các model.
- Có **phân tích lỗi**: đọc tận mắt hoá đơn sai, câu hỏi bị hiểu sai qua giọng nói nhưng đúng qua chữ, và đặt mỗi lỗi vào
  đúng khối.
- Có **giới hạn và việc tiếp theo**: dữ liệu giả lập, rupiah, 8 câu hỏi là ít, giọng TTS không phải giọng người thật.

## Tiêu chí đạt

- Mọi test pass.
- Pipeline chạy hết từ ảnh tới báo cáo; mọi lời gọi model được cache, chạy lại notebook không gọi lại model.
- Không có con số nào trong câu trả lời hay báo cáo do LLM tự tính.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng số đo từng khối và hình kiến trúc.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Dựng từng khối như một hàm nhận và trả dữ liệu có cấu trúc, cache kết quả của khối gọi model ra đĩa (JSONL theo chỉ số),
rồi mới nối chúng lại. Đo độ trễ ở chỗ gọi model, không ở chỗ đọc cache. Sổ chi tiêu "đúng" để so là sổ dựng từ nhãn
`cord-v2` bằng chính `gold_from_cord` của Basic 02.

### Gợi ý 2

Kiểm số trong báo cáo: lấy mọi cụm chữ số (`\d[\d.]*\d|\d`) trong văn bản LLM viết và trong số liệu bạn đưa cho nó, phần
chênh là số bịa (cho phép vài số hiển nhiên như năm, tháng). Với `route`, `month` nên là chuỗi `"YYYY-MM"`: đưa ngày hôm
nay vào system prompt để LLM hiểu "tháng này", "tháng trước".
