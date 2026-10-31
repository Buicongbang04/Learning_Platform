# Lời giải: BERT và GPT trên cùng dữ liệu, cùng ngân sách

## Các hàm

| Hàm | Cài đặt | Điểm dễ sai |
| --- | --- | --- |
| `mlm_mask` | `selected = rand < p`; `labels = where(selected, ids, -100)`; một tensor `rand` thứ hai chia 80/10/10; token ngẫu nhiên `randint(vocab_size)`; gán trên `ids.clone()` | thay mọi vị trí chọn bằng `[MASK]` (bỏ 10/10); dùng RNG toàn cục; sửa `ids` tại chỗ |
| `attention_mask` | nhân quả: `ones(T, T).triu(1)` (True = cấm); hai chiều: toàn False | `tril()` là quy ước ngược (True = được nhìn) của một số thư viện khác |
| `TinyTransformer` | `tok_emb + pos_emb`, `nn.TransformerEncoder(layer, n_layer)` với `mask=attention_mask(T, causal)`, `ln_f`, `head.weight = tok_emb.weight` | quên truyền mask: "GPT" nhìn trộm tương lai, loss train rất thấp, sinh văn bản hỏng |
| `lm_loss` | `cross_entropy(logits[:, :-1], ids[:, 1:])` | không dịch: model học chép token hiện tại |
| `mlm_loss` | `cross_entropy(..., ignore_index=-100)` | |
| `masked_accuracy` | argmax đúng trên vị trí `labels != -100` | chia cho mọi vị trí |

Khi `causal=True`, `TinyTransformer` chính là GPT; khi `False`, là BERT (không có next-sentence prediction, giống RoBERTa). Không
có dòng code nào khác giữa hai model ngoài mask và loss.

## Kết quả của notebook lời giải

Cùng 1 000 bài train, BPE 8 000 thêm `[MASK]` (vocab 8 001), context 128, batch 32, AdamW 1e-3, warmup 100 bước + cosine.
Validation: 1 491 cửa sổ 128 token; cách 1 che 28 233 vị trí (15%) cùng lúc, cách 2 che một vị trí mỗi lần, 8 vị trí mỗi cửa sổ
(11 928 lần).

| Cấu hình | Model | Loss train cuối | Cách 1: che 15% cùng lúc | Cách 2: một chỗ trống mỗi lần |
| --- | --- | --- | --- | --- |
| CPU: `n_embd` 128, 800 bước (1.83 triệu tham số) | GPT | 5.849 | 0.105 | 0.104 |
| | BERT | 6.834 | 0.043 | 0.041 |
| GPU: `n_embd` 256, 3 000 bước (5.24 triệu tham số) | GPT | 3.743 | 0.239 | 0.238 |
| | BERT | 4.375 | 0.221 | 0.245 |

(CPU 4 luồng: cả notebook 11 phút; GPU: PC RTX 3060, cả notebook 6 phút.)

Với ví dụ "Hà Nội là thủ [MASK] của nước Việt Nam.", bản GPU: BERT đoán `thủ, bóng, quân, địch, cầu`, GPT (chỉ thấy "Hà Nội là
thủ") đoán `lĩnh, tướng, đô, phủ, môn`; không model nào đặt "đô" lên đầu. Sinh greedy từ "Hà Nội là": GPT ra "Hà Nội là một trong
những người nổi tiếng nhất của Trung Quốc. / Năm 2013, ông được trao tặng Huân chương ..."; BERT ra "Hà Nội là gọi là tên là tên là
tên là tiếng tiếng tiếng ...".

Đọc kết quả:

- Giả thuyết "BERT điền chỗ trống giỏi hơn vì nhìn hai phía" **chỉ đúng một phần** ở ngân sách này: khi mọi token khác thật
  (cách 2), BERT bản GPU hơn GPT 0.007, một chênh lệch nhỏ cỡ nhiễu; khi 15% token khác cũng bị che, BERT thua. Bản CPU 800 bước
  thì BERT gần như chưa học (accuracy 0.04 là mức đoán token phổ biến).
- Lý do là hiệu quả dữ liệu: cùng 3 000 bước, BERT chỉ nhận loss trên khoảng 15% token, tức khoảng 1.8 triệu dự đoán so với 12.3
  triệu của GPT. BERT gốc train 1 triệu bước với batch 256; ELECTRA (2020) sinh ra chính để sửa sự lãng phí này (học trên mọi
  token bằng nhiệm vụ "token này có bị thay không").
- Sinh văn bản thì không có tranh cãi: BERT không được train cho việc đó.
- Bài học kỹ sư: một giả thuyết hợp lý vẫn phải đo; và so hai mục tiêu train phải nói rõ ngân sách (bước, token, tín hiệu train).

## Bẫy thường gặp

- So loss train của hai model: khác nhiệm vụ (đoán 15% token bị che so với đoán mọi token kế), không so được.
- Đánh giá GPT trên chỗ trống bằng logits **tại** vị trí bị che: logits ở vị trí $$i$$ của GPT dự đoán token $$i + 1$$; phải lấy
  logits ở $$i - 1$$.
- Quên rằng BERT thấy `[MASK]` ở mọi chỗ cần đoán khi train nhưng khi dùng thật không có `[MASK]`: đó là lý do của 10% token
  ngẫu nhiên và 10% giữ nguyên.
