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

Bản tham chiếu (code ngoài repo), 24 hoá đơn đầu của split validation, tháng 9 và 10/2026 mỗi tháng 12 hoá đơn, PC của track
(Ollama dùng chung; Whisper và TTS trên CPU 4 luồng); cả pipeline chạy chưa tới 3 phút khi model đã tải. Log:
`.superpowers/scratch/logs/adv01_ref_log.json`, `adv01_ref_voice.json`, `adv01_ref_run.log`, `adv01_month_error.log`.

| Khối | Thước đo | Giá trị |
| --- | --- | --- |
| Trích xuất (`qwen3-vl:2b`, 1024) | tổng đúng / F1 dòng hàng (24 hoá đơn) | 1.000 / 0.978 (precision 0.957, recall 1.000) |
| Trích xuất | độ trễ p50 mỗi hoá đơn | 1.22 s |
| Sổ chi tiêu | tổng tháng 9 so với sổ từ nhãn | 532 636 so với 532 636 (lệch 0%) |
| Sổ chi tiêu | tổng tháng 10 so với sổ từ nhãn | 1 413 134 so với 818 771 (**lệch 73%**) |
| Phân loại | số dòng phải gọi LLM | 49 / 87 (luật ~40 từ khoá chỉ bắt 44%) |
| STT (`small`, giọng TTS) | CER trung bình 8 câu | 0.178 |
| Hiểu ý định | đúng cả ý định và tham số, hỏi bằng chữ / bằng giọng | 5/8 / 3/8 |
| Báo cáo tháng | lần chạy phải viết lại hoặc dùng mẫu | 0/3 |
| Độ trễ một câu hỏi giọng nói (trung vị từng khối) | STT / route / TTS câu trả lời | 1.79 / 1.57 / 1.52 s |

Bốn bài học, mỗi cái là một chỗ bản tham chiếu **sai** và một bài portfolio tốt phải tìm ra:

- **F1 dòng hàng cao không có nghĩa sổ chi tiêu đúng.** Tháng 10 lệch 73% gần như hoàn toàn do **một** hoá đơn (số 22): nhãn
  có một món 280 000 cùng hai món tặng kèm không ghi giá; model gán 280 000 cho cả ba dòng. Trên thước đo dòng hàng đó chỉ là 2
  dòng thừa (precision 0.957); trên sổ chi tiêu đó là 560 000 đồng không có thật. Thước đo phải đo **thứ người dùng thấy**
  (tổng tháng), và pipeline cần luật cảnh báo: tổng các dòng vượt tổng hoá đơn thì hỏi lại người dùng (mục 2 lý thuyết: dùng
  làm tín hiệu, không làm luật từ chối).
- **Kiểm số bắt số bịa, không bắt số dùng sai.** Ba báo cáo đều qua bước kiểm (không có số lạ), nhưng cả ba viết "So với tháng
  trước: Tăng 532.636 đồng", trong khi 532 636 là **tổng tháng trước**, mức tăng thật là 880 498. Số có trong FACTS nên kiểm
  tra cho qua. Sửa: đưa sẵn mức chênh vào FACTS kèm nhãn rõ ("chênh so với tháng trước"), hoặc để code viết các câu có số và
  LLM chỉ viết câu nhận xét.
- **PII lọt qua khi định dạng đổi.** Câu "gửi báo cáo qua số không chín một hai ba bốn năm sáu bảy tám" được Whisper chép thành
  "091-234567 tăng": chỉ 9 chữ số có gạch nối, regex điện thoại (0 + 9 chữ số) không bắt, và bản chép lời đó đi thẳng vào log.
  Bộ lọc PII phải được test trên **đầu ra thật của STT**, không chỉ trên văn bản gõ tay.
- **Hiểu ý định là khối yếu nhất.** Ngay khi hỏi bằng chữ, `qwen2.5:3b` gán `total` cho câu hỏi theo nhóm (2 câu) và cho câu xin gửi báo cáo qua điện thoại; qua giọng
  nói thêm lỗi: "tháng 9" thành `2026-11`, "món nào" nghe thành "móng nạo" vẫn đúng ý định nhưng tự thêm `category`. Hàm
  `answer` của bản tham chiếu bỏ qua `category` khi intent là `total`, nên trả lời sai câu hỏi một cách tự tin. Cải thiện:
  vài ví dụ few-shot, luật hậu kiểm (có category thì intent phải là `by_category`), và hỏi lại khi tháng nằm ngoài dữ liệu.

Báo cáo của học viên không cần ra cùng các số này (tập câu hỏi, luật phân loại, prompt khác nhau); điều cần có là đo được
từng khối và tìm ra loại lỗi như trên.

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
