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
| kagglehub | >= 0.3 (1.0.2) | để notebook chạy bằng kernel `ai-gpu` import được `data.download_dataset` (`ex.dataset`, `ensure`) |
| gymnasium[classic-control,box2d] / ale-py / imageio[ffmpeg] | 1.4.0 / 0.12.1 / 2.38.1 | RL trên GPU (Atari) và quay video, module 07 |
| onnxruntime-gpu / onnx | 1.29.0 (bản CUDA 12) / 1.23.2 | serving DL track MLOps (module 11); thêm 2026-11-03, xem mục bên dưới |

Phiên bản chính xác đã khóa trong `uv.lock`.

## Cài và kiểm tra

```bash
unset VIRTUAL_ENV
uv sync --project setup/gpu                      # tải ~3GB+ lần đầu
uv run --project setup/gpu python setup/gpu/check_gpu.py
```

Env này dùng Python do uv quản lý (`python-preference = "only-managed"` trong `pyproject.toml`), vì
Triton (`torch.compile`, một số kernel backward trên GPU) phải biên dịch module C và cần `Python.h`;
Python hệ thống thường thiếu header này nếu chưa cài `python3.12-dev`. Lần sync đầu uv tự tải Python
3.12. Env cũ tạo từ Python hệ thống: xoá `setup/gpu/.venv` rồi sync lại.

`check_gpu.py` in tên GPU, VRAM, phiên bản CUDA/torch và chạy matmul fp16; thoát mã khác 0 nếu
không thấy GPU.

## ONNX Runtime GPU (thêm 2026-11-03)

- `onnxruntime-gpu` trên PyPI từ 1.28 build cho **CUDA 13** (cần driver >= 580). Trên laptop driver 550,
  bản 1.31.0 của PyPI báo `CUDA failure 35: CUDA driver version is insufficient for CUDA runtime version` rồi
  âm thầm chạy CPU. Vì vậy env này lấy bản **CUDA 12** từ feed chính thức `onnxruntime-cuda-12`
  (Azure DevOps của ONNX Runtime); bản CUDA 12 mới nhất ở đó là **1.29.0** (PyPI 1.29.0 phát hành 2026-08-17),
  nên lệch với `onnxruntime==1.31.0` CPU của env gốc. Bản 1.31.0 chỉ có CUDA 12 dưới dạng "CUDA plugin EP"
  (tarball 440 MB, không có trên pip), không dùng.
- `onnxruntime` CPU (faster-whisper kéo theo) bị gỡ bằng `override-dependencies`: hai gói cùng ghi thư mục
  `onnxruntime/`, cài cả hai thì gói nào cài sau sẽ đè gói kia. `faster-whisper` vẫn import được (`onnxruntime-gpu` có đủ CPU EP).
- onnxruntime-gpu 1.29.0 build bằng CUDA 12.8+, gọi `cudaLibraryGetKernel` (có từ libcudart 12.8). torch cu126 ghim
  `nvidia-cuda-runtime-cu12==12.6.77` nên ORT báo `undefined symbol: cudaLibraryGetKernel` và rơi về CPU. Env này
  override `nvidia-cuda-runtime-cu12==12.9.79` (cùng major 12; driver 550 chạy được nhờ CUDA minor version
  compatibility). Đã kiểm: `check_gpu.py`, conv + autocast fp16 + backward của torch, và ORT
  `InferenceSession(..., providers=["CUDAExecutionProvider", ...]).get_providers()[0] == "CUDAExecutionProvider"`.
- Gọi `onnxruntime.preload_dlls()` trước khi tạo session để ORT nạp cuDNN/cuBLAS từ các wheel `nvidia-*` của torch.
- Luôn kiểm `session.get_providers()[0]`: `get_available_providers()` chỉ liệt kê EP được build sẵn, kể cả khi thư viện CUDA không nạp được.

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
