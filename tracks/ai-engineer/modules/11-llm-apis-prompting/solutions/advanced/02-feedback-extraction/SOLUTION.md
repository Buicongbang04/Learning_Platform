# Hướng làm: ứng dụng trích xuất phản hồi sinh viên

Bài không có code lời giải: ứng dụng và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả
của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Schema | 5 trường, `required` đủ cả 5, `suggestion` kiểu `["string", "null"]`, `additionalProperties: false` | trường luôn có mặt giúp code phía sau đơn giản; `null` tường minh tốt hơn thiếu khoá |
| Nhãn | giá trị enum tiếng Anh, mô tả tiếng Việt trong prompt | enum ngắn, ổn định để đọc bằng code; mô tả mới là thứ dạy model ranh giới |
| Quy tắc ngoài schema | `suggestion` có khi và chỉ khi `actionable`; `aspects` không có phần tử rỗng, không trùng | JSON Schema khó diễn đạt ràng buộc giữa hai trường; lỗi loại này lọt qua constrained decoding |
| Ép output | `format` = `EXTRACTION_SCHEMA` (Ollama) | bỏ hẳn lớp lỗi parse; chi phí là độ trễ (đo ở dưới) |
| Gọi lại | bản ghi sai quy tắc gửi lại một lần kèm danh sách lỗi (bài Basic 03) | sửa được phần lớn lỗi quy tắc với một lượt gọi thêm cho số ít câu |
| Thước đo | macro-F1 cảm xúc và chủ đề theo nhãn UIT-VSFC, tỉ lệ hợp lệ; trường tự do chấm tay 30 câu | có nhãn thì đo bằng nhãn; không có nhãn thì người chấm, không tin cảm giác |
| Tập | 150 câu ghim (cân bằng cảm xúc) | dùng lại tập của Intermediate 02 để so trực tiếp với prompt chỉ phân loại cảm xúc |

Lỗi hay gặp: tin `format` nên không validate (quy tắc nghiệp vụ vẫn sai); chấm chủ đề bằng accuracy trên tập mà 2/3 là
`lecturer` (đoán toàn `lecturer` đã được 0.66); đặt `aspects` không giới hạn độ dài khiến output dài và chậm; so cấu hình
mà không ghi model sinh, phần cứng; ước chi phí bằng số từ thay vì token đo được.

## Kết quả tham chiếu

Bản tham chiếu (giữ ngoài repo) chạy trên 150 câu ghim, `qwen2.5:3b` qua Ollama 0.13.5, `temperature` 0, `seed` 0,
`num_predict` 256, cùng system prompt mô tả từng khoá, ngày 2026-11-01, PC của track (RTX 3060 **dùng chung** với một job
train khác; số giây chỉ để so tương đối). Phân phối chủ đề của tập ghim: lecturer 99, training_program 27, others 17,
facility 7.

| Cấu hình | Hợp lệ | Sai quy tắc | Gọi lại | Cảm xúc acc / macro-F1 | Chủ đề acc / macro-F1 | `actionable` | Vào / ra | p50 giây |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| chỉ dặn trong prompt | 150 / 150 | 0 | 0 | 0.713 / 0.665 | 0.747 / 0.676 | 15.3% | 266 / 53.7 | 1.02 |
| JSON mode | 150 / 150 | 0 | 0 | 0.713 / 0.665 | 0.747 / 0.676 | 15.3% | 266 / 53.7 | 2.95 |
| JSON schema | 150 / 150 | 0 | 0 | 0.713 / 0.665 | 0.747 / 0.676 | 15.3% | 266 / 53.7 | 2.01 |
| JSON schema + gọi lại một lần | 150 / 150 | 0 | 0 | như trên | như trên | như trên | như trên | như trên |

- Ba mức ép cho output giống nhau từng byte ở 149/150 câu. Với prompt mô tả khoá rõ và model này, ép schema không đổi
  kết quả; nó là bảo hiểm cho model khác, input lạ, prompt dài hơn. Không câu nào sai quy tắc nghiệp vụ nên đường gọi
  lại **không được kích hoạt** lần nào trên tập này: muốn kiểm nó, dựng ca lỗi bằng `FakeLLM` hoặc input cố ý mâu thuẫn.
- F1 từng lớp (JSON schema): cảm xúc negative 0.730, neutral 0.381, positive 0.883; model chỉ chọn neutral 13/150 lần,
  29 câu neutral thành negative, 9 thành positive. Chủ đề lecturer 0.836, training_program 0.576, facility 0.923, others
  0.370; nhầm nhiều nhất là lecturer thành training_program (12) và others thành lecturer (10). Đoán toàn `lecturer`
  đã được accuracy chủ đề 0.66, nên accuracy 0.747 nói rất ít.
- So với prompt chỉ phân loại cảm xúc của Intermediate 02 (macro-F1 0.804), trích xuất 5 trường một lượt làm cảm xúc tụt
  hẳn, gần như toàn bộ ở lớp neutral. Khuyến nghị của bản tham chiếu: lấy cảm xúc từ một lời gọi riêng (hoặc một bộ phân
  loại đã train ở module 04), dùng lời gọi trích xuất cho chủ đề, khía cạnh và gợi ý.
- **Tự chấm 30 câu đầu** (implementer viết bản tham chiếu tự chấm, một người, bảng 30 dòng lưu ngoài repo cùng bản
  tham chiếu; tiêu chí viết trước: `actionable` đúng khi phản hồi nêu hoặc ngầm chỉ một việc cụ thể làm được, ví dụ "máy chiếu hơi mờ"; `aspects` đạt khi mọi cụm có trong câu và không
  là chữ đệm): `actionable` đồng ý 27/30, cả 3 câu lệch đều là model bỏ sót việc ngầm định ("máy chiếu hơi mờ", "giờ lên
  lớp không chắc chắn", "chỉ cần cho bài tập qua web"), không có câu model gắn `true` sai; 4/4 `suggestion` có mặt đều
  dùng được; `aspects` đạt 23/30 khi chấm nới (chấp nhận cụm chung như "giảng viên" nếu câu rõ ràng nói về giảng viên), chỉ
  khoảng 19/30 nếu chấm chặt đúng tiêu chí; lỗi chính là **đệm cho đủ 3 cụm** bằng chữ chép từ mô tả chủ đề trong prompt
  ("giảng viên", "cách dạy") hoặc chữ vô nghĩa ("phản hồi").
- Chi phí 10 000 phản hồi một học kỳ với 266 token vào và 53.7 token ra mỗi câu (token Qwen, ước lượng), giá kiểm
  2026-11-01: Claude Haiku 5.5 khoảng 0.53 USD, Gemini 3.8 Flash khoảng 4.0 USD (giá tới 31/12/2026), gpt-6.1-terra
  khoảng 5.4 USD, Claude Sonnet 5.5 khoảng 10.7 USD. Tiền không phải rào cản; rào cản là dữ liệu cá nhân: phản hồi có
  thể nêu tên giảng viên, sinh viên, lớp, nên cần chính sách của trường trước khi gửi ra API ngoài, hoặc chạy model
  local như bản tham chiếu.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Ứng dụng | 20 | Schema, prompt, validate (schema + quy tắc), gọi lại có giới hạn, cache, chạy lại cả lô bằng một lệnh |
| Đo bằng nhãn | 20 | Ít nhất hai cấu hình trên cùng tập, macro-F1 cảm xúc và chủ đề, F1 từng lớp, tỉ lệ hợp lệ, số câu gọi lại, độ trễ, token |
| Tự chấm trường tự do | 15 | 30 câu, tiêu chí viết trước, tỉ lệ đồng ý, model sai theo hướng nào |
| Phân tích lỗi và chi phí | 20 | Ít nhất 5 câu sai đọc tận mắt có phân loại; chi phí 10 000 phản hồi theo bảng giá có ngày kiểm hoặc "giả định"; nêu rủi ro dữ liệu cá nhân |
| Báo cáo | 10 | Khuyến nghị có số ở đầu, thiết lập tái lập được, giới hạn |

Đạt từ 70 điểm. Báo cáo chỉ dùng accuracy chủ đề trên tập lệch, hoặc không kiểm quy tắc nghiệp vụ, không quá 50 điểm.
