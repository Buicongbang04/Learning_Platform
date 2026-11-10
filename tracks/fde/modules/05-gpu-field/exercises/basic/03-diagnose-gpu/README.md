---
title: Chẩn đoán GPU từ output nvidia-smi khách gửi
level: basic
services: []
files:
  - path: starter/diagnose_gpu.py
    note: Hàm diagnose và CLI, bạn viết
  - path: tests/fixtures
    note: 12 output nvidia-smi; nguồn gốc từng tệp ở tests/fixtures/README.md
  - path: tests/test_diagnose_gpu.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/05-gpu-field/exercises/basic/03-diagnose-gpu -q
---

## Mục tiêu

Lệnh đầu tiên khách gõ giúp bạn là `nvidia-smi`, và thứ bạn nhận lại có khi là một bảng, có khi là một dòng lỗi. Bài này
viết công cụ phân loại output đó thành một chẩn đoán có nghĩa vận hành ("driver chưa nạp", "GPU đang bị người khác dùng",
"card đang chia MIG"…) để bước tiếp theo là một câu hỏi đúng cho khách, không phải một buổi đoán mò.

## Đề bài

`tests/fixtures/` có 12 output: 3 tệp ghi thật (laptop của repo có card RTX 3050 Mobile nhưng driver không nạp; máy
`factory` không cài driver, qua `bash` và qua `sh`), 9 tệp dựng lại theo đúng định dạng của `nvidia-smi` nhánh 550/570
(xem `tests/fixtures/README.md`).

Viết `starter/diagnose_gpu.py`, hàm **`diagnose(text: str, need_mb: int) -> str`**: `text` là toàn bộ stdout + stderr
của `nvidia-smi`, `need_mb` là VRAM model của bạn cần (MiB). Trả **một** mã, xét theo đúng thứ tự:

| Thứ tự | Mã | Khi `text` |
| --- | --- | --- |
| 1 | `not_installed` | Có `nvidia-smi: command not found` hoặc `nvidia-smi: not found` |
| 2 | `driver_not_loaded` | Có `couldn't communicate with the NVIDIA driver` |
| 3 | `driver_mismatch` | Có `Driver/library version mismatch` |
| 4 | `nvml_unknown` | Có `Failed to initialize NVML: Unknown Error` |
| 5 | `gpu_lost` | Có `Unable to determine the device handle` hoặc `GPU is lost` |
| 6 | `no_gpu` | Có `No devices were found` |
| 7 | `unknown` | Không khớp dòng nào ở trên và không đọc được GPU nào từ bảng |
| 8 | `mig_enabled` | Có ít nhất một GPU mà cột `MIG M.` là `Enabled` |
| 9 | `gpu_busy` | Với **mọi** GPU, `total − used` của cột `Memory-Usage` (MiB) < `need_mb` |
| 10 | `ok` | Còn lại: có ít nhất một GPU còn trống ≥ `need_mb` |

"GPU trong bảng" là mỗi khối ba dòng giữa dòng `|===…===|` đầu tiên và bảng `Processes:`/`MIG devices:`: dòng hai có
`<used>MiB / <total>MiB` ở cột giữa, dòng ba có giá trị `MIG M.` ở cột cuối. Bảng `MIG devices` và `Processes` không được
dùng để tính bộ nhớ trống.

**CLI** `python diagnose_gpu.py <tệp output> <need_mb>` in `{"diagnosis": "<mã>"}` ra stdout, thoát `0`.

## Tiêu chí đạt

- `test_recorded_samples`: đúng mã cho cả 12 tệp (mỗi tệp có tập mã chấp nhận ghi trong test).
- `test_memory_numbers_are_read`: 200 biến thể sinh ngẫu nhiên mỗi lần chạy từ 4 bảng (số MiB đã dùng đổi ngẫu nhiên,
  `need_mb` quanh ngưỡng): đúng `ok`/`gpu_busy`.
- `test_mig_wins_over_free_memory`, `test_unparseable_is_unknown`, `test_cli`.

## Gợi ý

### Gợi ý 1

Mở `container-hidden-processes.txt` và `mig-a100.txt` cạnh `idle-rtx3060.txt`. Cái gì trong bảng nói thật về tình trạng
GPU, cái gì chỉ là một phần sự thật?

### Gợi ý 2

Đừng đếm cột theo số khoảng trắng: tên GPU dài ngắn khác nhau. Tách dòng theo `|` rồi đọc ô.

### Gợi ý 3

Với mỗi chẩn đoán, viết thêm (cho chính bạn, không cần nộp) câu bạn sẽ hỏi khách tiếp theo. Bảng ở phần 3 của README
module có cột đó.
