# setup/gpu — môi trường CUDA cho bài train nặng

Env uv riêng (`ai-gpu`) cho các bài fine-tune / QLoRA của track AI Engineer. Tách khỏi env gốc
vì env gốc dùng torch **CPU** (`pytorch-cpu`), còn ở đây dùng torch **CUDA 12.6** (`cu126`).

## Phiên bản (kiểm ngày 2026-10-29)

| Gói | Phiên bản | Ghi chú |
|---|---|---|
| torch / torchvision | 2.14.1 / 0.29.1 (`+cu126`) | khớp env gốc; cu130 mới hơn nhưng cần driver >= 580, laptop driver 550 |
| transformers | >= 5.22 (PyPI mới nhất 5.22.0) | |
| accelerate | >= 1.15 (1.15.0) | |
| peft | >= 0.21 (0.21.2) | |
| trl | >= 1.17 (1.17.0) | |
| bitsandbytes | >= 0.50 (0.50.2) | lượng tử hóa 4-bit cho QLoRA |
| datasets | >= 5.1 (5.1.0) | |

Phiên bản chính xác đã khóa trong `uv.lock`.

## Cài và kiểm tra

```bash
unset VIRTUAL_ENV
uv sync --project setup/gpu                      # tải ~3GB+ lần đầu
uv run --project setup/gpu python setup/gpu/check_gpu.py
```

`check_gpu.py` in tên GPU, VRAM, phiên bản CUDA/torch và chạy matmul fp16; thoát mã khác 0 nếu
không thấy GPU.

## Chạy notebook bằng kernel của env này

```bash
uv run --project setup/gpu python -m ipykernel install --user --name ai-gpu
```

Rồi chọn kernel `ai-gpu` trong Jupyter/VS Code cho các bài cần GPU.

## Hai máy, cùng repo

| Máy | GPU | Dùng cho |
|---|---|---|
| Laptop | RTX 3050 Laptop 4GB | thử nhanh, model nhỏ, inference; QLoRA chỉ model rất nhỏ |
| PC | RTX 3060 12GB, RAM 128GB | train thật (QLoRA 7B), chạy Ollama |

Hai máy dùng chung repo: sửa ở máy nào thì commit/push, máy kia `git pull`, rồi `uv sync --project setup/gpu`.
(PC chưa kiểm tra từ môi trường phát triển; chạy `check_gpu.py` trên PC lần đầu để xác nhận.)

## Dùng Ollama trên PC từ laptop

Trên PC, cho Ollama nghe mọi interface rồi khởi động lại:

```bash
OLLAMA_HOST=0.0.0.0 ollama serve
```

Trên laptop, trỏ client về PC:

```bash
export OLLAMA_HOST=http://<ip-PC>:11434
```

`llmkit.py` đọc biến này (xem docstring đầu `llmkit.py`); bảng biến môi trường ở
[`../SETUP.md`](../SETUP.md).

## Giai đoạn 3: thư viện thêm và vLLM

`diffusers`, `ultralytics`, `opencv-python-headless`, `tokenizers`, `tiktoken`, `faster-whisper`, `gguf` cùng phiên bản với env gốc (ghim `==`). Phụ thuộc gián tiếp phát hành sau 2026-10-16 bị chặn bằng `constraint-dependencies` (bỏ khi đủ 2 tuần).

**vLLM không cài được** cùng env này: `vllm==0.31.0` đòi `transformers<5.18`, trong khi env cần `transformers>=5.22`. Module 20 (serving) dùng `llama.cpp` server / Ollama trên laptop; vLLM chỉ nên thử trong env riêng trên PC (driver mới) và ghi là cell không chấm.
