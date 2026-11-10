---
title: Installer chọn cấu hình theo phần cứng
level: intermediate
services: []
files:
  - path: starter/hw_config.py
    note: Bước "chọn cấu hình LLM" của installer quillo, bạn viết
  - path: tests/fixtures/laptop-i7-11800h
    note: Cây topology CPU thật (sysfs) của laptop i7-11800H, 8 core 16 luồng
  - path: tests/test_hw_config.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit derive 05-gpu-field-factory
  - nice -n 15 uv run python -m fdekit derive 05-gpu-field-lab
  - uv run pytest tracks/fde/modules/05-gpu-field/exercises/intermediate/02-hardware-config -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Cùng một bundle quillo được cài ở máy xưởng 2 core 3 GB, ở máy lab 4 core 5 GB và (sẽ có) ở máy có GPU. Cấu hình LLM
viết tay cho từng khách thì sớm muộn sẽ sai ở một khách; installer phải tự đọc phần cứng và chọn theo **một bảng quy tắc
duy nhất**, in ra điều nó đã chọn và vì sao, và không bao giờ nhận nhầm "có `nvidia-smi`" là "có GPU dùng được".

## Đề bài

Viết `starter/hw_config.py` (Python 3.10+, thư viện chuẩn, chạy trên máy khách bằng user `fde`). Các hàm:

| Hàm | Trả |
| --- | --- |
| `physical_cores(root=Path("/sys/devices/system/cpu"))` | Số core vật lý trong các CPU đang online: đọc danh sách trong `root/online` (dạng `0-3,8-11`), mỗi CPU `N` có `root/cpuN/topology/physical_package_id` và `core_id`; các CPU cùng cặp (package, core) là một core |
| `mem_total_mb(path=Path("/proc/meminfo"))` | `MemTotal` theo MB (KiB // 1024) |
| `gpu_info()` | GPU dùng được đầu tiên `{"name": str, "memory_mb": int}`, hoặc `None`. "Dùng được" nghĩa là `nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits` (tìm trên `PATH`) chạy được, thoát `0` và in ít nhất một dòng `<tên>, <MiB>` |
| `choose(cores, mem_mb, gpu)` | Dict cấu hình theo bảng dưới |

Quy tắc của `choose` (`budget` = `gpu["memory_mb"]` nếu có GPU, không thì `mem_mb`):

| Khoá | Giá trị |
| --- | --- |
| `physical_cores`, `mem_total_mb`, `gpu` | Đúng đầu vào |
| `backend` | `"cuda"` nếu có GPU, không thì `"cpu"` |
| `n_gpu_layers` | `99` nếu có GPU, không thì `0` |
| `model` | `"llm-medium"` nếu `budget` ≥ 4096, không thì `"llm-small"` |
| `llm_file` | `qwen2.5-1.5b-instruct-q4_k_m.gguf` (medium) hoặc `qwen2.5-0.5b-instruct-q4_k_m.gguf` (small) |
| `llm_threads` | Số core vật lý |
| `embed_threads` | `max(1, cores // 2)` |

CLI `python3 hw_config.py [--quillo DIR] [--models DIR] [--dry-run]` (mặc định `~/quillo-1.0.0` và `~/models`): tính cấu
hình từ máy đang chạy và in nó dạng JSON một dòng ở **dòng cuối** stdout, thoát `0`. Không có `--dry-run` thì trước khi
in còn **áp dụng** vào bản cài quillo đang chạy bằng compose:

1. `backend` là `cuda` mà máy chưa có image `ghcr.io/ggml-org/llama.cpp:server-cuda-b11718`: in lý do ra stderr, thoát
   `3`, **không đổi gì**.
2. Model chọn chưa có trong `<quillo>/models/` thì lấy từ `--models` (thiếu cả ở đó thì thoát khác 0 kèm lý do).
3. Trong `<quillo>/.env` đặt `QUILLO_LLM_FILE`, `QUILLO_LLM_MODEL` (tên `llm-…`), `QUILLO_LLM_THREADS`,
   `QUILLO_EMBED_THREADS`; mọi dòng khác giữ nguyên từng byte, tệp giữ quyền `600` (có secret).
4. `docker compose up -d` trong `<quillo>`, chờ `http://127.0.0.1:18080/healthz` trả 200 (≤ 180 s).
5. Chạy lại khi không có gì đổi thì không khởi động lại container nào.

Test:

- Gọi thẳng `physical_cores` trên cây topology thật của laptop i7-11800H (và các biến thể `online`), gọi `choose` với 9
  bộ đầu vào.
- `--dry-run` trên máy của bạn trong sandbox, với một `nvidia-smi` giả đặt đầu `PATH` ở hai trạng thái: có nhưng driver
  không chạy (in nguyên văn output của laptop ở bài basic 03, thoát 9); có GPU RTX 3060 12288 MiB. Máy `factory` không có
  `nvidia-smi` nào.
- Boot snapshot `05-gpu-field-factory` (2 core, 3072 MB) rồi `05-gpu-field-lab` (`lab-open`, 4 core, 5120 MB), cả hai đang
  chạy quillo 1.0.0 với `llm-small` và có `llm-medium` ở `~/models`. Trên `lab-open`, `PATH` có `nvidia-smi` báo driver
  không chạy; trước đó test chạy một lần với `nvidia-smi` báo có RTX 3060 (máy không có image CUDA).

Đo trên máy của repo: cả bài ~80 s.

## Tiêu chí đạt

- `test_physical_cores_on_recorded_topology`, `test_choose_rules`: đúng giá trị.
- `test_dry_run_with_nvidia_smi`: JSON đúng với phần cứng thật của máy bạn (`lscpu`, `/proc/meminfo`) cho cả hai trạng
  thái `nvidia-smi`.
- `test_factory_and_lab`:
  - `lab-open` với `nvidia-smi` báo có GPU: thoát `3`, `.env` và container không đổi.
  - Trên mỗi máy: thoát `0`, JSON đúng quy tắc với số core vật lý (`lscpu`) và `MemTotal` của chính máy đó; `.env` có bốn
    khoá đúng, các dòng khác không đổi, quyền `600`; container `quillo-llm-1` chạy đúng tệp model và `-t`,
    `quillo-embed-1` đúng `-t`; `/healthz` 200; chạy lại lần hai không khởi động lại container quillo nào.

## Gợi ý

### Gợi ý 1

`os.cpu_count()`, `nproc` và `lscpu` trả lời ba câu hỏi khác nhau. Cây topology của laptop trong `tests/fixtures/` là
máy có hyper-threading: đếm thử.

### Gợi ý 2

Laptop của repo có `nvidia-smi` và có card NVIDIA. Nó có GPU dùng được không?

### Gợi ý 3

Compose chỉ tạo lại container khi cấu hình của service đó đổi. Muốn lần chạy thứ hai "không làm gì", lần đầu phải ghi
`.env` thế nào?
