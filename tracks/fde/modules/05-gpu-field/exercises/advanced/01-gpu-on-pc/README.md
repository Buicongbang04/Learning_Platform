---
title: "Tuỳ chọn: llama.cpp CUDA trên PC có GPU, so với CPU"
level: advanced
services: []
files:
  - path: starter/bench_pc.sh
    note: Script đo CPU và GPU trên PC, bạn viết
  - path: tests/test_pc_gpu.py
    note: Không sửa; tự skip khi chưa đặt FDE_PC_SSH
run:
  - uv run pytest tracks/fde/modules/05-gpu-field/exercises/advanced/01-gpu-on-pc -q -rs
---

## Mục tiêu

Mọi bài khác của module chạy bằng CPU. Bài này (tuỳ chọn, cần PC có GPU NVIDIA của bạn, ví dụ RTX 3060 12 GB) đi trọn
chuỗi driver → toolkit → image CUDA trên một máy thật mà bạn **không** có quyền root khi làm bài, đo cùng một model trên
CPU và trên GPU, và tự tay thấy các con số trong phần 2 và 4 của README module.

## Đề bài

**Chuẩn bị PC một lần (bạn tự làm bằng quyền admin của PC, ngoài bộ chấm):**

1. Làm theo mục "PC GPU" của [setup/fde/README.md](../../../../../../../setup/fde/README.md): OpenSSH server, user
   `fde-lab` **không** sudo, khoá SSH riêng `~/.ssh/fde-pc` trên laptop, `FDE_PC_SSH=fde-lab@<địa chỉ PC>` trong
   `setup/.env`. Bài này chạy container nên thêm `fde-lab` vào nhóm `docker` (nhóm `docker` tương đương root trên PC đó;
   chỉ làm trên PC lab của bạn, và ghi nhớ đây chính là điều bạn sẽ **không** được xin ở máy khách).
2. Cài driver NVIDIA và NVIDIA Container Toolkit theo tài liệu của distro/NVIDIA (`nvidia-ctk runtime configure --runtime=docker`,
   khởi động lại Docker). Kiểm bằng user `fde-lab`: `nvidia-smi` chạy, `docker run --rm --gpus all
   ghcr.io/ggml-org/llama.cpp:server-cuda-b11718 --version` chạy.
3. Dưới user `fde-lab`: `docker pull ghcr.io/ggml-org/llama.cpp:server-b11718` và `…:server-cuda-b11718` (image CUDA này
   có `CUDA_VERSION=12.8.1`: driver ≥ 570.26 chạy đầy đủ; nhánh 535/550/560/565 chạy nhờ minor version compatibility và
   ngoại lệ trong `NVIDIA_REQUIRE_CUDA` của image; nhánh khác dưới 570 (vd. 545, 555) bị toolkit chặn; xem bài basic 01), chép `qwen2.5-1.5b-instruct-q4_k_m.gguf` (`llm-medium`, sha256 trong `fdekit.MODELS`) vào `~/fde-models/`.

Bộ chấm không cài gì lên PC: nó chỉ ghi vào `~/fde-ex-<run_id>` và dọn thư mục đó khi xong.

**Viết `starter/bench_pc.sh`** (POSIX sh, chạy trên PC bằng `fde-lab`): `sh bench_pc.sh <thư mục làm việc>`. Đo
`llm-medium` (`~/fde-models/…`, biến `FDE_PC_MODEL` ghi đè được) hai lần, mỗi lần một container llama.cpp server với
`-c 4096 -np 1 -t <số core vật lý>`: lần CPU bằng image `server-b11718`, lần GPU bằng image `server-cuda-b11718` với
`--gpus all` và `-ngl 99`. Mỗi lần: chờ `/health` 200, một request khởi động, 3 request `/completion` `n_predict` 128,
`ignore_eos` true, `cache_prompt` false; tokens/s = tổng `predicted_n` / tổng `predicted_ms` × 1000. Container mang tên
bắt đầu bằng tên thư mục làm việc (`fde-ex-<run_id>-…`) và bị xoá kể cả khi script bị ngắt. Dòng cuối stdout là JSON:

```json
{"gpu": {"name": "NVIDIA GeForce RTX 3060", "memory_mb": 12288, "driver": "570.172.08"},
 "cpu_tokens_per_s": 21.4, "gpu_tokens_per_s": 118.0}
```

Rồi viết vào `SOLUTION` của riêng bạn (không nộp) một đoạn ngắn: tỉ lệ GPU/CPU bạn đo được, VRAM đã dùng (`nvidia-smi`
trong lúc chạy) so với công thức của bài basic 02, và log khởi động của server CUDA có dòng nào cho thấy lớp đã được
đưa lên GPU.

## Tiêu chí đạt

`test_gpu_beats_cpu_on_pc` (skip với hướng dẫn khi `FDE_PC_SSH` chưa đặt; không bao giờ tự dò PC):

- `bench_pc.sh` thoát `0` trong 240 s, không để lại container nào có tên chứa `fde-ex-<run_id>`.
- `gpu.name` và `gpu.memory_mb` khớp `nvidia-smi --query-gpu` trên PC (`fdekit` đọc độc lập).
- `gpu_tokens_per_s` ≥ 3 × `cpu_tokens_per_s`. Ngưỡng 3× là ước lượng thận trọng cho model 1,5B Q4 trên GPU tầm RTX 3060
  so với CPU desktop; repo chưa đo được trên PC (driver của laptop repo không chạy), số bạn đo được là dữ liệu đầu tiên.

Tự chấm phần viết theo rubric trong `solutions/`.

## Gợi ý

### Gợi ý 1

Chạy lần GPU mà tokens/s gần bằng CPU: đọc log khởi động của container. llama.cpp in rõ có tìm thấy thiết bị CUDA không
và bao nhiêu lớp được offload.

### Gợi ý 2

`docker run --gpus all` báo `could not select device driver "" with capabilities: [[gpu]]` là tầng nào trong sơ đồ phần 1?

### Gợi ý 3

PC Windows + WSL2: driver cài ở Windows, trong WSL không cài driver Linux; toolkit cài trong WSL. Đọc tài liệu CUDA on WSL
của NVIDIA trước khi cài gì.
