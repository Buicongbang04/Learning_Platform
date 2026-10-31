---
title: GPT mini tiếng Việt từ số 0 (portfolio)
level: advanced
services: []
files:
  - path: starter/gpt_vi.ipynb
    note: 3 hàm chấm, còn lại tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo portfolio
  - path: tests/test_gpt_vi.py
    note: Không sửa
run:
  - uv run python data/download_dataset.py wikipedia-vi
  - uv sync --project setup/gpu
  - uv run jupyter lab tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/advanced/01-gpt-mini-vietnamese/starter/gpt_vi.ipynb
  - uv run pytest tracks/ai-engineer/modules/05-transformers-llm-architecture/exercises/advanced/01-gpt-mini-vietnamese -q
---

## Mục tiêu

Pretrain từ số 0 một GPT tiếng Việt trên toàn bộ bài Wikipedia dài của hai shard đã tải, bằng lớp `GPT` bài Basic 01 và vòng
train bài Intermediate 01, rồi đóng gói thành một checkpoint tự chứa và một báo cáo portfolio. Câu hỏi trung tâm: với một GPU cá
nhân và vài chục phút, một Transformer nhỏ đi được bao xa so với LSTM của module 04, và văn bản nó sinh ra tốt tới đâu. Checkpoint
này là đầu vào của module 08 (interpretability) và module 10 (quantization).

## Đề bài

**Phần cứng:** GPU 12GB (PC) · ~480 phút

Thời gian trên là thời gian làm bài. Thời gian máy của bản tham chiếu, đo trên **PC RTX 3060 12GB** (GPU dùng chung với một
tiến trình khác): cấu hình PC (6 tầng, `n_embd` 384, context 256, 13.8 triệu tham số, 8 000 bước batch 64, 131 triệu token)
17.6 phút, 3.0 GB VRAM; cấu hình laptop (4 tầng, `n_embd` 256, context 256, 5.3 triệu tham số, 6 000 bước batch 32, 49 triệu
token) 5.3 phút, 1.6 GB VRAM. **Laptop GPU 4GB:** dùng cấu hình laptop (vừa bộ nhớ, chậm hơn vài lần, chưa đo lại). **Không có
GPU:** cấu hình của bài Intermediate 01 bản CPU trên 2 000 bài, kết luận vẫn kiểm được, số tuyệt đối kém hơn.

1. Trong `starter/gpt_vi.ipynb`, viết 3 hàm được chấm: `save_checkpoint`, `load_checkpoint` (định dạng `gpt-mini-v1`, đặc tả
   trong notebook) và `distinct_n`.
2. Dữ liệu: validation là đúng 100 bài của module 04; train là mọi bài dài (≥ 2 000 ký tự) còn lại của hai shard
   `train-00001` và `train-00002` (14 473 bài, 95.5 triệu ký tự). Tokenizer BPE byte-level 8 000 train trên 1 000 bài
   train của module 04 (để bpc so được với LSTM và với bài Intermediate 01), hoặc tokenizer của bạn nếu ghi rõ lý do.
3. Train `GPT` của bài Basic 01 với cấu hình hợp phần cứng; đánh giá định kỳ bằng `evaluate_nll` (cửa sổ trượt stride bằng nửa
   context), lưu checkpoint tốt nhất bằng `save_checkpoint`.
4. Báo cáo bpc so với LSTM module 04 (1.975) và GPT mini bài Intermediate 01; mẫu sinh từ cùng câu mở đầu với vài temperature
   và top-k, `distinct_n`; nạp lại checkpoint bằng `load_checkpoint` và kiểm cho cùng bpc.
5. Viết `starter/REPORT.md`, rồi làm phần trắc nghiệm của bài trong app.

## Tiêu chí đạt

- `save_checkpoint` lưu đúng khoá và định dạng; `load_checkpoint` dựng lại model cho cùng output, ở chế độ eval, giữ weight
  tying, trả tokenizer cho cùng token id, từ chối định dạng khác; `distinct_n` đúng.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng, dùng bpc; hình (nếu có) phải tồn tại.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

Encode 96 triệu ký tự bằng `tokenizer.encode_batch` theo từng bài rồi nối, lưu mảng `uint16` ra đĩa (`np.save`) để không phải
encode lại mỗi lần chạy notebook. Lấy batch ngẫu nhiên từ mảng này như bài Intermediate 01. Nối bài bằng token của `"\n\n"`.

### Gợi ý 2

Trên GPU Ampere, `torch.autocast("cuda", dtype=torch.bfloat16)` gần gấp đôi tốc độ không cần loss scaling; `torch.compile`
nhanh thêm khoảng 20-30% sau một phút biên dịch (đặt `TORCHINDUCTOR_COMPILE_THREADS` nhỏ nếu máy dùng chung). Thiếu VRAM thì
giảm batch và dùng gradient accumulation (module 02). Lưu checkpoint bằng `model.state_dict()` của model **gốc**, không phải
của bản `torch.compile` (khoá có tiền tố `_orig_mod.`).
