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

PC của track (RTX 3060 12GB), kernel `ai-gpu`, LoRA r = 16, batch hiệu dụng 32. GPU dùng chung với tiến trình khác (Ollama
của một module khác giữ 2.5 tới 7 GB) trong mọi lượt train, nên thời gian chỉ để tham khảo.

| Cấu hình | Train | Câu ghim: exact | Câu ghim: law | Câu train: exact | Câu train: law | Format |
| --- | --- | --- | --- | --- | --- | --- |
| BM25 âm tiết top-1, toàn corpus | index 9.8 giây (CPU) | 0.433 | 0.660 | 0.483 | 0.680 | 1.00 |
| Qwen2.5-0.5B gốc, chỉ prompt | | 0.000 | 0.000 | 0.000 | 0.000 | 0.01 |
| SFT trên 2 432 câu train, 3 epoch | 228 bước, 465 giây, 1.46 GiB | 0.000 | 0.290 | 0.010 | 0.103 | 1.00 |
| SFT trên câu train + 61 425 mẫu "tiêu đề → trích dẫn", 1 epoch | 1 992 bước, 3 279 giây, 1.58 GiB | 0.007 | 0.437 | 0.017 | 0.310 | 1.00 |

Trích dẫn trỏ tới một điều **có thật** trong corpus: 54% (SFT câu hỏi) và 76% (thêm tiêu đề) trên câu ghim; phần còn lại là
số hiệu hoặc số điều bịa ra theo đúng khuôn.

Đọc bảng:

- **Không có gì để nhớ**: 0 trên 300 câu ghim có điều đúng từng được hỏi ở train. Closed-book SFT trên câu hỏi train vì
  vậy không thể trích đúng điều nào cho câu ghim, và đúng là 0. Nó học được **khuôn** (định dạng 100%, so với 1% của model
  gốc) và vài văn bản phổ biến (đúng văn bản ở 29% câu ghim). Văn bản thì có chung: 269/300 câu ghim có văn bản đúng từng xuất
  hiện ở train, và riêng Nghị định 100/2019/NĐ-CP là văn bản đúng của 83/300 câu ghim, nên đoán văn bản phổ biến đã ăn điểm
  `law`.
- **Với ngân sách train này, không học thuộc nổi chính câu train**: 1% câu train trích đúng điều sau 3 epoch (r = 16, lr
  2e-4, batch 32), thấp hơn hẳn BM25 trên chính các câu đó (48%). Loss vẫn đang giảm ở cuối lượt train (trung bình cả lượt
  0.64), nên train lâu hơn, hạng cao hơn hoặc full fine-tune sẽ nhớ được nhiều hơn; bảng chỉ cho thấy học thuộc 2 432 cặp
  (câu hỏi, số hiệu + số điều) không rẻ, và kể cả nhớ được thì cũng không giúp gì cho câu chưa thấy (dòng trên).
- **"Đọc" cả corpus giúp ở mức văn bản, không ở mức điều**: thêm 61 425 mẫu tiêu đề nâng `law` lên 0.44 và tỉ lệ trích dẫn có
  thật lên 76%, nhưng `exact` vẫn chỉ 2/300, so với 130/300 của BM25 chạy 10 giây trên CPU. Model biết "điều này thuộc văn bản
  nào" khi được hỏi đúng tiêu đề, nhưng không nối được câu hỏi đời thường với tiêu đề điều.
- **BM25 thắng ở mọi cột trừ `format`** (hoà 1.00), và đó là baseline yếu nhất của module 13 (hybrid và rerank còn cao hơn). Hơn nữa nó trích được
  điều mới thêm vào corpus ngay lập tức, còn model fine-tune phải train lại.
- Nơi fine-tune có ích trong hệ này: embedding model (capstone milestone 5), khuôn trả lời có trích dẫn, và đọc nguồn
  RAG tốt hơn (SFT trên (câu hỏi, các điều đã truy hồi, câu trả lời có trích dẫn)): bảng này chưa đo cấu hình đó.

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
