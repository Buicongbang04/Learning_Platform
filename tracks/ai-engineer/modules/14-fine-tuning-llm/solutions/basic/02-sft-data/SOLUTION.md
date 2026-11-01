# Lời giải: dữ liệu SFT, chỉ học phần trả lời, padding và packing

## Cách làm

**`tokenize_chat`.** Dựng chuỗi của cả hội thoại bằng `apply_chat_template(..., tokenize=False)` rồi tokenize một lần
(`add_special_tokens=False`, vì template đã chứa mọi thẻ cần thiết; thêm BOS lần nữa là lỗi kinh điển với Llama). Với
lượt assistant thứ `i`:

- `prompt` = token của `messages[:i]` với `add_generation_prompt=True`: kết thúc đúng ở `<|im_start|>assistant\n`.
- `upto` = token của `messages[:i+1]`: kết thúc sau `<|im_end|>\n` của lượt đó.
- Đoạn `[len(prompt), len(upto))` là phần model phải học: nội dung trả lời **và** token kết thúc lượt. Học token kết thúc
  là cách model biết **dừng**; bỏ nó thì model fine-tune xong sinh tiếp mãi.

Kiểm `ids[:len(prompt)] == prompt` vì cách này chỉ đúng khi template "cộng dồn": hội thoại dài hơn có tiền tố là chuỗi
của hội thoại ngắn hơn. Đa số template (ChatML của Qwen2.5, Llama 3) thoả; template xoá nội dung lượt trước (ví dụ bỏ
phần suy luận của lượt cũ ở một số model reasoning) thì không, và lúc đó phải báo lỗi thay vì gán label lệch. Một lựa
chọn khác là `return_assistant_tokens_mask=True` của Transformers, nhưng nó chỉ chạy với template có thẻ
`{% generation %}`, mà template của Qwen2.5 không có.

**Không dịch label.** Model causal LM của Hugging Face tự so `logits[:, :-1]` với `labels[:, 1:]`. `labels[t] = input_ids[t]`
ở vị trí cần học là đúng; tự dịch thêm làm model học đoán token cách hai bước. Test so loss của model với cross-entropy
tính tay để bắt lỗi này.

**`pad_batch`.** Pad bên phải khi train (bên trái chỉ cần khi **sinh** theo batch, bài Intermediate 03). Label ở chỗ pad
là `-100`, không phải `pad_token_id`: với Qwen2.5, `pad_token` là `<|endoftext|>`, một token thật; để nó trong label là
dạy model sinh hàng loạt `<|endoftext|>`.

**`pack_examples`.** Nối tham lam theo thứ tự, mở khối mới khi mẫu kế tiếp không vừa. `position_ids` đếm lại từ 0 cho
mỗi mẫu để RoPE thấy đúng vị trí. Nhưng như mục 2 lý thuyết đo: với attention `sdpa` hay `eager`, `position_ids` **không**
chặn mẫu sau nhìn thấy mẫu trước trong cùng khối; chỉ kernel varlen (FlashAttention, `padding_free` của TRL) hoặc mask
khối chéo mới chặn. Token đầu tiên của mẫu sau được dự đoán từ token cuối của mẫu trước, nhưng token đó thuộc system
hoặc user nên đã là `-100`.

**`real_token_fraction`.** Cộng token thật và `max × số mẫu` của từng batch theo thứ tự. Bài Intermediate 02 dùng nó để
thấy batch theo ngân sách token (xếp theo độ dài) bớt padding thế nào.

## Bẫy thường gặp

- Học cả prompt (`labels = input_ids`): loss trông thấp hơn (prompt dài, dễ đoán), model học bắt chước câu hỏi và system
  prompt. Với dữ liệu ngắn kiểu phân loại, phần trả lời chỉ vài phần trăm số token, nên loss toàn chuỗi gần như không
  phản ánh thứ bạn muốn dạy.
- Chỉ học lượt assistant cuối của hội thoại nhiều lượt: phí dữ liệu, và model không học trả lời ở giữa hội thoại.
- Tự viết lại template bằng f-string thay vì dùng template của tokenizer: lệch một dấu xuống dòng là lệch với lúc serve.
- Tokenize từng message rồi nối: BPE cắt khác khi văn bản đứng cạnh nhau, và thiếu thẻ của template.
