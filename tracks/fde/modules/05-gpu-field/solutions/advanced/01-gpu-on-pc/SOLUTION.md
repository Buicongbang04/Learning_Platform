# Lời giải: llama.cpp CUDA trên PC, so với CPU

Script tham chiếu ở `bench_pc.sh` cạnh tệp này. Bài tuỳ chọn; test skip khi `FDE_PC_SSH` chưa đặt:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/05-gpu-field/exercises/advanced/01-gpu-on-pc -q -rs
```

Repo **chưa chạy được** script này trên GPU thật (driver của laptop repo không nạp, xem bài basic 03), nên mọi con số GPU
dưới đây là kỳ vọng để bạn so, không phải số đã đo.

## Hướng làm

1. Kiểm từng tầng như phần 1 của README module, dưới user `fde-lab`: `nvidia-smi`, `nvidia-ctk --version`,
   `docker run --rm --gpus all ghcr.io/ggml-org/llama.cpp:server-cuda-b11718 --version`. Ghi lại driver, toolkit, Docker,
   compute capability rồi chạy `cuda_compat.py` (bài basic 01) với `cuda` = `12.8.1` (biến `CUDA_VERSION` của image).
   RTX 3060 (CC 8.6) với driver 550: `minor_version_compat`; với 570+: không vấn đề; toolkit < 1.19.1: `toolkit_cve`.
2. Script đo hai lần cùng một model, cùng cờ, chỉ khác image và `--gpus all -ngl 99`. Container mang tên bắt đầu bằng
   thư mục làm việc (`fde-ex-<run_id>`) để bộ chấm kiểm được không còn sót; `trap` dọn trên EXIT, và INT/TERM/HUP chuyển
   thành `exit` để EXIT trap chạy đúng một lần.
3. Trong lúc lần GPU chạy, `nvidia-smi` trên PC cho VRAM đã dùng. So với bài basic 02: `llm-medium` tệp 1 066 MB, KV
   `-c 4096` 112 MB, overhead CUDA vài trăm MB → kỳ vọng ~1,5–2 GB.
4. Log khởi động của server CUDA phải có dòng tìm thấy thiết bị CUDA (`ggml_cuda_init: found 1 CUDA devices`) và dòng
   offload toàn bộ lớp (`offloaded 29/29 layers to GPU` với Qwen2.5-1.5B: 28 lớp + lớp output). Thiếu các dòng này mà
   tokens/s vẫn bằng CPU là container không thấy GPU.

Kỳ vọng thô (cần bạn đo): CPU desktop 6–8 core cho `llm-medium` cỡ 20–40 tokens/s; RTX 3060 cỡ 100–200 tokens/s. Tỉ lệ
≥ 3× của test là ngưỡng thận trọng.

## Rubric tự chấm phần viết (đạt cả 4)

| # | Tiêu chí |
| --- | --- |
| P1 | Ghi đủ tổ hợp đã chạy: driver, CUDA của image, toolkit, Docker, CC; kết quả `cuda_compat.py` cho tổ hợp đó |
| P2 | Tỉ lệ GPU/CPU đo được kèm điều kiện (cờ, độ dài sinh, số lần chạy) |
| P3 | VRAM đo được so với công thức bài basic 02, giải thích chênh lệch (overhead CUDA, compute buffer) |
| P4 | Trích dòng log cho thấy GPU được dùng và số lớp được offload |
