---
title: Seq2seq với attention Bahdanau và Luong, dịch Anh-Việt
level: intermediate
services: []
files:
  - path: starter/seq2seq.ipynb
    note: 9 hàm/lớp TODO
  - path: tests/test_seq2seq.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv run jupyter lab tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/intermediate/03-seq2seq-attention/starter/seq2seq.ipynb
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/intermediate/03-seq2seq-attention -q
---

## Mục tiêu

Tự viết attention Bahdanau (additive) và Luong (multiplicative), ghép vào một seq2seq GRU có ba chế độ (không attention,
Bahdanau, Luong), decode greedy, đo BLEU bằng sacrebleu. Làm xong bạn thấy bằng số nút thắt cổ chai của seq2seq thuần, hiểu
vì sao thứ tự "attention trước hay sau bước RNN" quyết định có train song song được không, và đọc được ma trận attention.

## Đề bài

**Phần cứng:** CPU · ~150 phút

Thời gian trên là thời gian làm bài. Thời gian máy của notebook lời giải trên CPU 4 luồng: khi máy rảnh mỗi model đảo chuỗi
40-90 giây và mỗi epoch dịch khoảng 1 phút (tổng chừng 10 phút); lần đo trên PC đang bị chiếm (load 20-30) mất 44 phút vì
có epoch kéo dài tới 20 phút. Kernel `ai-gpu` (GPU) nhanh
hơn nhiều nhưng không bắt buộc.

Mở `starter/seq2seq.ipynb`, làm theo đặc tả trên từng cell (quy ước shape: batch trước, `mask` là `True` ở token thật):

1. `BahdanauAttention` (lớp `W_q`, `W_k`, `v` không bias) và `LuongAttention` (`"dot"`, `"general"` với `W`): trả
   `(context, weights)`, padding có trọng số đúng bằng 0.
2. `Seq2Seq(src_vocab, tgt_vocab, emb, hidden, attn, dropout)` với `encode`, `step`, `forward` theo bảng trong notebook:
   encoder BiGRU có packing, `self.bridge` cho state đầu, decoder theo đúng thứ tự của từng paper; `forward` cho `"none"` và
   `"luong"` chạy GRU decoder cả chuỗi một lần.
3. `greedy_decode` (dừng khi mọi câu đã sinh `<eos>`), `corpus_bleu` (sacrebleu, `tokenize="none"`).
4. `read_parallel`, `build_vocab`, `encode` cho IWSLT'15.

Rồi chạy các cell `explore`: bài đảo chuỗi dài tới 20 với ba chế độ, heatmap attention; dịch Anh-Việt câu ≤ 15 từ với
`none` và `luong`, 3 epoch; vài bản dịch và heatmap của một câu. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Hai attention khớp công thức tính tay (`atol=1e-6`), padding có trọng số và gradient bằng 0, Luong `"dot"` từ chối số
  chiều lệch.
- Với cả ba chế độ: `forward` (teacher forcing) bằng việc gọi `step` lần lượt ở chế độ eval; `s0` đúng định nghĩa; encoder
  không đọc padding.
- Bahdanau tính attention từ $$s_{t-1}$$ (không phụ thuộc token vừa đọc), Luong từ $$s_t$$.
- `greedy_decode` cắt trước `<eos>` và dừng ngay khi mọi câu đã xong (đếm số lần gọi `step`).
- Học được bài đảo chuỗi dài tới 8 (≥ 80% chuỗi đúng hoàn toàn) trong 250 bước.
- `corpus_bleu` đúng `tokenize="none"`; IWSLT thật: `tst2013` có 1 268 cặp, 378 cặp cả hai phía ≤ 15 từ.
- Cell `explore` in số giống mục 6 lý thuyết (máy khác có thể lệch nhẹ).

## Gợi ý

### Gợi ý 1

Viết attention cho cả batch bằng broadcasting và `bmm`, không lặp theo câu: với Bahdanau, query `(N, ·)` cần thêm một trục
để cộng được với keys `(N, S, ·)`; với Luong, score là một tích theo batch. Context cũng là một `bmm` của trọng số với
keys. Mask áp **trước** softmax (mục 6 lý thuyết). Kiểm shape của `h_n` của GRU hai chiều: chiều xuôi và chiều ngược nằm ở
chỉ số nào?

### Gợi ý 2

Với Luong, decoder GRU không cần context nên chạy được cả `tgt_in` một lần; score cho mọi cặp (bước đích, vị trí nguồn) khi
đó là một `bmm` ra shape `(N, T, S_src)`, và mask phải thêm một trục để broadcast. Dùng test "forward bằng step" làm thước
đo: hai đường phải cho cùng logits, lệch là có chỗ nối sai thứ tự hoặc quên mask. Với Bahdanau, kiểm kích thước input của
GRU decoder (embedding nối với context) và state ban đầu có shape `(1, N, H)`.
