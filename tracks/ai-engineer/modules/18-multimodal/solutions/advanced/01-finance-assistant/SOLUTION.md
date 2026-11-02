# Hướng làm: trợ lý tài chính đa phương thức

Bài không có code lời giải: pipeline, câu hỏi và báo cáo là của bạn. Dưới đây là cách làm các hàm được test, các quyết định
thiết kế, kết quả của một bản tham chiếu (chạy ngoài repo) để bạn so, và rubric.

## Các hàm được test

- `expenses_from_receipt`: duyệt `items`, bỏ phần tử không phải dict, `parse_amount` từng `amount`, giữ số dương (giảm giá
  âm không phải một khoản chi); không còn dòng nào thì dùng tổng. Hoá đơn chỉ đọc được tổng vẫn vào sổ, mất chi tiết nhưng
  không mất tiền.
- `categorize`: chuẩn hoá tên thành chữ hoa, mọi ký tự không phải chữ hay số thành dấu cách, bọc hai dấu cách ở hai đầu, rồi
  tìm `" " + từ khoá + " "`. So chuỗi con thì "ES" (đá, tiếng Indonesia) khớp cả "TESTER". LLM gọi một lần với schema enum,
  bọc `try/except` cả lời gọi lẫn `json.loads`, kiểm giá trị thuộc danh sách.
- `monthly_summary`: lọc theo tiền tố `"YYYY-MM"`, cộng theo nhóm, sắp bằng khoá `(-tiền, tên)`; `n_receipts` đếm cặp (ngày,
  cửa hàng) vì một hoá đơn sinh nhiều khoản.
- `mask_pii`: email trước (để chữ số trong email không bị bắt nhầm), thẻ sau với kiểm Luhn (module 19 mục 3), điện thoại cuối.
  Mã đơn 12 chữ số không qua Luhn và không bắt đầu bằng 0 nên được giữ.
- `route`: schema có `intent` enum, `month` và `category` cho phép `null`; kiểm lại phía client vì constrained decoding không
  bảo đảm ngữ nghĩa (tháng "2026-13"). Mọi lỗi về `"other"`: an toàn hơn đoán bừa.
- `format_vnd`: `f"{round(x):,}".replace(",", ".")`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Đọc hoá đơn | `qwen3-vl:2b`, cạnh dài 1024, prefill `"{"` | cân bằng độ đúng và token theo bài Intermediate 01 |
| Sổ chi tiêu | list `Expense` (ngày, cửa hàng, món, tiền, nhóm) | mọi câu trả lời và báo cáo tính từ đây bằng code |
| Phân loại | ~40 từ khoá tiếng Indonesia/Anh cho "ăn uống", "đồ uống", LLM `qwen2.5:3b` cho phần còn lại | luật bắt phần lớn dòng, LLM cho tên lạ |
| STT | `faster-whisper small`, int8, CPU, beam 5, `language="vi"` | điểm khởi đầu của mục 3 lý thuyết |
| Hiểu câu hỏi | `qwen2.5:3b` + JSON schema (intent, tháng, nhóm), ngày hôm nay trong system prompt | LLM chỉ hiểu, không tính |
| Câu trả lời | mẫu câu do code điền số, `format_vnd` | không có số nào do LLM sinh |
| TTS | `mms-tts-vie`, seed 0, câu trả lời qua `normalize_for_tts` của bài Intermediate 02 | vocab không có chữ số |
| Báo cáo tháng | LangGraph: `facts` (code) → `write` (LLM) → `check` (code so mọi cụm số) → viết lại tối đa 1 lần → mẫu cố định | không để số bịa lọt ra |

## Kết quả tham chiếu

⟦TODO adv01 ref⟧

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 10 | Mọi test pass |
| Pipeline chạy trọn, có cache | 15 | Ảnh tới báo cáo trong một lần chạy notebook; chạy lại không gọi lại model; độ trễ đo ở chỗ gọi model |
| Số đo từng khối | 25 | Có độ đúng trích xuất, sai số tổng tháng so với sổ từ nhãn, CER của STT, độ đúng ý định chữ và giọng trên bộ câu có nhãn, số con số bị bắt trong báo cáo, độ trễ từng khối; mỗi số kèm cỡ mẫu |
| LLM không làm toán | 15 | Mọi con số trong câu trả lời và báo cáo do code tính; có bước kiểm số và đường dự phòng |
| Riêng tư, an toàn, giấy phép | 15 | Che PII trước khi log; nói rõ dữ liệu nào lưu ở đâu; xử lý injection qua ảnh; nêu giấy phép không thương mại |
| Phân tích lỗi và giới hạn | 20 | Đọc tận mắt các lỗi, gắn mỗi lỗi vào một khối; nêu giới hạn (rupiah, dữ liệu giả, cỡ mẫu, giọng TTS) và việc tiếp theo |

Đạt từ 70 điểm. Báo cáo có con số do LLM tự cộng, hoặc ghi bản chép lời chưa che PII vào log, không quá 50 điểm.
