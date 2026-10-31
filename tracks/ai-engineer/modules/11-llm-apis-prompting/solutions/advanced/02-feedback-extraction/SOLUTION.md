# Hướng làm: ứng dụng trích xuất phản hồi sinh viên

Bài không có code lời giải: ứng dụng và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả
của một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Schema | 5 trường, `required` đủ cả 5, `suggestion` kiểu `["string", "null"]`, `additionalProperties: false` | trường luôn có mặt giúp code phía sau đơn giản; `null` tường minh tốt hơn thiếu khoá |
| Nhãn | giá trị enum tiếng Anh, mô tả tiếng Việt trong prompt | enum ngắn, ổn định để đọc bằng code; mô tả mới là thứ dạy model ranh giới |
| Quy tắc ngoài schema | `suggestion` có khi và chỉ khi `actionable`; `aspects` không trùng, không rỗng | JSON Schema khó diễn đạt ràng buộc giữa hai trường; lỗi loại này lọt qua constrained decoding |
| Ép output | `format` = `EXTRACTION_SCHEMA` (Ollama) | bỏ hẳn lớp lỗi parse; chi phí là độ trễ (đo ở dưới) |
| Gọi lại | bản ghi sai quy tắc gửi lại một lần kèm danh sách lỗi (bài Basic 03) | sửa được phần lớn lỗi quy tắc với một lượt gọi thêm cho số ít câu |
| Thước đo | macro-F1 cảm xúc và chủ đề theo nhãn UIT-VSFC, tỉ lệ hợp lệ; trường tự do chấm tay 30 câu | có nhãn thì đo bằng nhãn; không có nhãn thì người chấm, không tin cảm giác |
| Tập | 150 câu ghim (cân bằng cảm xúc) | dùng lại tập của Intermediate 02 để so trực tiếp với prompt chỉ phân loại cảm xúc |

Lỗi hay gặp: tin `format` nên không validate (quy tắc nghiệp vụ vẫn sai); chấm chủ đề bằng accuracy trên tập mà 2/3 là
`lecturer` (đoán toàn `lecturer` đã được 0.66); đặt `aspects` không giới hạn độ dài khiến output dài và chậm; so cấu hình
mà không ghi model sinh, phần cứng; ước chi phí bằng số từ thay vì token đo được.

## Kết quả tham chiếu

§§A02REF§§

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
