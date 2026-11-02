---
title: Speculative decoding - draft, verify, prompt lookup và đo tăng tốc thật
level: intermediate
services: []
files:
  - path: starter/speculative.ipynb
    note: 3 hàm TODO
  - path: tests/test_speculative.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py zalo-legal
  - uv run jupyter lab tracks/ai-engineer/modules/20-evaluation-production/exercises/intermediate/03-speculative-decoding/starter/speculative.ipynb
  - uv run pytest tracks/ai-engineer/modules/20-evaluation-production/exercises/intermediate/03-speculative-decoding -q
---

## Mục tiêu

Cài speculative decoding greedy trên một giao diện model có KV cache: một hàm đoán đề xuất vài token, model chính kiểm cả
khối trong một forward, nhận phần khớp, sửa token sai, cắt cache. Output phải trùng từng token với greedy; bạn đo tỉ lệ
nhận, số forward tiết kiệm được và tăng tốc thật trên CPU, với prompt lookup và (mở rộng) một model nháp.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Thời gian trên là thời gian làm bài. Phần đo dùng `Qwen/Qwen2.5-0.5B-Instruct` (khoảng 1 GB, tự tải vào cache Hugging Face
ở lần chạy đầu), float32, CPU 4 luồng, khoảng 4 phút trên PC của track. Cell mở rộng (Qwen2.5-0.5B đoán cho Qwen2.5-3B)
cần thêm khoảng 6 GB tải về, khoảng 14 GB RAM và 5 phút; chỉ chạy khi đặt `M20_DRAFT_3B=1`.

Mở `starter/speculative.ipynb`, viết các cell chấm điểm theo mô tả trong notebook:

1. `greedy_generate(lm, prompt_ids, max_new_tokens, eos_id=None)`: một `reset` rồi mỗi token một `extend`.
2. `prompt_lookup_draft(context, k, max_ngram=3)`: token đứng sau lần xuất hiện gần cuối nhất của n-gram đuôi.
3. `speculative_generate(target, draft, prompt_ids, k, max_new_tokens, eos_id=None)`: kết quả và `stats`
   (`target_calls`, `rounds`, `proposed`, `accepted`, `acceptance_rate`).

Rồi chạy các cell `explore`: harness Hugging Face (`DynamicCache`), 8 tác vụ (chép nguyên văn và giải thích tự do trên 4
điều luật Zalo) với greedy và prompt lookup $$k = 4, 8$$. Trả lời các câu ở cuối notebook, rồi làm phần trắc nghiệm của bài
trong app.

## Tiêu chí đạt

- `greedy_generate` trùng greedy tham chiếu, đúng một lần gọi model mỗi token, dừng đúng ở `eos_id` và `max_new_tokens`.
- `prompt_lookup_draft` đúng 8 ví dụ (gần cuối nhất, ưu tiên n-gram dài, ngắn hơn `k`, không khớp, ngữ cảnh ngắn).
- `speculative_generate` trùng greedy của target với 4 loại hàm đoán (đoán đúng hết, đoán sai hết, model khác, prompt
  lookup) ở nhiều `k`; đếm đúng `stats` trong các ca có đáp án tính tay; không xin đoán quá số token còn lại; cắt bỏ khối đoán
  dài; dừng khi nhận `eos_id` nằm trong khối đoán; trạng thái target không giữ token bị từ chối.
- Notebook lời giải chạy hết và in bảng tăng tốc.

## Gợi ý

### Gợi ý 1

Viết ra giấy một lượt với $$k = 3$$: trạng thái target trước lượt, khối gửi kiểm, dòng logits nào dự đoán cho vị trí nào, và
trạng thái sau khi nhận $$a$$ token. Token kế tiếp là argmax của dòng $$a$$, và nó **chưa** nằm trong trạng thái target.

### Gợi ý 2

Model giả trong test tính logits từ hai token cuối của **trạng thái** của nó, giống KV cache thật: quên cắt trạng thái sau
một lượt đoán sai thì lượt sau dự đoán từ token đã bị từ chối, và output lệch khỏi greedy. Test "đoán sai hết" là cách
nhanh nhất để thấy điều đó.
