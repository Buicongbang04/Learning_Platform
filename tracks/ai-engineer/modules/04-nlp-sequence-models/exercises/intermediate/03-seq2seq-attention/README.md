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

Thời gian trên là thời gian làm bài. Chạy cả notebook lời giải trên CPU 4 luồng: lần đo của lời giải mất 90 phút vì CPU đang bị chia sẻ rất nặng (mỗi model đảo chuỗi 3.5-6 phút, mỗi epoch
dịch 3-35 phút); ở một lần thử khi máy nhẹ hơn, mỗi epoch dịch chỉ mất 1-1.5 phút. Kernel `ai-gpu` (GPU) nhanh
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

Attention theo batch: Bahdanau `self.W_q(query).unsqueeze(1) + self.W_k(keys)` broadcast thành `(N, S, attn_dim)`, qua
`tanh` rồi `self.v` và `squeeze(-1)`. Luong: `torch.bmm(k, query.unsqueeze(-1))`. Context: `torch.bmm(weights.unsqueeze(1),
keys).squeeze(1)`. Mask: `scores.masked_fill(~mask, float("-inf"))` rồi mới softmax. `h_n` của GRU hai chiều có shape
`(2, N, hidden)`: `h[0]` là chiều xuôi, `h[1]` chiều ngược.

### Gợi ý 2

`forward` song song cho Luong: `S, _ = self.decoder(emb(tgt_in), s0.unsqueeze(0))` ra `(N, T, H)`; score mọi bước một lần
`torch.bmm(S, self.attn.W(keys).transpose(1, 2))` shape `(N, T, S_src)`, mask `~mask.unsqueeze(1)`, softmax, `bmm` với
`keys`. Muốn chắc đúng, chạy test `forward` bằng `step`: hai đường phải ra cùng logits. Trong `step` của Bahdanau,
`nn.GRU` nhận input `(N, 1, emb + 2H)` và state `(1, N, H)`.
