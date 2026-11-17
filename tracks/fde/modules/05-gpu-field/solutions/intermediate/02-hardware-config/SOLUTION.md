# Lời giải: installer chọn cấu hình theo phần cứng

Lời giải ở `hw_config.py` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/05-gpu-field/exercises/intermediate/02-hardware-config -q
```

Đo 2026-11-11 trên máy của repo: ~92 s (hai VM lần lượt, `factory` 3072 MB rồi `lab-open` 5120 MB).

## Kết quả trên hai máy

| Máy | Core vật lý | MemTotal | GPU | Cấu hình |
| --- | --- | --- | --- | --- |
| `factory` | 2 | 2 919 MB | không có `nvidia-smi` | `llm-small`, `-t 2`, embed 1 |
| `lab-open` (4 vCPU, 5120 MB) | 4 | ~4 900 MB | `nvidia-smi` có nhưng driver không chạy | `llm-medium`, `-t 4`, embed 2 |
| Laptop của repo (dry-run) | 8 (16 luồng) | 31 802 MB | `nvidia-smi` có, driver không chạy | `llm-medium`, `-t 8`, embed 4 |

## Các điểm dễ sai

1. **Core vật lý ≠ CPU logic.** `os.cpu_count()` trên laptop i7-11800H là 16, core vật lý 8. Sinh token bị giới hạn bởi
   băng thông bộ nhớ; thêm luồng hyper-thread không nhanh hơn và làm các luồng tranh nhau. Đếm cặp
   (`physical_package_id`, `core_id`) của các CPU **online** (CPU bị offline không đếm). Trong VM của lab, QEMU khai mỗi
   vCPU là một core nên hai con số trùng nhau; trên máy thật của khách thì không.
2. **"Có `nvidia-smi`" ≠ "có GPU".** Laptop của repo có card và có `nvidia-smi`, nhưng module không nạp nên `nvidia-smi`
   thoát 9. GPU chỉ "dùng được" khi lệnh query chạy thành công và in ra dòng có tên + bộ nhớ. Chọn `cuda` trên máy như vậy
   thì llama.cpp CUDA không khởi động (hoặc lặng lẽ chạy CPU với image to gấp mấy lần).
3. **Có GPU mà thiếu image CUDA thì dừng ngay, không đổi gì, không tải gì.** Đây là chỗ hỏng thật của `factory`: máy ra
   internet qua proxy, nhưng proxy chỉ được khai trong `/etc/environment` (cho phiên đăng nhập), còn `dockerd` không có
   proxy nào. Một installer "thấy thiếu image thì `docker pull`" treo ở bước phân giải DNS rồi chết sau ~50 s (đo:
   `lookup ghcr.io … i/o timeout`); tải model hay image bằng `curl` qua proxy thì đi được ra internet nhưng lấy về thứ
   không ghim, chưa đánh giá. Lời giải kiểm `docker image inspect` (đo: 0,06–0,08 s), thoát 3 kèm thông báo nói thiếu gì
   và lấy ở đâu (bundle GPU). Có image thì thoát 4: bundle 1.0.0 chỉ có compose CPU, áp cấu hình CUDA là việc của một
   bản phát hành khác. Một installer "đổi một nửa rồi chết" ở máy khách là sự cố tệ hơn installer từ chối chạy.
4. **`.env` có secret**: sửa đúng bốn khoá, giữ nguyên mọi dòng khác **theo byte** (làm việc trên `bytes`, giữ kết thúc
   dòng `\r\n` của từng dòng, chỉ thêm xuống dòng cho dòng cuối khi phải nối khoá mới), ghi tệp tạm tạo sẵn quyền `0600` (không phải ghi rồi
   mới `chmod`: giữa hai bước tệp đọc được bởi mọi người) rồi `os.replace` nguyên tử; SIGINT/SIGTERM bị chặn trong lúc
   ghi để không bao giờ còn `.env` dở dang.
5. **Idempotent**: chỉ ghi khi nội dung đổi; `docker compose up -d` tự không tạo lại service có cấu hình không đổi, nên lần
   chạy thứ hai không khởi động lại container nào. Model chỉ chép khi chưa có, chép qua tệp `.part` rồi đổi tên (hardlink
   khi cùng filesystem, không tốn thêm 1,1 GB; không `chmod` tệp hardlink vì đó cũng là inode của tệp nguồn).
6. **Đi thẳng tới `127.0.0.1`** khi chờ `/healthz` (`ProxyHandler({})`): máy xưởng có `http_proxy` trong
   `/etc/environment`.

## Các cách khác

Đạt test và đúng: đọc topology bằng `lscpu -p=CORE,SOCKET` thay vì sysfs (nhưng hàm `physical_cores(root)` vẫn phải đọc
cây sysfs được truyền vào, vì test gọi thẳng); viết installer bằng shell gọi một phần Python.

Có thể qua test nhưng sai với khách: hard-code `-t $(nproc)` khi `nproc` trùng số core trong VM (đúng ở lab, sai gấp đôi trên
server có hyper-threading); chọn model theo `MemAvailable` lúc cài (con số đổi theo ca và theo chính quillo đang chạy,
nên cùng một máy cài hai lần ra hai cấu hình). Quy tắc theo `MemTotal` ổn định; RAM trống theo ca là việc của benchmark
và giám sát (bài intermediate 01), không phải của bước chọn cấu hình.
