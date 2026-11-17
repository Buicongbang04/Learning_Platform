# Lời giải: định cỡ LLM theo VRAM và RAM

Lời giải ở `size_model.py` cạnh tệp này:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/05-gpu-field/exercises/basic/02-size-model -q
```

## Cách làm

- `weights_mb` từ kích thước tệp khi có tệp, từ `params × bpw / 8` khi chưa. Đúng một trong hai, không thì `ValueError`.
- `kv_mb` dùng `n_kv_heads` và `head_dim = hidden_size // n_heads`. Qwen2.5-7B có 28 head nhưng 4 KV head (GQA): dùng
  `n_heads` thì KV lớn gấp 7.
- `max_ctx`: tính nhanh `(memory − weights − overhead) / kv_một_token`, làm tròn xuống bội 256, kẹp ở `ctx_train`, rồi
  **kiểm lại đúng bất đẳng thức** và chỉnh một bậc lên/xuống: chia số thực có thể lệch đúng ở biên.

## Đọc các tình huống trong test

| Tình huống | Kết quả | Câu nói với khách |
| --- | --- | --- |
| Qwen2.5-7B Q4_K_M (tệp 4 466 MB) trên RTX 3060 12 GB | 4 người × 32k vẫn vừa (12 146 MB) | 7B Q4 là lựa chọn tự nhiên cho 3060; giới hạn là tốc độ khi nhiều người, không phải bộ nhớ |
| Qwen2.5-7B FP16 trên 12 GB | Không vừa, `max_ctx` 0 | Trọng số 14,5 GB: cần quantize hoặc GPU 24 GB |
| Qwen2.5-32B ~4.85 bpw trên 24 GB | Vừa ở 8k, tối đa ~21k | Muốn 32k thì KV q8_0 (23,7 GB), chấp nhận giảm nhẹ chất lượng |
| Qwen2.5-72B ~4.85 bpw | 24 GB không vừa ngay cả trọng số; 48 GB vừa | Đừng hứa 72B trên một card 24 GB |
| `llm-medium` (tệp thật) với RAM trống 1 400 MB | Không vừa (1 690 MB) | Công thức coi trọng số là bộ nhớ chiếm hẳn; trên CPU với `mmap` thì trọng số là page cache, chiếm ít `MemAvailable` hơn (bài intermediate 01 đo ~0,7× tệp). Công thức là cận trên an toàn, không phải số đo |

Công thức là **ước lượng trước khi đo**: overhead thật phụ thuộc runtime (CUDA context, compute buffer theo batch xử lý
prompt, `CPU_REPACK` của llama.cpp trên CPU). Đo trên `factory`: `llm-medium` RSS đỉnh ~1,6–1,75 GB với `-c 4096`, tức
overhead thực ~500–600 MB, khớp với mặc định 512 MB. Luôn đo lại trên máy khách trước khi ký số.
