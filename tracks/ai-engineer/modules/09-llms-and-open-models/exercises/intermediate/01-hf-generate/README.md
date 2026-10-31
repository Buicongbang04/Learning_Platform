---
title: Tự viết vòng sinh token và KV cache với Qwen2.5-0.5B
level: intermediate
services: []
files:
  - path: starter/generate.ipynb
    note: 5 hàm TODO
  - path: tests/test_generate.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv run jupyter lab tracks/ai-engineer/modules/09-llms-and-open-models/exercises/intermediate/01-hf-generate/starter/generate.ipynb
  - uv run pytest tracks/ai-engineer/modules/09-llms-and-open-models/exercises/intermediate/01-hf-generate -q
---

## Mục tiêu

Mở `model.generate()` của Hugging Face ra: tự viết vòng sinh token trên logits, tự quản lý KV cache qua
`past_key_values`, đo cái giá của việc không có cache, thấy temperature đổi độ đa dạng thế nào, và đo một con số
quyết định chi phí của mọi ứng dụng tiếng Việt: một câu tiếng Việt tốn bao nhiêu token so với cùng câu tiếng Anh
qua từng tokenizer.

## Đề bài

**Phần cứng:** CPU · ~75 phút

Ngoài thời gian làm bài: lần đầu tải `Qwen/Qwen2.5-0.5B-Instruct` khoảng 1 GB và tokenizer Phi-3 vài MB. Chạy hết
notebook lời giải trên laptop của track mất khoảng 15 phút khi máy đang bận (vòng không cache chiếm nhiều nhất),
model chạy float32 trên CPU, 4 luồng, khoảng 2 GB RAM. Không cần GPU, không cần Ollama.

Mở `starter/generate.ipynb`. Trong cell chấm điểm:

1. `decode(next_logits, prompt_ids, max_new_tokens, pick, eos_ids)`: vòng sinh token tách khỏi model, test bằng
   logits giả.
2. `hf_next_logits(model)`: mỗi bước chạy model trên **cả chuỗi**, trả logits vị trí cuối.
3. `cached_next_logits(model)`: dùng `past_key_values`, chỉ đưa token mới vào model khi chuỗi nối tiếp chuỗi cũ,
   chạy lại từ đầu khi gặp chuỗi khác.
4. `fertility(count_tokens, texts)`: token trên mỗi từ.
5. `distinct_n(texts, n)`: tỉ lệ n-gram khác nhau, đo độ đa dạng.

Rồi chạy các cell `explore`: chat template của Qwen và phân phối token đầu tiên, greedy bằng 4 cách (vòng của bạn
không cache và có cache, `model.generate` mặc định và tắt penalty) kèm token/s, thời gian một bước ở chuỗi 64,
256, 1 024 token, distinct-n ở 4 mức temperature, và fertility của 4 tokenizer trên 1 268 cặp câu IWSLT15 tst2013.
Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `decode`: đưa đúng cả chuỗi mỗi bước, `pick` nhận các token đã sinh trước bước đó, dừng sau eos (eos có trong
  kết quả), trả `int` Python, không sửa prompt.
- `hf_next_logits`: một lần gọi model với cả chuỗi, tensor `long` shape `(1, n)`, trong `no_grad`, trả `float32`
  của vị trí cuối.
- `cached_next_logits`: kết quả trùng bản không cache; sau lần đầu mỗi bước chỉ đưa token mới với
  `past_key_values` của lần trước; chạy lại từ đầu khi chuỗi không nối tiếp.
- `fertility`, `distinct_n` khớp giá trị tính tay (n-gram không nối qua hai văn bản).
- Cell `explore` chạy hết; vòng greedy có cache của bạn cho đúng chuỗi token của `model.generate(...,
  repetition_penalty=1.0)`.

## Gợi ý

### Gợi ý 1

Hai hàm bọc model là closure: biến `seen` (chuỗi đã xử lý) và `past` sống giữa các lần gọi, sửa bằng `nonlocal`.
Model Hugging Face nhận `model(input_ids=..., past_key_values=..., use_cache=True)` và trả object có `.logits` shape
`(1, số token đưa vào, vocab)` và `.past_key_values`. Logits cần lấy luôn là `[0, -1]`.

### Gợi ý 2

Khi `cached` lệch với không cache: kiểm điều kiện "nối tiếp" (`ids[:len(seen)] == seen` **và** dài hơn), và nhớ
gán `seen = ids` sau mỗi lần gọi. Khi vòng greedy của bạn không khớp `model.generate()` mặc định, đừng sửa vòng của
bạn: in `model.generation_config` và đọc kỹ từng tham số mà `generate` tự áp.
