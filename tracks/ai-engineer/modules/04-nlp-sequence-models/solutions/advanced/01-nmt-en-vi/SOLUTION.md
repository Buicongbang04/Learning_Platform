# Hướng làm: dịch máy Anh-Việt (portfolio)

Bài không có code lời giải: pipeline là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả của một bản
tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Tiền xử lý | `html.unescape`, giữ chữ hoa, NFC; lọc cặp > 80 token BPE khi train | reference có chữ hoa và `'`, `"` thật; câu quá dài làm batch tốn bộ nhớ |
| Tokenizer | BPE riêng mỗi ngôn ngữ, 8 000, `WhitespaceSplit` + `end_of_word_suffix="</w>"` | dữ liệu đã tách từ; decoder `BPEDecoder` trả đúng dạng token cách dấu cách như reference |
| Kiến trúc | Embedding 256, BiGRU 512 encoder, GRU 512 decoder, attention Luong general, dropout 0.3 (13.6 triệu tham số) | Luong không input feeding cho phép teacher forcing song song, nhanh hơn trên GPU |
| Batch | xếp theo độ dài nguồn thành batch 64, xáo thứ tự batch mỗi epoch | ít padding, ổn định bộ nhớ |
| Optimizer | Adam 1e-3, clip 1.0, 8 epoch | đơn giản; dev BLEU còn tăng ở epoch 8 nên train lâu hơn sẽ hơn |
| Chọn checkpoint | BLEU greedy trên `tst2012` sau mỗi epoch | không nhìn `tst2013` cho tới lần đánh giá cuối |
| Decode | beam 5, $$\alpha = 0.6$$, từng câu một | beam theo batch nhanh hơn nhưng khó viết đúng |
| Đánh giá | sacrebleu `tokenize="none"` (dữ liệu đã tách từ), chrF, chữ ký | so được với bảng khác cùng chữ ký |

Lỗi hay gặp: so BLEU với reference đã `lower()` trong khi hypothesis giữ chữ hoa (hoặc ngược lại), mất 2-5 BLEU vô lý;
quên `html.unescape` một phía; ghi thiếu dòng cho câu dịch rỗng (tệp lệch dòng, BLEU sụp); chọn checkpoint theo `tst2013`;
beam search không chuẩn hoá độ dài nên bản dịch ngắn bất thường (brevity penalty kéo BLEU xuống); quên `model.eval()` khi
decode (dropout làm bản dịch ngẫu nhiên).

## Kết quả tham chiếu

RTX 3050 Laptop 4GB dùng chung với tiến trình khác (dưới 1.5 GB VRAM), seed 0. BPE: 1.13 token mỗi từ tiếng Anh; 130 700
cặp sau khi lọc.

| Epoch | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Train loss | 4.64 | 3.96 | 3.77 | 3.65 | 3.58 | 3.48 | 3.39 | 3.33 |
| Dev perplexity | 52.9 | 41.3 | 37.1 | 34.9 | 32.9 | 29.4 | 27.7 | 26.5 |
| Dev BLEU greedy | 4.12 | 5.82 | 6.49 | 6.75 | 7.81 | 8.70 | 9.21 | 9.88 |

Mỗi epoch 5-7 phút (kể cả decode dev). `tst2013`, checkpoint epoch 8:

| Decode | BLEU (`tok:none`) | chrF | Thời gian |
| --- | --- | --- | --- |
| Greedy | 9.78 | không đo | 24 s |
| Beam 5, $$\alpha = 0.6$$ | 11.63 (43.0/18.5/8.6/4.3, BP 0.887) | 27.9 | 90 s |

@@FILL_A01_ABL

Đọc kết quả:

- Beam 5 hơn greedy gần 2 BLEU, chủ yếu nhờ precision n-gram dài; brevity penalty 0.887 cho thấy bản dịch vẫn ngắn hơn
  reference 11%: thử $$\alpha$$ lớn hơn.
- Dev BLEU còn tăng khoảng 0.5-1 mỗi epoch ở cuối: model **chưa hội tụ**, train lâu hơn (12-15 epoch), lr giảm dần, hai tầng
  encoder là hướng rẻ nhất để lên 15+ BLEU. Hệ thống của Stanford năm 2015 đạt khoảng 23.
- Lỗi điển hình (ví dụ thật trên `tst2013`): "And I was very proud ." thành "Và tôi rất hào hứng ."; câu về chủ tịch Kim
  Il-Sung thành "lịch sử của Alan Kay"; "Bắc Triều Tiên" thì dịch đúng. Bản dịch trôi chảy nhưng bịa: decoder là language
  model tiếng Việt tốt hơn khả năng căn chỉnh của attention.

## Rubric

| Tiêu chí | Điểm | Đạt khi |
| --- | --- | --- |
| Test | 15 | `beam_search` pass mọi test; `tst2013.hyp.vi` đủ 1 268 dòng, BLEU ≥ 8.0 |
| Pipeline đúng | 15 | tiền xử lý nhất quán hai phía, BPE train chỉ trên train, chọn checkpoint theo dev, `tst2013` chỉ dùng một lần |
| Đánh giá chuẩn | 10 | sacrebleu có chữ ký, BLEU và chrF, greedy và beam, thời gian decode |
| Ablation | 20 | ít nhất: không attention / có attention, greedy / beam, một biến thể của bạn; cùng ngân sách epoch; bảng có số |
| Phân tích lỗi | 20 | BLEU theo nhóm độ dài, ≥ 5 ví dụ có giải thích bằng cơ chế (exposure bias, nút thắt, BPE, tên riêng), attention heatmap có câu đọc |
| Chất lượng portfolio | 20 | tóm tắt có số ở đầu, đặt BLEU vào bối cảnh (so với gì), đường cong học có câu đọc, giới hạn và bước tiếp (Transformer) |

Đạt từ 70 điểm. Báo cáo chỉ có một con số BLEU không kèm chữ ký, hoặc kết luận "Bahdanau tốt hơn Luong" từ chênh lệch dưới
0.5 BLEU một lần chạy, không quá 50 điểm.
