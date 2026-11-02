---
title: Đếm token tiếng Việt và tiếng Anh trên IWSLT'15 với 3 tokenizer
level: intermediate
services: []
files:
  - path: starter/tokens.ipynb
    note: 5 hàm TODO
  - path: tests/test_tokens.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py iwslt15-en-vi
  - uv run jupyter lab tracks/ai-engineer/modules/00-introduction/exercises/intermediate/01-token-counting/starter/tokens.ipynb
  - uv run pytest tracks/ai-engineer/modules/00-introduction/exercises/intermediate/01-token-counting -q
---

## Mục tiêu

Đo bằng số thật câu "tiếng Việt tốn bao nhiêu token": cùng 1 268 câu đã dịch, bản tiếng Việt tốn bao nhiêu token so
với bản tiếng Anh dưới ba tokenizer khác thế hệ, và dùng con số đó để quản lý ngân sách context. Làm xong bạn biết vì
sao không được so giá API chỉ bằng "USD mỗi triệu token".

## Đề bài

**Phần cứng:** CPU · ~50 phút

Các cell `explore` chạy khoảng 20 giây; lần đầu cần mạng để tải tokenizer (`tiktoken` và `tokenizer.json` của Qwen2.5,
tổng khoảng 15 MB).

Dữ liệu là tập test `tst2013` của IWSLT'15 Anh–Việt (1 268 cặp câu phụ đề TED, một câu mỗi dòng, đã tách từ kiểu
Moses). Đọc mục 3 và mục 5 lý thuyết trước. Mở `starter/tokens.ipynb`; trong các cell chấm điểm viết:

1. `detokenize(line) -> str`: đưa câu đã tách từ về dạng tự nhiên theo đúng 5 bước trong notebook (giải HTML entity,
   bỏ khoảng trắng quanh dấu câu, nối `can 't` thành `can't`, gộp khoảng trắng).
2. `token_stats(texts, encode) -> dict`: tổng ký tự, từ, token và hai tỉ lệ `tokens_per_word`, `chars_per_token`.
   `encode` là bất kỳ hàm `str -> list` nào: `list` (ký tự), `str.split` (từ), `tiktoken...encode`.
3. `token_tax(src_texts, tgt_texts, encode) -> float`: tổng token bản dịch chia tổng token bản gốc (tỉ lệ của tổng,
   không phải trung bình tỉ lệ từng cặp).
4. `fits_in_context(n_prompt, max_new_tokens, context_window) -> bool`.
5. `truncate_to_budget(texts, encode, budget) -> list[str]`: tiền tố dài nhất của `texts` có tổng token không vượt
   ngân sách; dừng ở đoạn đầu tiên làm vượt.

Rồi chạy các cell `explore`: bảng 6 cách đếm (ký tự, byte, từ, `cl100k_base`, `o200k_base`, Qwen2.5), các mảnh token
của một câu, histogram tỉ lệ Việt/Anh theo từng cặp câu, và số câu vừa ngân sách 3 000 token. Trả lời các câu ở cuối
notebook, sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `detokenize` đúng mọi ví dụ trong test, kể cả `&#91; 2 &#93;` thành `[2]` và giữ `' tự` của tiếng Việt.
- `token_stats`, `token_tax` khớp tính tay với encoder byte UTF-8; `token_tax` báo `ValueError` khi hai danh sách lệch
  độ dài hoặc bản gốc không có token.
- `truncate_to_budget` lấy đúng bằng ngân sách, không nhảy qua đoạn dài để nhét đoạn ngắn phía sau.
- Test dữ liệu thật (tự skip nếu chưa tải): sau `detokenize`, bản Anh có 123 769 ký tự và 23 093 từ, bản Việt 133 496
  ký tự và 30 809 từ, tỉ lệ byte UTF-8 Việt/Anh 1.443.
- Cell `explore` chạy hết và in bảng 6 cách đếm.

## Gợi ý

### Gợi ý 1

`html.unescape` lo bước 1. Bước 2 và 3 mỗi bước một `re.sub` với một lớp ký tự trong `[...]` (nhớ escape `]` và `[`
trong lớp ký tự). Bước 4 cần **lookahead** `(?=...)` để kiểm ký tự sau dấu nháy mà không "ăn" nó. Bước 5:
`" ".join(s.split())`.

### Gợi ý 2

Trong `token_stats`, để ý mẫu số bằng 0 (danh sách rỗng, chuỗi chỉ có khoảng trắng). `str.split()` không đối số tách
theo mọi loại khoảng trắng và bỏ phần rỗng, khác với `split(" ")`. `truncate_to_budget` chỉ cần một biến cộng dồn và
`break`.
