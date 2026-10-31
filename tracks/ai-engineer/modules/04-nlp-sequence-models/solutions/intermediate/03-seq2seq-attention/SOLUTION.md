# Lời giải: seq2seq với attention Bahdanau và Luong

## Cách làm

**Attention.** Cả hai lớp cùng khung: tính score `(N, S)`, `masked_fill(~mask, -inf)`, softmax theo trục nguồn, context
bằng `bmm(weights.unsqueeze(1), keys)`. Khác nhau ở score:

| | Score theo batch | Tham số |
| --- | --- | --- |
| Bahdanau | `v(tanh(W_q(q).unsqueeze(1) + W_k(keys))).squeeze(-1)` | `W_q`, `W_k`, `v`, không bias |
| Luong dot | `bmm(keys, q.unsqueeze(-1)).squeeze(-1)` | không có |
| Luong general | `bmm(W(keys), q.unsqueeze(-1)).squeeze(-1)` | `W: enc_dim → dec_dim` |

Gán `-inf` **trước** softmax nên trọng số padding đúng bằng 0 và gradient không chảy vào padding. Câu nào cũng có ít nhất
một token thật nên không có hàng toàn `-inf` (sẽ ra NaN).

**Seq2Seq.** Encoder: embedding → dropout → BiGRU trên chuỗi đã pack, `pad_packed_sequence(total_length=S)` để `keys`
có đúng `S` cột như `mask`; `s0 = tanh(bridge([h[0]; h[1]]))`. Decoder theo đúng thứ tự từng paper:

| `attn` | Bước decoder | `forward` khi teacher forcing |
| --- | --- | --- |
| `none` | GRU($$e_t$$) → $$W_o s_t$$ | GRU chạy cả chuỗi một lần |
| `bahdanau` | attn($$s_{t-1}$$) → GRU($$[e_t; c_t]$$) → $$W_o[s_t; c_t; e_t]$$ | lặp `step` |
| `luong` | GRU($$e_t$$) → attn($$s_t$$) → $$W_o \tanh(W_c[s_t; c_t])$$ | GRU cả chuỗi, score mọi bước bằng một `bmm` `(N, T, S)` |

Test "forward bằng step lần lượt" bắt mọi chỗ lệch giữa hai đường (quên mask khi tính song song, nhầm thứ tự nối
$$[s; c]$$, dùng `keys` thay vì `W(keys)`).

**Decode.** `greedy_decode` cộng dồn cờ `done |= y == EOS` và dừng khi mọi câu đã xong; cắt mỗi câu trước `<eos>` đầu tiên.
`corpus_bleu` gọi sacrebleu với `tokenize="none"` vì IWSLT đã tách từ (sacrebleu in cảnh báo "forgot to detokenize", có thể
bỏ qua hoặc truyền `force=True`).

## Kết quả thật

CPU 4 luồng, seed 0, chạy lại ngày 2026-10-31 trên PC (CPU dùng chung, load trung bình 20-30): cả notebook mất 44 phút, trong
đó hai epoch cuối của model Luong mỗi epoch gần 20 phút vì máy bận; khi máy rảnh mỗi epoch dịch khoảng 1 phút, bài đảo chuỗi
40-90 giây mỗi model.

| Bài đảo chuỗi (dài 5-20, hidden 32, 1 500 bước) | Đúng nguyên chuỗi |
| --- | --- |
| Không attention | 0.108 |
| Luong general | 0.992 |
| Bahdanau | 1.000 |

| Dịch Anh-Việt (46 311 cặp ≤ 15 từ, vocab 4 000, emb 64, hidden 128, 3 epoch) | Train PPL epoch 1 / 2 / 3 | BLEU 378 câu tst2013 |
| --- | --- | --- |
| Không attention | 167.0 / 75.0 / 55.9 | 3.25 |
| Luong general | 190.3 / 79.8 / 55.8 | 4.63 |

Tỉ lệ `<unk>` phía tiếng Việt: 1.2% token. Đọc kết quả:

- Bài đảo chuỗi cho thấy nút thắt rõ nhất có thể: thông tin cần (vị trí đối xứng) nằm ở một chỗ cụ thể của nguồn, attention
  học được đường chéo ngược gần hoàn hảo, còn một vector 32 chiều không chứa nổi 20 ký hiệu.
- Trên dịch thật ở quy mô này, attention chỉ hơn 1.4 BLEU (lần chạy trên laptop cùng seed: Luong 4.15, tức hơn 0.9; model
  không attention ra đúng 3.25 trên cả hai máy). Chênh lệch giữa hai máy cỡ nửa BLEU là nhiễu số học, không phải kết quả.
  Heatmap của "i was very proud of my country ." cho thấy mọi bước sinh dồn trọng số vào dấu chấm cuối câu: model chưa học căn chỉnh, dùng attention như một vector tóm tắt. Bản dịch
  "và tôi rất rất nhiều ." vừa sai nghĩa vừa lặp từ (exposure bias). Muốn attention có ích cần nhiều dữ liệu, model lớn hơn,
  nhiều epoch: bản tham chiếu của bài Advanced 01 (GPU, BPE, toàn bộ dữ liệu) có heatmap căn chỉnh gần như từng từ.
- Luong song song hoá được khi teacher forcing nên mỗi epoch nhanh như model không attention; Bahdanau lặp từng bước, chậm
  hơn vài lần mỗi epoch, nhưng đưa context vào chính RNN nên học nhanh hơn theo epoch (số đo ở bài Advanced 01).

## Bẫy thường gặp

- Nhân mask sau softmax: trọng số không còn tổng 1, test so công thức fail.
- Không pack encoder: `keys` ở vị trí padding khác 0, state cuối của câu ngắn đã đọc padding.
- `pad_packed_sequence` thiếu `total_length`: `keys` có ít cột hơn `mask` khi câu dài nhất batch có padding phía sau.
- Bahdanau dùng $$s_t$$ thay vì $$s_{t-1}$$ (thành một biến thể khác); Luong dùng $$s_{t-1}$$ thì mất khả năng song song.
- `done = y == EOS` thay vì cộng dồn: vòng lặp không dừng sớm khi các câu xong ở các bước khác nhau.
