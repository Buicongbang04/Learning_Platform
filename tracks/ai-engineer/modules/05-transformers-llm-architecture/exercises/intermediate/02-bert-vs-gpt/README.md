---
title: BERT và GPT trên cùng dữ liệu, cùng ngân sách
level: intermediate
services: []
files:
  - path: starter/bert_gpt.ipynb
    note: 6 hàm/lớp TODO
  - path: tests/test_bert_gpt.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv run jupyter lab tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/intermediate/02-bert-vs-gpt/starter/bert_gpt.ipynb
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/intermediate/02-bert-vs-gpt -q
---

## Mục tiêu

Thấy bằng số rằng BERT và GPT là **một** khối Transformer với hai lựa chọn khác nhau: mask attention và mục tiêu train. Bạn
viết masked language modeling theo công thức 80/10/10 của BERT, một `TinyTransformer` có cờ `causal`, train hai bản trên
Wikipedia tiếng Việt cùng ngân sách, rồi đo mỗi bản trên việc của bên kia: điền chỗ trống và sinh văn bản.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Notebook lời giải trên CPU 4 luồng: hai model, mỗi model 800 bước, cả notebook 11 phút (PC, máy rảnh);
kernel `ai-gpu` dùng model `n_embd` 256 và 3 000 bước mỗi model. Đọc mục 3 phần lý thuyết. Mở `starter/bert_gpt.ipynb`:

1. `mlm_mask`: chọn 15% vị trí, nhãn chỉ ở vị trí được chọn, 80% thành `[MASK]`, 10% thành token ngẫu nhiên, 10% giữ
   nguyên, mọi số ngẫu nhiên từ `generator`.
2. `attention_mask(T, causal)` theo quy ước bool của `nn.TransformerEncoderLayer` (`True` là bị cấm).
3. `TinyTransformer` (embedding token và vị trí, `nn.TransformerEncoder` pre-norm, LayerNorm cuối, head dùng chung trọng số
   với embedding), `lm_loss`, `mlm_loss`, `masked_accuracy`.

Rồi chạy các cell `explore`: train GPT và BERT cùng kiến trúc và ngân sách; điền 15% vị trí bị che trên validation; ví dụ
"Hà Nội là thủ [MASK] của nước Việt Nam."; thử sinh văn bản bằng cả hai. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `mlm_mask` chọn khoảng 15% vị trí, đúng tỉ lệ 80/10/10, không sửa input, tái lập theo `generator`.
- `attention_mask` đúng quy ước; `TinyTransformer` nhân quả khi `causal=True` (đổi token 8 không ảnh hưởng vị trí 0..7) và hai
  chiều khi `causal=False`, có position embedding, weight tying, pre-norm.
- `lm_loss` dịch một vị trí, `mlm_loss` chỉ tính vị trí có nhãn, `masked_accuracy` chỉ đếm vị trí có nhãn.
- Một `TinyTransformer` hai chiều học được điền chỗ trống trong chuỗi có quy luật sau 150 bước.

## Gợi ý

### Gợi ý 1

Làm `mlm_mask` bằng các mặt nạ bool cùng shape với `ids`: một mặt nạ "được chọn", một tensor số ngẫu nhiên thứ hai để chia
80/10/10, một tensor token ngẫu nhiên; ghép bằng phép `&` và gán theo mặt nạ trên một bản `clone()`. Giá trị `-100` trùng
`ignore_index` mặc định của `F.cross_entropy`.

### Gợi ý 2

`nn.TransformerEncoder(layer, n_layer)` chép `layer` thành `n_layer` bản độc lập; truyền mask qua tham số `mask` của
`forward`. Để so công bằng ở phần thí nghiệm, GPT đoán token ở vị trí $$i$$ bằng logits ở vị trí $$i - 1$$ (dịch logits sang phải
một vị trí), còn BERT đoán ngay tại vị trí bị thay bằng `[MASK]`.
