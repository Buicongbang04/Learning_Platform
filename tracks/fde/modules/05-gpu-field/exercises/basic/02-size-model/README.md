---
title: Định cỡ LLM theo VRAM và RAM
level: basic
services: []
files:
  - path: starter/size_model.py
    note: Hàm size_model, bạn viết
  - path: models.yaml
    note: Kiến trúc thật của 7 model (config.json trên Hugging Face), không sửa
  - path: tests/test_size_model.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/05-gpu-field/exercises/basic/02-size-model -q
---

## Mục tiêu

Khách hỏi "GPU 12 GB của em chạy được model nào, cho mấy người, context bao dài". Trả lời trong vài phút bằng một phép
tính có công thức rõ ràng, trước khi bỏ công đo, và biết con số nào là của trọng số, con số nào là của context và người
dùng đồng thời.

## Đề bài

`models.yaml` có 7 model thật (Qwen2.5 0.5B → 72B, Mistral 7B v0.3), mỗi model có `params_b` (tỉ tham số), `n_layers`,
`n_heads`, `n_kv_heads`, `hidden_size`, `ctx_train` (context tối đa khi huấn luyện), lấy từ `config.json` và model card.

Viết `starter/size_model.py`, hàm:

```python
size_model(model: dict, *, ctx: int, memory_mb: float, batch: int = 1, bits_per_weight: float | None = None,
           file_bytes: int | None = None, kv_bytes: float = 2.0, overhead_mb: float = 512.0) -> dict
```

Công thức (1 MB = 1 048 576 byte):

| Đại lượng | Công thức |
| --- | --- |
| `weights_mb` | `file_bytes / 1048576` nếu có `file_bytes`, không thì `params_b × 10⁹ × bits_per_weight / 8 / 1048576` |
| `head_dim` | `hidden_size // n_heads` |
| `kv_mb` | `2 × n_layers × n_kv_heads × head_dim × ctx × batch × kv_bytes / 1048576` |
| `total_mb` | `weights_mb + kv_mb + overhead_mb` |
| `fits` | `total_mb ≤ memory_mb` |
| `max_ctx` | Bội số lớn nhất của 256, ≤ `ctx_train`, mà `weights_mb + kv_mb(ctx = max_ctx) + overhead_mb ≤ memory_mb` (cùng `batch`, `kv_bytes`); không có bội số nào thoả thì `0` |

Trả dict có đúng năm khoá trên (`weights_mb`, `kv_mb`, `total_mb` là số, sai số cho phép 0,5 MB; `fits` là `bool`;
`max_ctx` là `int`). `ValueError` khi: không có hoặc có cả hai `bits_per_weight` và `file_bytes`; `ctx` < 1 hoặc
> `ctx_train`; `batch` < 1.

`memory_mb` là VRAM của GPU khi chạy GPU, hoặc RAM **trống** khi chạy CPU. `batch` là số chuỗi chạy song song (số người
hỏi cùng lúc). `kv_bytes` là 2 với KV f16, ~1,06 với q8_0.

## Tiêu chí đạt

- `test_cases`: 15 tình huống (Qwen2.5-7B Q4_K_M theo kích thước tệp thật trên RTX 3060, 32B trên 24 GB với KV f16 và
  q8_0, 72B trên 24/48 GB và 2× 80 GB, `llm-medium` trên máy `factory`…): đúng cả năm khoá.
- `test_random`: 300 bộ tham số sinh ngẫu nhiên mỗi lần chạy.
- `test_bad_input`: năm kiểu đầu vào sai đều `ValueError`.

## Gợi ý

### Gợi ý 1

Model nào trong `models.yaml` có `n_kv_heads` khác `n_heads`? Thay `n_kv_heads` bằng `n_heads` thì KV lớn lên bao nhiêu
lần?

### Gợi ý 2

`max_ctx` có thể tính thẳng từ chỗ còn trống chia cho KV của một token, nhưng nhớ hai điều kiện còn lại: bội số của 256 và
không quá `ctx_train`. Tính xong thì kiểm lại đúng bất đẳng thức, số thực có thể làm bạn lệch một bậc.

### Gợi ý 3

So `weights_mb` tính từ `bits_per_weight=4` với kích thước tệp Q4_K_M thật của Qwen2.5-7B trong test. Con số nào bạn sẽ
đưa khách?
