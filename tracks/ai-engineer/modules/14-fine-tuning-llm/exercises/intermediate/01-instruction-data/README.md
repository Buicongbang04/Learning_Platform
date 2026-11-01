---
title: Làm sạch, khử trùng lặp và chia bộ instruction tiếng Việt
level: intermediate
services: []
files:
  - path: starter/instruction_data.ipynb
    note: 8 hàm TODO
  - path: tests/test_instruction_data.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py openorca-viet
  - uv run jupyter lab tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/intermediate/01-instruction-data/starter/instruction_data.ipynb
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/intermediate/01-instruction-data -q
---

## Mục tiêu

Làm phần việc chiếm nhiều thời gian nhất của một dự án fine-tune: biến một bộ instruction tải về thành dữ liệu SFT tin
được. Bạn đọc giấy phép, chuẩn hoá, đưa về định dạng hội thoại, khử trùng lặp chính xác và gần đúng bằng MinHash + LSH,
lọc theo độ dài token, chia train/validation theo nhóm, và đo nhiễm bẩn n-gram. Kết quả là hai tệp mà bài 02 dùng để SFT.

## Đề bài

**Phần cứng:** CPU · ~120 phút

Ngoài thời gian làm bài: notebook lời giải chạy khoảng 7 phút trên PC của track (CPU 4 luồng, máy dùng chung), trong đó
MinHash cho khoảng 121 nghìn mẫu mất gần 4 phút (chữ ký được cache, chạy lại nhanh). Lần đầu tải bộ dữ liệu khoảng 290 MB
và tokenizer của Qwen2.5 vài MB. Đọc mục 5 phần lý thuyết.

Mở `starter/instruction_data.ipynb`. Trong các cell chấm điểm, viết theo đặc tả trong notebook:

1. `normalize_text`, `to_messages`: chuẩn hoá NFC và khoảng trắng; đưa `instruction`, `input`, `output` về danh sách
   message, bỏ system prompt hỏng.
2. `dedup_key`, `exact_dedup`: khoá trùng lặp không phụ thuộc system prompt, hoa thường, khoảng trắng.
3. `minhash_signature`, `near_duplicate_groups`: MinHash trên shingle 5 ký tự, LSH theo band có kiểm ngưỡng, gộp nhóm bắc cầu.
4. `group_split`, `contamination`: chia theo nhóm bằng hash, tỉ lệ word 13-gram của mẫu đánh giá có mặt trong train.

Rồi chạy các cell `explore` theo thứ tự: chúng in lỗi dữ liệu thật, đếm sau từng bước, so chia ngẫu nhiên với chia theo
nhóm, đo nhiễm bẩn, và ghi `data/raw/openorca-viet/cache/m14-train.jsonl` (10 000 mẫu) cùng `m14-val.jsonl`. Sau đó làm
phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `normalize_text` đưa NFD về NFC, gộp khoảng trắng ngang (cả tab và NBSP), giữ một dòng trống giữa hai đoạn.
- `to_messages` bỏ system prompt chỉ là dấu câu hoặc quá ngắn; nội dung mọi message đã chuẩn hoá.
- `dedup_key` giống nhau khi chỉ khác system prompt, hoa thường hoặc khoảng trắng; khớp SHA-1 của định dạng đặc tả.
- `minhash_signature` khớp từng thành phần với đặc tả; tỉ lệ thành phần bằng nhau xấp xỉ Jaccard thật (sai dưới 0.08 với
  256 hàm hash).
- `near_duplicate_groups` chỉ nối khi qua ngưỡng, gộp bắc cầu, mã nhóm là chỉ số nhỏ nhất.
- `group_split` giữ cùng nhóm cùng phía, không phụ thuộc thứ tự, tỉ lệ validation gần `val_frac`.
- `contamination` khớp giá trị tính tay, không ghép n-gram qua hai văn bản train, chuẩn hoá NFC.
- Các cell `explore` chạy hết và ghi hai tệp cho bài 02.

## Gợi ý

### Gợi ý 1

Đọc kỹ ký tự nào Python coi là khoảng trắng: `str.split()` không tham số tách theo nhiều ký tự hơn bạn nghĩ, kể cả vài ký
tự điều khiển. Với MinHash, mỗi thành phần của chữ ký là giá trị nhỏ nhất của một hàm hash trên **tập** shingle; hai văn
bản có chung thành phần thứ `k` khi phần tử nhỏ nhất theo hàm thứ `k` nằm trong phần giao của hai tập.

### Gợi ý 2

Tính cả ma trận `num_perm × số shingle` một lần bằng numpy (`np.outer` rồi `% P`, `min` theo trục 1) thay vì vòng lặp
Python: với `uint64`, `a·h + b` không tràn vì cả ba nhỏ hơn $$2^{31}$$. Union-find cần hai thứ: `find` có nén đường đi, và
khi nối thì để gốc nhỏ hơn làm cha, nên gốc của mỗi nhóm luôn là chỉ số nhỏ nhất.
