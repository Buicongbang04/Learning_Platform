---
title: Driver, CUDA và container toolkit có hợp nhau không
level: basic
services: []
files:
  - path: starter/cuda_compat.py
    note: Hàm check và CLI, bạn viết
  - path: tests/test_cuda_compat.py
    note: Không sửa
run:
  - uv run pytest tracks/fde/modules/05-gpu-field/exercises/basic/01-cuda-compat -q
---

## Mục tiêu

Trước khi gửi image GPU cho khách, trả lời được "máy này chạy được không, với điều kiện gì" từ bốn con số khách gõ giúp
qua screen-share, theo một bảng tương thích có nguồn chứ không theo trí nhớ. Công cụ này là thứ bạn chạy cho từng máy
trong buổi khảo sát và đưa thẳng vào báo cáo.

## Đề bài

Viết `starter/cuda_compat.py` với hàm **`check(host: dict) -> dict`**. `host` có các khoá:

| Khoá | Ví dụ | Lấy từ máy khách bằng |
| --- | --- | --- |
| `driver` | `"550.163.01"` hoặc `None` (không có driver chạy được) | Dòng đầu `nvidia-smi` |
| `cuda` | `"12.8.1"` | Biến `CUDA_VERSION` của image (`docker image inspect`) |
| `toolkit` | `"1.17.8"` hoặc `None` (chưa cài) | `nvidia-ctk --version` |
| `compute_capability` | `"8.6"` | `nvidia-smi --query-gpu=compute_cap --format=csv` |
| `access` | `"gpus"` (`docker run --gpus`) hoặc `"cdi"` (`--device nvidia.com/gpu=all`) | Cách bạn định chạy |
| `docker` | `"28.3.0"` hoặc `None` | `docker version --format '{{.Server.Version}}'` |

Phiên bản so theo số từng phần (`580.65.06` > `580.9`; `620` < `620.0.1`). `cuda` chỉ xét `X.Y` (bỏ phần update).
`X.Y` không có trong bảng 1 (vd. `12.7`, `10.2`) hoặc `access` khác `gpus`/`cdi` thì `ValueError`.

**Bảng 1. Driver tối thiểu theo CUDA (Linux x86_64, mốc GA)**, theo CUDA Toolkit Release Notes 13.5 đọc ngày 2026-11-11:

| CUDA | Driver ≥ | CUDA | Driver ≥ | CUDA | Driver ≥ |
| --- | --- | --- | --- | --- | --- |
| 11.0 | 450.51.05 | 12.0 | 525.60.13 | 13.0 | 580.65.06 |
| 11.1 | 455.23 | 12.1 | 530.30.02 | 13.1 | 590 |
| 11.2 | 460.27.03 | 12.2 | 535.54.03 | 13.2 | 595 |
| 11.3 | 465.19.01 | 12.3 | 545.23.06 | 13.3 | 610 |
| 11.4 | 470.42.01 | 12.4 | 550.54.14 | 13.4 | 615 |
| 11.5 | 495.29.05 | 12.5 | 555.42.02 | 13.5 | 620 |
| 11.6 | 510.39.01 | 12.6 | 560.28.03 | | |
| 11.7 | 515.43.04 | 12.8 | 570.26 | | |
| 11.8 | 520.61.05 | 12.9 | 575.51.03 | | |

**Bảng 2. Mốc theo major**: driver tối thiểu cho minor version compatibility và compute capability (CC) tối thiểu.

| Major | Driver ≥ (minor version compatibility) | CC ≥ |
| --- | --- | --- |
| 11 | 450.80.02 | 3.5 |
| 12 | 525.60.13 | 5.0 |
| 13 | 580.65.06 | 7.5 |

**Quy tắc.** Kết quả là `{"compatible": bool, "issues": [...]}`; mỗi vấn đề là dict có `code`, `severity`
(`"error"` hoặc `"warning"`) và `detail` (chuỗi khác rỗng, lý do để đọc cho khách); mỗi `code` tối đa một lần;
`compatible` là `True` khi và chỉ khi không có vấn đề `error`.

| `code` | `severity` | Khi nào |
| --- | --- | --- |
| `no_driver` | error | `driver` là `None` (khi đó không xét ba dòng driver bên dưới) |
| `driver_too_old` | error | `driver` < mốc của `X.Y` trong bảng 1 **và** < mốc major trong bảng 2 |
| `minor_version_compat` | warning | `driver` < mốc của `X.Y` trong bảng 1 nhưng ≥ mốc major trong bảng 2 |
| `driver_drops_gpu` | error | (`driver` ≥ 495 và CC < 5.0) hoặc (`driver` ≥ 590 và CC < 7.5) |
| `cuda_drops_gpu` | error | CC < mốc CC của major trong bảng 2 |
| `no_toolkit` | error | `toolkit` là `None` (khi đó không xét ba dòng toolkit bên dưới) |
| `cdi_unsupported` | error | `access` là `cdi` và (`toolkit` < 1.12.0 hoặc `docker` là `None` hoặc `docker` < 25.0.0) |
| `cdi_needs_daemon_config` | warning | `access` là `cdi`, không có `cdi_unsupported`, và `docker` < 28.3.0 (phải bật `features.cdi` trong `daemon.json`) |
| `toolkit_cve` | warning | `toolkit` < 1.19.1 (còn CVE đã công bố tới bulletin 30/06/2026) |

`docker` chỉ được xét khi `access` là `cdi`.

**CLI** `python cuda_compat.py <host.json>` in kết quả của `check` dạng JSON ra stdout, thoát `0` khi `compatible`, `1`
khi không.

## Tiêu chí đạt

- `test_cases`: 26 tổ hợp có thật ở hiện trường (laptop driver hỏng, RTX 3060 với image CUDA 12.4 và 12.8, P100, V100,
  K80, toolkit cũ, CDI trên Docker 24/27/28.3, các mốc biên như `525.60.12`/`525.60.13`…): đúng tập `code`, đúng
  `severity`, có `detail`, đúng `compatible`.
- `test_unknown_input_raises`: CUDA 12.7 (không tồn tại), CUDA 10.2 (ngoài bảng), `access` lạ đều `ValueError`.
- `test_cli`: CLI chạy trong sandbox, JSON đúng, mã thoát đúng.

## Gợi ý

### Gợi ý 1

`"580.9" > "580.65.06"` khi so chuỗi. Còn `"620"` so với `"620.40.02"` thì sao khi so tuple?

### Gợi ý 2

Thứ tự kiểm driver: đạt mốc của đúng bản `X.Y` trước đã; chỉ khi không đạt mới cần biết nó có đạt mốc "cả major" không.

### Gợi ý 3

Lấy hai dòng `driver_too_old` và `minor_version_compat`: một máy không bao giờ có cả hai cùng lúc.
