# Hướng làm: prompt regression suite

Bài không có code lời giải: suite và báo cáo là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả của
một bản tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Phiên bản prompt | dict `{tên: {"messages": hàm dựng messages, "format": schema hoặc None, "num_predict": n, "parse": hàm đọc nhãn}}` | prompt, ràng buộc output và parser đổi cùng nhau; tách chúng ra là nguồn hồi quy hay gặp nhất (đổi định dạng mà quên đổi parser) |
| Khoá cache | `cache_key(messages mẫu với chỗ trống {sentence}, model, tham số sinh + format, id câu)` | sửa một chữ trong prompt tự chạy lại đúng phiên bản đó; đổi model hay `temperature` cũng vậy; không đổi gì thì không gọi model |
| Lưu cache | một tệp JSON, mỗi khoá `{reply, seconds, prompt_tokens, output_tokens}` | độ trễ lưu lúc gọi, không đo lại khi đọc cache; đổi parser hay thước đo không phải gọi lại |
| Tập ghim | 150 câu test, 50 mỗi nhãn, `random_state=0` (như Intermediate 02) | dùng lại được số của bài trước làm baseline; ghi rõ tập cân bằng khác phân phối thật |
| Cổng | `max_drop` 0.02, `class_max_drop` 0.10, không cho thêm câu `None` | 150 câu: đòi "tốt hơn có ý nghĩa" sẽ chặn gần như mọi thay đổi; chặn tụt rõ, tụt quá ngưỡng, hy sinh lớp hiếm, output hỏng |
| Sàn nhiễu | cùng baseline, chạy chỉ CPU (`num_gpu` 0) | chạy lại y hệt trên cùng máy cho 0 câu đổi nhãn, nên không đo được nhiễu thật; đổi phần cứng thì có |
| Chi phí | token đo được x bảng giá Claude Haiku 5.5 kiểm ngày 2026-11-01 (0.10 / 0.50 USD mỗi MTok), ghi rõ token là của tokenizer Qwen | so tương đối giữa các prompt; con số tuyệt đối là ước lượng |

Lỗi hay gặp: khoá cache chỉ gồm tên phiên bản (sửa prompt mà giữ tên thì dùng lại kết quả cũ, cổng "xanh" sai); cổng chỉ
nhìn macro-F1 (thay đổi hy sinh lớp neutral lọt qua); so ứng viên chạy hôm nay với baseline chạy tuần trước trên máy
khác; báo "tốt hơn" từ một chênh lệch trong sàn nhiễu.

## Kết quả tham chiếu

§§A01REF§§

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Suite | 20 | Phiên bản prompt là dữ liệu (gồm parser); cache theo `cache_key`, sửa prompt tự chạy lại đúng phiên bản; cả bảng sinh bằng một lệnh |
| Cổng và diễn giải | 25 | Cổng áp cho ít nhất 4 ứng viên; giải thích từng ngưỡng; có sàn nhiễu đo được; không gọi chênh lệch trong nhiễu là cải thiện; nêu một ca không đồng ý với cổng |
| Chi phí và độ trễ | 10 | Token vào/ra và p50 cho mọi phiên bản; chi phí 1 000 câu theo bảng giá có ngày kiểm hoặc ghi "giả định" |
| Phân tích lỗi | 20 | Ít nhất 5 câu bị thay đổi bị chặn làm sai, đọc tận mắt, có phân loại (ví dụ lệch, nhãn đáng ngờ, câu mơ hồ) |
| Báo cáo | 10 | Quyết định có số ở đầu, thiết lập tái lập được, có giới hạn |

Đạt từ 70 điểm. Cổng chỉ dựa trên macro-F1 điểm (không khoảng tin cậy, không F1 từng lớp), hoặc khoá cache không gồm nội
dung prompt, không quá 50 điểm.
