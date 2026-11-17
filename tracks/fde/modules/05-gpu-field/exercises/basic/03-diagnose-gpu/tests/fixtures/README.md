# Output `nvidia-smi` dùng trong bài

Ghi thật (2026-11-11):

| Tệp | Máy | Lệnh |
| --- | --- | --- |
| `laptop-driver-not-loaded.txt` | Laptop của repo: GeForce RTX 3050 Mobile (GA107M), gói `nvidia-driver 550.163.01-2` của Debian, kernel `6.12.116+deb13-amd64`, module `nvidia` không nạp (`lsmod` trống, không có `/proc/driver/nvidia/version`) | `nvidia-smi > tệp 2>&1`, mã thoát 9 |
| `factory-not-installed.txt` | VM `factory` (Debian 12, không cài driver), lệnh gửi qua SSH (bash) | `nvidia-smi`, mã thoát 127 |
| `factory-not-installed-sh.txt` | VM `factory`, cùng lệnh qua `sh -c` (dash) | `sh -c nvidia-smi`, mã thoát 127 |

Dựng lại theo định dạng (repo không có máy ở các trạng thái này): bảng mặc định của `nvidia-smi` nhánh 550 và 570
(độ rộng cột 41/24/22, khối ba dòng mỗi GPU, bảng `Processes` với cột GI/CI, bảng `MIG devices` như trên A100 bật MIG),
theo tài liệu `nvidia-smi` của NVIDIA và các output công khai trong issue/diễn đàn của NVIDIA; thông báo lỗi giữ
nguyên văn chuỗi mà `nvidia-smi`/NVML in ra. Định dạng có thể lệch vài khoảng trắng so với một bản driver cụ thể.
Số liệu (nhiệt độ, công suất, PID, bộ nhớ) là số bịa nhưng hợp lý cho từng loại card. Ngày giờ ở dòng đầu là giả.

| Tệp | Tình huống |
| --- | --- |
| `idle-rtx3060.txt` | RTX 3060 12 GB trên máy bàn có giao diện đồ hoạ, Xorg + gnome-shell giữ ~300 MiB |
| `busy-rtx3060.txt` | Cùng máy, một tiến trình `python3` của người khác giữ ~10,5 GiB, GPU-Util 97% |
| `two-l4-one-busy.txt` | Server 2× L4 24 GB, GPU 0 bận, GPU 1 trống |
| `container-hidden-processes.txt` | Gọi từ trong container: bộ nhớ đã dùng ~19 GiB nhưng `No running processes found` |
| `mig-a100.txt` | A100-SXM4-80GB bật MIG, hai instance `1g.10gb` |
| `no-devices.txt` | Driver nạp nhưng không nhận card |
| `driver-library-mismatch.txt` | Gói driver đã nâng, module kernel cũ chưa reboot |
| `nvml-unknown-error-in-container.txt` | Container mất quyền device sau `systemctl daemon-reload` |
| `gpu-fell-off-bus.txt` | GPU rơi khỏi bus (Xid 79) |
