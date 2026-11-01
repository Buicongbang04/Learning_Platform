---
title: Rejection sampling và SFT - model tự học từ lời giải đúng của chính nó
level: intermediate
services: []
files:
  - path: starter/rft.ipynb
    note: 4 hàm TODO, dán reward từ Basic 01
  - path: tests/test_rft.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py gsm8k
  - uv run jupyter lab tracks/ai-engineer/modules/15-reasoning-models/exercises/intermediate/03-rejection-sampling-sft/starter/rft.ipynb
  - uv run pytest tracks/ai-engineer/modules/15-reasoning-models/exercises/intermediate/03-rejection-sampling-sft -q
---

## Mục tiêu

Dựng một pipeline synthetic data cho reasoning ở dạng đơn giản nhất: model sinh nhiều lời giải, verifier (reward của
bài Basic 01) giữ lời giải đúng, khử trùng lặp, kiểm nhiễm bẩn với tập đo, rồi SFT chính model đó (rejection sampling
fine-tuning, họ hàng của STaR). Bạn đo được nó mang lại gì và giới hạn của nó: model chỉ học được từ những câu nó đã tự
giải được.

## Đề bài

**Phần cứng:** GPU 4GB · ~90 phút

Thời gian trên là thời gian làm bài. Máy chạy riêng: sinh 3 200 lời giải, SFT 2 epoch và hai lần đo 500 câu; số phút
đo trên PC của track ghi ở `SOLUTION.md`. Kernel CPU chạy bản thu nhỏ (6 câu) để kiểm code. Chạy bằng kernel `ai-gpu`.
Đọc mục 6 lý thuyết, và mục 2, 5 module 14 (SFT chỉ tính loss trên phần trả lời, chuẩn bị dữ liệu).

Mở `starter/rft.ipynb`:

1. Dán `normalize_number`, `extract_answer`, `format_reward`, `correctness_reward` (cùng regex, hàm phụ) từ Basic 01.
2. `select_traces(samples, gold, max_keep=2)`: giữ lời giải đúng cả đáp số và khung, bỏ trùng (sau khi gộp khoảng
   trắng), ngắn trước, tối đa `max_keep`.
3. `word_ngrams(text, n)` và `contaminated(train_questions, eval_questions, n=13)`: chỉ số câu train có chung một n-gram
   từ với tập đo.
4. `to_sft_record(question, trace, system)`: mẫu prompt-completion hội thoại cho TRL.

Rồi chạy các cell `explore`: kiểm nhiễm bẩn (8-gram và 13-gram), sinh 4 lời giải cho mỗi câu trong 800 câu train, lọc,
SFT LoRA bằng TRL, đo trước/sau trên 500 câu test ghim. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `select_traces` lọc đúng (sai đáp số, sai khung, không có hộp bị bỏ), bỏ trùng theo khoảng trắng và giữ bản đầu
  nguyên văn, xếp ngắn trước, ổn định khi bằng độ dài.
- `word_ngrams` chữ thường, bỏ dấu câu; `contaminated` đúng trên ví dụ (13-gram chỉ bắt câu chép lại, 6-gram bắt cả cụm từ
  chung), và trên GSM8K thật: 0 câu train trùng 13-gram với 500 câu test ghim.
- `to_sft_record` đúng cấu trúc TRL.
- Các cell `explore` chạy hết và in bảng thống kê lọc cùng bảng trước/sau.

## Gợi ý

### Gợi ý 1

Thứ tự "ngắn trước, bằng nhau giữ thứ tự xuất hiện" là một tính chất mà sort của Python có sẵn (sort ổn định). Nghĩ xem
nên khử trùng trước hay sau khi sắp xếp để giữ đúng "bản xuất hiện đầu".

### Gợi ý 2

Gộp mọi n-gram của tập đo vào **một** `set` trước, rồi với mỗi câu train chỉ cần một phép giao tập hợp. Với 7 473 câu train
và 500 câu đo, cách này chạy dưới một giây; so từng cặp câu thì chậm hơn hàng nghìn lần.
