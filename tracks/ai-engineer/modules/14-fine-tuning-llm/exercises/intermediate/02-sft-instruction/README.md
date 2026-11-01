---
title: Vòng SFT viết tay với LoRA cho Qwen2.5-0.5B trên instruction tiếng Việt
level: intermediate
services: []
files:
  - path: starter/sft_instruction.ipynb
    note: 4 hàm TODO, 2 hàm dán từ Basic 02
  - path: tests/test_sft_instruction.py
    note: Không sửa
run:
  - uv run jupyter lab tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/intermediate/02-sft-instruction/starter/sft_instruction.ipynb
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/intermediate/02-sft-instruction -q
---

## Mục tiêu

Chạy một vòng SFT viết tay (không dùng `Trainer`, cho sẵn trong notebook) và tự viết các hàm dữ liệu, đo mà nó dùng, để
thấy từng mảnh: dữ liệu theo chat template và label của bài Basic
02, batch theo ngân sách token, LoRA của PEFT với gradient checkpointing, warmup rồi cosine, rồi đo **trước và sau** bằng
loss trên tập validation chia theo nhóm và exact-match câu trắc nghiệm. Cuối bài so model 0.5B đã fine-tune với model 3B
không fine-tune để trả lời câu hỏi: thứ model thiếu là hành vi hay năng lực?

## Đề bài

**Phần cứng:** GPU 4GB · ~120 phút

Chạy notebook bằng kernel `ai-gpu`. Thời gian trên là thời gian làm bài; notebook lời giải chạy khoảng 12 phút trên PC của
track (RTX 3060 12GB), VRAM đỉnh khi train dưới 3 GiB (cấp phát bởi PyTorch, ngân sách 1 024 token mỗi batch). Cell so với Qwen2.5-3B-Instruct (bf16, khoảng 6 GB trọng số) chỉ
chạy khi GPU trống trên 8 GiB, tức trên PC; laptop 4GB tự bỏ qua cell đó và dùng số trong lời giải. Kernel CPU (môi trường gốc) chỉ chạy bản thu nhỏ khoảng 5 phút
để kiểm code. Cần hai tệp do bài 01 ghi ra: làm bài 01 trước. Đọc mục 2, 3, 7 lý thuyết.

Mở `starter/sft_instruction.ipynb`:

1. **Dán** `tokenize_chat`, `pad_batch` từ bài Basic 02.
2. `token_budget_batches`: batch theo độ dài với ngân sách token, trộn thứ tự batch theo seed.
3. `heldout_nll`: NLL trung bình **theo token** trên các token có label, ở chế độ eval, không gradient.
4. `normalize_answer`, `is_short_answer`, `exact_match`: chọn câu trắc nghiệm có đáp án ngắn nằm trong câu hỏi, so đáp án
   sau chuẩn hoá.

Rồi chạy các cell `explore`: chọn 4 000 câu train, 300 câu validation cho loss, 200 câu trắc nghiệm (cả hai lấy từ phần
validation chia theo nhóm của bài 01, không trùng nhau); đo model gốc; train 1 epoch LoRA r = 16 trên mọi lớp tuyến tính;
đo lại; so với 3B. Sau đó làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- Hai hàm dán từ Basic 02 qua kiểm tra nhanh.
- `token_budget_batches`: mỗi mẫu đúng một lần, không batch nào vượt ngân sách (trừ mẫu đứng một mình), gom tham lam theo
  độ dài, sort ổn định, seed đổi thứ tự batch.
- `heldout_nll` khớp NLL tính tay theo token tới `1e-5`, khác trung bình các loss batch, đặt model về eval.
- `normalize_answer`, `exact_match`, `is_short_answer` khớp các ví dụ của test (NFC, dấu câu, giới hạn độ dài).
- Các cell `explore` chạy hết và in bảng trước/sau.

## Gợi ý

### Gợi ý 1

Ngân sách token so với **kích thước sau khi pad** của batch, không với tổng độ dài thật. Sort theo độ dài trước thì mẫu
dài ngắn gần nhau đi cùng batch, pad ít; trộn thứ tự batch sau đó để model không thấy mọi mẫu ngắn trước rồi mọi mẫu dài
sau (loss sẽ đi theo độ dài chứ không theo học).

### Gợi ý 2

`model(**batch).loss` của Hugging Face đã là trung bình trên token có label **của batch đó**. Cộng nó qua các batch rồi chia
số batch là trung bình của trung bình: batch ít token nặng ký bằng batch nhiều token. Tự tính cross-entropy với
`reduction="sum"` trên logits dịch một vị trí, đếm token, rồi chia ở cuối.
