---
title: Dữ liệu SFT, chỉ học phần trả lời, padding và packing
level: basic
services: []
files:
  - path: starter/sft_data.py
    note: 4 hàm TODO
  - path: tests/test_sft_data.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/basic/02-sft-data -q
---

## Mục tiêu

Biến một hội thoại thành đúng thứ mà vòng SFT cần: `input_ids` theo chat template của model và `labels` chỉ giữ token
của **assistant** (phần còn lại là `-100`), rồi gom nhiều mẫu thành batch bằng padding hoặc packing và đo mỗi cách lãng
phí bao nhiêu. Đây là nơi sinh ra phần lớn lỗi im lặng của SFT: model vẫn train, loss vẫn giảm, chỉ là học sai thứ.

## Đề bài

**Phần cứng:** CPU · ~60 phút

Đọc mục 2 phần lý thuyết và mục 4 (chat template) của module 09. Trong `starter/sft_data.py`:

1. `tokenize_chat(messages, tokenizer, max_length=None) -> dict | None`. Chỉ dùng hai thứ của tokenizer:
   `tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=...)` để dựng chuỗi, và
   `tokenizer(text, add_special_tokens=False)["input_ids"]` để tokenize.
   - `input_ids`: token của cả hội thoại theo template (template có thể tự chèn system mặc định: giữ nguyên).
   - `labels`: cùng độ dài; với **mỗi** lượt assistant, vị trí từ ngay sau phần prompt của lượt đó (chuỗi template của
     các message trước nó với `add_generation_prompt=True`) tới hết phần template của chính lượt đó giữ nguyên token;
     mọi vị trí khác là `-100`. **Không** tự dịch label: model của Hugging Face tự dịch khi tính loss.
   - Nếu token của phần prompt (hoặc của hội thoại tới hết lượt đó) không phải tiền tố của `input_ids` thì template
     không tách được lượt: `ValueError`.
   - `max_length`: cắt cả hai danh sách ở bên phải. Không còn token nào có label (cắt hết, hoặc không có lượt assistant)
     thì trả `None`.
2. `pad_batch(examples, pad_token_id, multiple_of=1) -> dict[str, Tensor]`: padding bên phải tới độ dài dài nhất (làm
   tròn lên bội của `multiple_of`): `input_ids` (pad bằng `pad_token_id`), `attention_mask` (1 ở token thật),
   `labels` (`-100` ở chỗ pad), đều `torch.long`.
3. `pack_examples(examples, block_size) -> list[dict]`: nối các mẫu **theo thứ tự** vào các khối không quá `block_size`
   token, không tách một mẫu ra hai khối (mẫu dài hơn `block_size` bị cắt còn `block_size` và đứng một khối riêng nếu
   khối hiện tại đã có mẫu). Mỗi khối có `input_ids`, `labels`, `position_ids` (đếm lại từ 0 ở đầu mỗi mẫu).
4. `real_token_fraction(lengths, batch_size) -> float`: chia các mẫu theo thứ tự thành batch `batch_size` mẫu (batch
   cuối có thể thiếu), padding mỗi batch tới mẫu dài nhất của nó; trả tỉ lệ token thật trên tổng token đã pad.

## Tiêu chí đạt

- Với tokenizer giả kiểu ChatML trong test: chỉ phần trả lời của assistant và token kết thúc lượt của nó có label; thẻ
  mở lượt, system mặc định, user đều là `-100`; label tại vị trí `t` bằng `input_ids[t]`.
- Hội thoại nhiều lượt: mọi lượt assistant đều có label, lượt user ở giữa thì không.
- Template không cho tiền tố ổn định thì báo lỗi thay vì gán label sai chỗ.
- Trên một Qwen2 tí hon: loss của model với batch từ `pad_batch` bằng cross-entropy tính tay chỉ trên token của assistant.
- `pack_examples` và `real_token_fraction` khớp các giá trị tính tay.

## Gợi ý

### Gợi ý 1

Cách tổng quát (không phụ thuộc thẻ đặc biệt của từng model) là so **độ dài**: tokenize phần hội thoại tới trước lượt
assistant thứ `i` kèm lời mời `assistant` của template, rồi tokenize phần tới hết lượt `i`. Hai độ dài đó chính là hai đầu
của đoạn cần học. Thử in `apply_chat_template` của vài hội thoại trong test để thấy chuỗi trông thế nào.

### Gợi ý 2

Model Hugging Face tính loss bằng cách so `logits[:, :-1]` với `labels[:, 1:]`: logits ở vị trí `t - 1` dự đoán token ở
vị trí `t`. Nếu bạn tự dịch label thêm một lần nữa, model học đoán token **sau** token kế tiếp. Với packing, đọc lại mục 2
lý thuyết: `position_ids` đếm lại từ 0 chưa đủ để các mẫu trong cùng một khối không nhìn thấy nhau.
