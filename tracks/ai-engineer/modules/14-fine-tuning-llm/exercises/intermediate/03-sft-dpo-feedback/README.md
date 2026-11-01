---
title: SFT rồi DPO cho bài trích xuất phản hồi sinh viên, so với prompt
level: intermediate
services: []
files:
  - path: starter/sft_dpo.ipynb
    note: 5 hàm TODO
  - path: tests/test_sft_dpo.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py uit-vsfc
  - uv run jupyter lab tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/intermediate/03-sft-dpo-feedback/starter/sft_dpo.ipynb
  - uv run pytest tracks/ai-engineer/modules/14-fine-tuning-llm/exercises/intermediate/03-sft-dpo-feedback -q
---

## Mục tiêu

Fine-tune một model nhỏ cho một tác vụ hẹp bằng công cụ thật (TRL `SFTTrainer`, `DPOTrainer`, LoRA của PEFT), và đo nó
với đúng baseline phải đánh bại: model lớn hơn chỉ dùng prompt ở module 11. Bạn cũng dựng cặp ưu tiên tái lập được từ lỗi
của chính model, chạy DPO, và so DPO với một đối chứng công bằng.

## Đề bài

**Phần cứng:** GPU 4GB · ~120 phút

Chạy notebook bằng kernel `ai-gpu`. Thời gian trên là thời gian làm bài; notebook lời giải chạy khoảng 16 phút trên PC của
track (RTX 3060 12GB, GPU có lúc dùng chung với tiến trình khác), VRAM đỉnh khi train dưới 3 GiB (cấp phát bởi PyTorch), vừa GPU 4GB của
laptop. Lần đầu tải Qwen2.5-0.5B-Instruct khoảng 1 GB. Kernel CPU (môi trường gốc) chỉ chạy bản thu nhỏ để kiểm code chạy
hết. Đọc mục 2, 5, 6 lý thuyết và mục 5, 7 module 11 (structured output, tập ghim 150 câu).

Mở `starter/sft_dpo.ipynb`. Trong các cell chấm điểm:

1. `to_chat`, `parse_output`, `macro_f1`: định dạng hội thoại với system prompt cho sẵn, đọc output **strict** (cả
   chuỗi là đúng một object JSON hai khoá, giá trị hợp lệ) và **lenient** (object đầu tiên trong chuỗi), macro-F1 tính
   output hỏng là sai.
2. `generate_batch`: sinh greedy theo batch, cho cùng kết quả như sinh từng câu.
3. `preference_pairs`: cặp (JSON vàng, output sai của model) theo định dạng hội thoại của TRL.

Rồi chạy các cell `explore`: model gốc chỉ bằng prompt; SFT LoRA trên 8 000 câu train; dựng cặp từ lỗi của model SFT trên
3 426 câu train còn lại; DPO với hai learning rate; đối chứng "SFT thêm trên cùng 3 426 câu"; bảng tổng hợp. Sau đó
làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `to_chat` cho đúng chuỗi JSON của assistant (thứ tự khoá, `ensure_ascii=False`).
- `parse_output` phân biệt strict và lenient đúng 13 trường hợp của test (code fence, khoá thừa, khoá thiếu, viết hoa,
  giá trị ngoài danh sách, JSON hỏng).
- `macro_f1` khớp `sklearn` khi output hỏng được tính là một nhãn sai.
- `preference_pairs` chỉ tạo cặp cho câu model sai khi đọc strict, giữ nguyên output của model làm câu bị loại.
- `generate_batch` với một model tí hon: batch các câu dài khác nhau cho đúng kết quả từng câu một, đúng thứ tự.
- Các cell `explore` chạy hết và in bảng trước/sau.

## Gợi ý

### Gợi ý 1

Model decoder sinh tiếp **sau token cuối** của mỗi dòng trong batch. Nghĩ xem với batch các prompt dài ngắn khác nhau,
token cuối của dòng ngắn nằm ở đâu nếu pad bên phải, và nếu pad bên trái. `generate` trả cả prompt lẫn phần mới sinh.

### Gợi ý 2

Định dạng hội thoại của TRL cho DPO: `prompt` là danh sách message (system, user), `chosen` và `rejected` là danh sách một
message assistant. Với SFT, dạng `prompt` / `completion` tương tự cho bạn `completion_only_loss` (chỉ học phần JSON) mà
không phải tự dựng label. DPO với `peft_config` dùng chính model khi tắt adapter làm reference: merge adapter SFT vào
trọng số trước khi DPO để reference là model SFT.
