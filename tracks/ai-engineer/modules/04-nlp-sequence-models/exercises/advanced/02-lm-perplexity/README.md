---
title: Language model LSTM tiếng Việt, byte vs BPE, bits-per-character (portfolio)
level: advanced
services: []
files:
  - path: starter/lm.ipynb
    note: 4 hàm chấm, còn lại tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_lm.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv sync --project setup/gpu
  - uv run jupyter lab tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/advanced/02-lm-perplexity/starter/lm.ipynb
  - uv run pytest tracks/ai-engineer/modules/04-nlp-sequence-models/exercises/advanced/02-lm-perplexity -q
---

## Mục tiêu

Train language model LSTM trên Wikipedia tiếng Việt với ba cách tokenize (byte, BPE 2 000, BPE 8 000), đo perplexity theo
token và bits-per-character, sinh văn bản với temperature và top-k. Câu hỏi trung tâm: perplexity của hai tokenizer có so
được không, và nếu không thì so bằng gì. Kết quả là baseline mà GPT mini của module 05 phải vượt qua trên cùng dữ liệu.

## Đề bài

**Phần cứng:** GPU 4GB · ~300 phút

Thời gian trên là thời gian làm bài. Thời gian máy của bản tham chiếu: ba model, mỗi model 3 000 bước, tổng khoảng 31 phút trên RTX 3050 4GB dùng chung với tiến trình khác (8-14
phút mỗi model). **Không có GPU:** dùng 200 bài, LSTM
1 tầng 256, 1 000 bước; kết luận về bpc vẫn kiểm được, số tuyệt đối kém hơn.

1. Trong `starter/lm.ipynb`, viết 4 hàm được chấm: `batchify`, `get_batch` (truncated BPTT), `nll_to_metrics` (perplexity,
   bit mỗi token, bpc), `sample_next` (temperature, top-k).
2. Dựng thí nghiệm (bố cục gợi ý trong notebook): 1 000 bài dài lấy ngẫu nhiên làm train, 100 bài khác làm validation;
   ba tokenizer; cùng một kiến trúc LSTM và **cùng số bước** train cho mọi tokenizer; chuyền hidden state giữa các đoạn
   BPTT (`detach`).
3. Đánh giá trên validation bằng tổng NLL → `nll_to_metrics`. Lập bảng: vocab, ký tự mỗi token, số tham số, perplexity theo
   token, bpc, thời gian. Sinh văn bản từ "Hà Nội là" với vài temperature và top-k.
4. Viết `starter/REPORT.md`, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `batchify` chia đoạn liên tục, bỏ phần dư; `get_batch` dịch một vị trí, đoạn cuối ngắn hơn; `nll_to_metrics` đúng ba
  đại lượng (bpc độc lập tokenizer); `sample_next` đúng argmax, top-k, temperature, chỉ dùng `generator` truyền vào.
- `REPORT.md` không còn TODO, ít nhất 500 từ, có bảng, dùng bpc; hình (nếu có) phải tồn tại.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Validation đánh giá trên **cả** chuỗi liên tục (batch 1, chuyền state qua các đoạn), cộng `cross_entropy(..., reduction="sum")`
mọi đoạn: đó là tổng NLL. Số token dự đoán là độ dài chuỗi trừ 1; số ký tự là `len(văn bản validation)`. Byte-level có
khoảng 0.8 ký tự mỗi token (chữ có dấu 2-3 byte), BPE 8 000 khoảng 3.5.

### Gợi ý 2

Cùng số bước nghĩa là model byte thấy ít văn bản hơn nhiều (mỗi bước 128 byte so với 128 token BPE): ghi rõ trong báo cáo
và, nếu còn thời gian, chạy thêm một cấu hình cùng **số ký tự** đã thấy. `tokenizers` ByteLevel BPE: `pre_tokenizers.ByteLevel`,
`decoders.ByteLevel`, `initial_alphabet=pre_tokenizers.ByteLevel.alphabet()` để không bao giờ có token lạ.
