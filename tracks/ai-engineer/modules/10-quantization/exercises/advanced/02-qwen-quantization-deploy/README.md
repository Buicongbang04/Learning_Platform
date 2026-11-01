---
title: Qwen2.5-0.5B, chọn cấu hình quantize cho laptop GPU 4 GB và server CPU
level: advanced
services: []
files:
  - path: starter/qwen_deploy.ipynb
    note: 4 hàm chấm, còn lại tự thiết kế
  - path: starter/REPORT.md
    note: Báo cáo khuyến nghị
  - path: tests/test_qwen_deploy.py
    note: Không sửa
run:
  - uv sync --project setup/gpu
  - ollama pull qwen2.5:0.5b-instruct-q4_K_M
  - uv run jupyter lab tracks/ai-engineer/modules/10-quantization/exercises/advanced/02-qwen-quantization-deploy/starter/qwen_deploy.ipynb
  - uv run pytest tracks/ai-engineer/modules/10-quantization/exercises/advanced/02-qwen-quantization-deploy -q
---

## Mục tiêu

Ra một quyết định triển khai có số: cùng một model (Qwen2.5-0.5B-Instruct), nên chạy bf16, bitsandbytes 8/4 bit, GPTQ tự cài
hay GGUF của llama.cpp, trên laptop GPU 4 GB và trên server chỉ có CPU. Mọi lựa chọn được đo bằng cùng một thước đo chất lượng
(bpc trên validation Wikipedia tiếng Việt), cùng cách đo bộ nhớ và tốc độ, và quyết định được rút ra bằng Pareto front chứ
không bằng cảm giác "4 bit thì nhẹ và nhanh".

## Đề bài

**Phần cứng:** GPU 4GB · ~360 phút

Thời gian trên là thời gian làm bài. Bản tham chiếu đo trên **PC RTX 3060 12GB dùng chung** với tiến trình khác (dùng dưới 4 GB
VRAM, nên chạy được như laptop 4 GB): mỗi cấu hình GPU mất khoảng 1-2 phút (nạp, đánh giá đủ validation, sinh 128 token); GPTQ
tự cài cho cả model khoảng __GPTQ_TIME__. Không có GPU: bỏ các dòng bitsandbytes (chỉ chạy trên CUDA), làm phần GGUF bằng CPU,
ghi rõ trong báo cáo.

1. Trong `starter/qwen_deploy.ipynb`, viết 4 hàm được chấm: `gguf_to_hf_name`, `load_gguf_state_dict`, `pareto_front`,
   `pick_config` (đặc tả trong notebook).
2. Đo trên GPU: bf16, fp16, bitsandbytes int8, NF4, FP4, NF4 + double quant, RTN và GPTQ int4 tự cài (chỉ chất lượng), GGUF
   (`Q8_0`, `Q4_K_M`, `Q3_K_M`) giải lượng tử bằng `load_gguf_state_dict`: bpc, bộ nhớ sau khi nạp và đỉnh khi sinh, token/giây.
3. Đo trên CPU: token/giây của các tệp GGUF (llama.cpp hoặc Ollama với `num_gpu: 0`) so với Transformers trên CPU.
4. Chọn cấu hình cho hai máy bằng `pareto_front` và `pick_config`; viết `starter/REPORT.md`; làm phần trắc nghiệm của bài trong
   app.

## Tiêu chí đạt

- 4 hàm pass mọi test.
- `REPORT.md` không còn TODO, ít nhất 600 từ, có bảng, dùng bpc, có cả CPU và GPU; hình (nếu có) phải tồn tại.
- Nội dung chấm theo rubric trong `SOLUTION.md`.

## Gợi ý

### Gợi ý 1

`BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16,
bnb_4bit_use_double_quant=...)` truyền vào `from_pretrained(..., quantization_config=..., device_map="cuda")`. Đo bộ nhớ bằng
`torch.cuda.reset_peak_memory_stats()` rồi `torch.cuda.max_memory_allocated()` quanh đúng đoạn bạn muốn đo; `nvidia-smi` cộng cả
CUDA context và bộ nhớ đệm của allocator nên luôn lớn hơn.

### Gợi ý 2

Đo tốc độ sinh: gọi `generate` một lần để khởi động, rồi đo lần sau với `min_new_tokens` bằng `max_new_tokens` để số token cố
định, `torch.cuda.synchronize()` trước khi bấm giờ. Ollama trả `eval_count` và `eval_duration` trong response: đó là tốc độ sinh
thuần, tách khỏi thời gian nạp model và xử lý prompt. Qwen2.5-0.5B dùng chung `lm_head` với embedding: GGUF chỉ có
`token_embd.weight`.
