# Hướng làm: dịch máy Anh-Việt (portfolio)

Bài không có code lời giải: pipeline là thiết kế của bạn. Dưới đây là các quyết định cần cân nhắc, kết quả của một bản
tham chiếu để bạn so, và rubric chấm `REPORT.md`.

## Quyết định thiết kế

| Quyết định | Bản tham chiếu chọn | Vì sao |
| --- | --- | --- |
| Tiền xử lý | `html.unescape`, giữ chữ hoa, NFC; lọc cặp > 80 token BPE khi train | reference có chữ hoa và `'`, `"` thật; câu quá dài làm batch tốn bộ nhớ |
| Tokenizer | BPE riêng mỗi ngôn ngữ, 8 000, `WhitespaceSplit` + `end_of_word_suffix="</w>"` | dữ liệu đã tách từ; decoder `BPEDecoder` trả đúng dạng token cách dấu cách như reference |
| Kiến trúc | Embedding 256, BiGRU 512 encoder, GRU 512 decoder, dropout 0.3; ba biến thể attention: không có (12.3 triệu tham số), Luong general không input feeding (13.6 triệu), Bahdanau (24.9 triệu, lớp output nhận $$[s_t; c_t; e_t]$$) | Luong train song song theo thời gian; Bahdanau đưa context vào chính RNN |
| Batch | xếp theo độ dài nguồn thành batch 64, xáo thứ tự batch mỗi epoch | ít padding, ổn định bộ nhớ |
| Optimizer | Adam 1e-3, clip 1.0, 8 epoch, seed 0 | đơn giản; dev BLEU của cả hai model attention đạt đỉnh ở epoch 7 rồi đi ngang, nên muốn hơn phải giảm lr dần |
| Chọn checkpoint | BLEU greedy trên `tst2012` sau mỗi epoch | không nhìn `tst2013` cho tới lần đánh giá cuối |
| Decode | beam 5 từng câu một, $$\alpha$$ chọn trên `tst2012` trong {0.6, 1.0, 1.4} | beam theo batch nhanh hơn nhưng khó viết đúng; chọn $$\alpha$$ trên test là nhìn trộm |
| Đánh giá | sacrebleu `tokenize="none"` (dữ liệu đã tách từ), chrF, chữ ký | so được với bảng khác cùng chữ ký |

Lỗi hay gặp: so BLEU với reference đã `lower()` trong khi hypothesis giữ chữ hoa (hoặc ngược lại): bản tham chiếu mất 1.7
BLEU vô lý (19.97 còn 18.30); quên `html.unescape` phía reference (mất 0.3); ghi thiếu dòng cho câu dịch rỗng (tệp lệch dòng, BLEU sụp); chọn checkpoint theo `tst2013`;
beam search không chuẩn hoá độ dài nên bản dịch ngắn bất thường (brevity penalty kéo BLEU xuống); quên `model.eval()` khi
decode (dropout làm bản dịch ngẫu nhiên).

## Kết quả tham chiếu

PC RTX 3060 12GB dùng chung với một tiến trình khác, env `setup/gpu` (torch 2.14.1+cu126), seed 0, ngày 2026-10-31. BPE:
1.14 token mỗi từ tiếng Anh, 1.02 token mỗi từ tiếng Việt; 130 700 / 133 317 cặp còn lại sau khi lọc ≤ 80 token. Chữ ký
sacrebleu `nrefs:1|case:mixed|eff:no|tok:none|smooth:exp|version:2.6.0`.

Đường cong học (dev = `tst2012`, BLEU greedy):

| Epoch | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Không attention: train loss / dev BLEU | 4.62 / 3.4 | 4.04 / 4.5 | 3.87 / 4.9 | 3.77 / 5.3 | 3.70 / 6.0 | 3.64 / 6.1 | 3.59 / 6.2 | 3.56 / 6.3 |
| Luong: train loss / dev BLEU | 4.51 / 6.3 | 3.78 / 9.1 | 3.60 / 10.5 | 3.52 / 11.0 | 3.47 / 10.5 | 3.44 / 11.6 | 3.43 / **11.8** | 3.42 / 11.7 |
| Bahdanau: train loss / dev BLEU | 4.05 / 12.2 | 3.23 / 14.1 | 2.99 / 16.0 | 2.87 / 15.4 | 2.79 / 16.3 | 2.73 / 17.5 | 2.69 / **17.7** | 2.66 / 17.1 |

Dev perplexity tốt nhất: không attention 35.3, Luong 27.7, Bahdanau 19.2. Mỗi epoch: Luong và không attention 2-4 phút,
Bahdanau 7-9 phút (lặp từng bước); 8 epoch mất tổng 44 phút (không attention), 46 phút (Luong), 67 phút (Bahdanau), có lúc GPU bị tiến trình khác chiếm.

Chọn $$\alpha$$ trên dev (beam 5, BLEU `tst2012`):

| $$\alpha$$ | 0.6 | 1.0 | 1.4 |
| --- | --- | --- | --- |
| Luong | 11.75 (BP 0.805) | 12.21 (BP 0.855) | **12.80** (BP 0.963) |
| Bahdanau | 18.47 (BP 0.908) | 18.76 (BP 0.930) | **19.03** (BP 0.960) |

`tst2013` (1 268 câu), checkpoint epoch tốt nhất theo dev, dùng một lần:

| Model | Greedy BLEU | Beam 5, $$\alpha$$ = 0.6 | Beam 5, $$\alpha$$ = 1.4 (chọn trên dev) | chrF (beam, $$\alpha$$ = 1.4) |
| --- | --- | --- | --- | --- |
| Không attention (epoch 8) | 5.59 | 5.72 (BP 0.611) | không đo | 20.9 ($$\alpha$$ = 0.6) |
| Luong (epoch 7) | 12.21 | 12.21 (BP 0.796) | 13.85 | 30.6 |
| Bahdanau (epoch 7) | 19.21 | 19.97 (BP 0.894) | **20.89** | 39.6 |

Decode cả `tst2013`: greedy theo batch dưới 3 giây, beam 5 từng câu khoảng 50 giây khi GPU rảnh (tới 3 phút khi bị chiếm).
Test chấm của bài dùng tệp beam Bahdanau $$\alpha$$ = 1.4: 20.89 ≥ 8.0.

BLEU theo độ dài câu nguồn (số từ tiếng Anh):

| Độ dài | Số câu | Không attention (greedy) | Luong (beam 1.4) | Bahdanau (greedy) | Bahdanau (beam 1.4) |
| --- | --- | --- | --- | --- | --- |
| 1-10 | 292 | 10.2 | 17.1 | 20.9 | 21.9 |
| 11-20 | 445 | 7.2 | 14.7 | 21.3 | 22.5 |
| 21-30 | 278 | 4.8 | 13.5 | 19.3 | 20.8 |
| 31-50 | 200 | 4.4 | 12.2 | 18.5 | 20.2 |
| > 50 | 53 | 3.6 | 11.3 | 15.0 | 18.3 |

Đọc kết quả:

- **Nút thắt cổ chai là có thật ở quy mô này**: không attention mất gần 2/3 BLEU khi câu dài từ dưới 10 lên trên 50 từ, Bahdanau
  chỉ mất khoảng 1/6. Khác với bài Intermediate 03 (câu ≤ 15 từ, attention chỉ hơn 1.4 BLEU).
- **Bahdanau hơn Luong rất xa** (20.9 so với 13.9), và đã hơn Luong tốt nhất ngay sau epoch 1. Nhưng đây không phải phép so
  "additive tốt hơn multiplicative": bản Luong không có input feeding nên decoder không biết đã nhìn đâu, và lớp output của
  Bahdanau nhận cả $$[s_t; c_t; e_t]$$ nên có gần gấp đôi tham số. Báo cáo tốt nêu rõ khác biệt kiến trúc, số tham số, thời
  gian mỗi epoch (Bahdanau chậm hơn 2-4 lần) và chỉ kết luận điều số đo cho phép; thử Luong có input feeding là biến thể hợp lý.
- **Chuẩn hoá độ dài quyết định beam có ích hay không**: với $$\alpha$$ = 0.6, beam của Luong không hơn greedy (12.21 cả hai)
  vì bản dịch ngắn hơn reference 20% (BP 0.796); $$\alpha$$ = 1.4 đưa BP lên 0.97 và thêm 1.6 BLEU. Precision n-gram của beam
  cao hơn greedy, cái mất là độ dài.
- Dev BLEU dao động ±0.6 giữa các epoch (Luong 11.0 → 10.5 → 11.6): chênh lệch dưới cỡ đó giữa hai cấu hình một seed chưa
  phải kết quả.
- Lỗi điển hình (beam, `tst2013`): "And I was very proud ." thành "Và tôi tự hào hứng ." ở Luong (ghép `tự hào` với `hào hứng`
  vì BPE và LM phía đích), Bahdanau dịch đúng "Và tôi rất tự hào ."; tên riêng hiếm bị BPE cắt rồi ghép bậy ("Amrok River"
  thành "Amnesrover", Luong bịa "Telambia"); từ hiếm bị thay bằng từ phổ biến sai nghĩa ("famine" thành "con bò khổng lồ");
  lặp cụm ở câu dài với Luong ("khi tôi bị ám sát bởi vì khi tôi bị ám sát..."), lặp số ("1995 vào năm 1995"). Bản dịch
  trôi chảy mà sai nghĩa là chữ ký của decoder làm language model tốt hơn phần căn chỉnh với câu nguồn.
- Heatmap attention (Luong, greedy) của "And I was very proud of my country ." gần như một-nóng và đơn điệu: "Và" nhìn
  "And", "tôi" nhìn "I", "rất tự" nhìn "was", "hào về" nhìn "proud", "đất nước ." nhìn "my" (lệch một từ, bỏ qua "very"); khác hẳn heatmap dồn vào dấu chấm cuối câu ở Intermediate 03.
- Bối cảnh: hệ attention LSTM nhiều tầng của Luong và Manning (2015) đạt khoảng 23 BLEU trên `tst2013`; model một tầng train
  1 giờ đạt 20.9 với beam. Transformer (module 05) vượt cả hai.

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
