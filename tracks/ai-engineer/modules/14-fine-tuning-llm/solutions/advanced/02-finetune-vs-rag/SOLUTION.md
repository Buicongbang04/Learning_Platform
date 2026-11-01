# Hướng làm: fine-tune để "nhớ" luật hay RAG

Bài không có code lời giải: phần thí nghiệm có nhiều cách dựng đúng, và `REPORT.md` là phân tích của bạn. Dưới đây là các
quyết định cần cân nhắc, kết quả của một bản tham chiếu để bạn so, và rubric chấm.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Định dạng trả lời | đúng một trích dẫn `<số hiệu>, Điều <n>` theo uid của corpus | kiểm bằng code, không cần LLM chấm; cùng đơn vị với qrels |
| Câu có nhiều điều đúng | train với điều đúng đầu tiên, chấm đúng nếu trùng **bất kỳ** điều nào | tránh dạy hai đáp án mâu thuẫn cho cùng câu |
| Tập đo | 300 câu ghim của module 13 (chưa thấy) và 300 câu train đầu tiên (đã thấy) | tách tổng quát hoá khỏi học thuộc |
| SFT | LoRA r = 16 mọi lớp tuyến tính, lr 2e-4 cosine, batch 32, TRL prompt-completion | cùng cấu hình các bài Intermediate để so được |
| "Đọc" corpus | thêm một mẫu "tiêu đề điều → trích dẫn" cho mỗi điều (61 425 mẫu), 1 epoch | cách rẻ nhất để model thấy mọi số hiệu; không phải continued pretraining trên toàn văn |
| Baseline retrieval | BM25 âm tiết của module 13 (k1 1.5, b 0.75) trên `title + text`, top-1 | baseline rẻ nhất; dense/hybrid/rerank của module 13 còn tốt hơn |

Những lỗi hay gặp:

- Không kiểm phần giao giữa điều được hỏi ở train và ở tập ghim: lúc đó không biết con số "chưa thấy" thật ra đo gì.
- Đo trên câu train rồi kết luận "model đã học luật".
- Parse lỏng (tìm số hiệu ở bất kỳ đâu): model viết "Điều 5 Luật Giao thông" cũng được tính, làm cột `format` vô nghĩa.
- So model fine-tune với BM25 trên hai tập câu khác nhau.

## Kết quả tham chiếu

<<A02_RESULTS>>

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | Mọi test pass |
| Thí nghiệm đúng | 25 | Đủ bốn cấu hình trên cùng 300 câu ghim và 300 câu train; SFT chỉ học phần trả lời; có con số giao giữa điều train và điều ghim |
| Số liệu | 20 | Bảng `exact`, `law`, `format` cho mọi cấu hình trên cả hai tập, thời gian train, VRAM |
| Phân tích lỗi | 20 | Đọc ít nhất 10 trích dẫn sai, phân loại (số hiệu không tồn tại, đúng văn bản sai điều, văn bản phổ biến trong train), có đếm |
| Khuyến nghị | 20 | Tách học thuộc và tổng quát hoá; nói rõ fine-tune có ích ở đâu trong hệ trợ lý pháp luật (embedding, khuôn trả lời, đọc nguồn), ở đâu không; nêu điều bảng chưa đo |

Đạt từ 70 điểm. Báo cáo kết luận "fine-tune học được luật" từ số trên câu train, hoặc so với BM25 trên tập khác, không quá
50 điểm.
