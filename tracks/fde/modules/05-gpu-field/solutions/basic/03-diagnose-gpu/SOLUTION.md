# Lời giải: chẩn đoán GPU từ output nvidia-smi

Lời giải ở `diagnose_gpu.py` cạnh tệp này:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/05-gpu-field/exercises/basic/03-diagnose-gpu -q
```

## Cách làm

1. Sáu thông báo lỗi kiểm theo đúng thứ tự trong README bằng regex trên toàn văn bản. Đó là các tầng từ dưới lên (gói →
   module kernel → module/thư viện → container → phần cứng → nhận card).
2. Bảng: duyệt từng dòng tới `| Processes:` hoặc `| MIG devices:`; dòng nào khớp `|…| <used>MiB / <total>MiB |…|` là
   dòng hai của một GPU, dòng ngay sau có `MIG M.` ở ô cuối. Tách theo `|` thay vì đếm khoảng trắng, vì tên card dài ngắn
   khác nhau và bảng MIG có ô `Memory-Usage` riêng (không được tính).
3. MIG trước bộ nhớ: A100 bật MIG trông như trống (38 MiB / 40960 MiB) nhưng không ai được cấp cả card.
4. Bận hay không theo **bộ nhớ trống so với nhu cầu**, không theo danh sách tiến trình: `container-hidden-processes.txt`
   không liệt kê tiến trình nào (chúng ở PID namespace khác) mà VRAM đã dùng 19 GiB.
5. Nhiều GPU: chỉ cần một GPU đủ chỗ là `ok` (`two-l4-one-busy.txt`: GPU 0 bận, GPU 1 trống); khi đó cấu hình runtime
   phải chọn đúng GPU (`CUDA_VISIBLE_DEVICES=1` hoặc `--gpus device=1`).

## Câu hỏi tiếp theo cho khách theo từng chẩn đoán

| Mã | Hỏi/nhờ khách |
| --- | --- |
| `not_installed` | `lspci -nn \| grep -i nvidia`: có card không? Có thì việc cài driver là của IT, gửi họ bản driver và toolkit tối thiểu |
| `driver_not_loaded` | `lsmod \| grep nvidia`, `dmesg \| grep -i nvidia`, `mokutil --sb-state`, `uname -r` so với bản kernel lúc cài driver (đúng trường hợp laptop của repo: kernel đã lên 6.12, không có module cho nó) |
| `driver_mismatch` | `cat /proc/driver/nvidia/version` so với gói; xin khung giờ reboot |
| `nvml_unknown` | Container chạy từ bao giờ, host có `daemon-reload` gần đây không; chạy lại container, cân nhắc CDI |
| `gpu_lost` | `dmesg \| grep Xid`; báo phần cứng, cần reboot, theo dõi nhiệt/nguồn |
| `no_gpu` | `lspci -k`: driver nào đang giữ card (vfio, nouveau)? |
| `mig_enabled` | Instance nào dành cho chúng tôi, profile gì (`nvidia-smi -L`) |
| `gpu_busy` | Ai dùng, theo lịch nào; có GPU khác hoặc khung giờ khác không |
| `unknown` | Xin chạy lại `nvidia-smi > gpu.txt 2>&1` và gửi tệp nguyên văn |

Cách khác cũng đạt test: dùng `nvidia-smi --query-gpu=memory.used,memory.total,mig.mode.current --format=csv` nếu bạn
được chạy lệnh. Nhưng đầu vào của bài là thứ khách **đã** gửi, thường là bảng mặc định, nên đọc được bảng vẫn là kỹ năng
cần có.
