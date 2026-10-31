# Lời giải: phân loại nút thắt hiệu năng từ output đã chụp

Code đầy đủ ở `triage.py` cạnh tệp này.

## Cách làm

1. **Đọc theo tên cột, không theo vị trí.** vmstat của procps 4 thêm cột `gu`, sysstat đổi `avgqu-sz` thành `aqu-sz`
   và thêm nhóm cột discard (`d/s`, `d_await`). Lấy tên từ dòng tiêu đề rồi `zip` với giá trị thì cùng một code đọc
   được output của Ubuntu 18.04 lẫn 24.04.
2. **Bỏ mẫu "từ lúc khởi động".** Dòng dữ liệu đầu của `vmstat` và báo cáo đầu của `iostat` là trung bình từ boot.
   Trong `vmstat_ok.txt`, dòng đó có `r=14`, `us=70`, `wa=5`: đọc nhầm là kết luận máy quá tải trong khi ba mẫu hiện
   tại gần như rảnh. Trong `vmstat_cpu.txt` thì ngược lại: dòng đầu báo `id=91`.
3. **Thứ tự chẩn đoán có lý do.** Swap kéo theo mọi thứ khác: trang bị đẩy ra đĩa làm `wa` tăng, kernel tốn CPU
   (`sy`) để quản lý bộ nhớ, tiến trình chờ trang (`b`). `vmstat_memory.txt` có `wa` 40,5% và `b` từ 4 tới 6, nhưng
   `si + so` trung bình 8 217 KiB/s: thêm đĩa nhanh hơn không giải quyết, thêm RAM hoặc giảm bộ nhớ ứng dụng thì có.
   Sau đó mới tới CPU (bão hoà là `r > ncpu`, không phải `us` cao) rồi đĩa.
4. **Bão hoà đĩa cần cả `%util` lẫn hàng đợi.** `sdb` (đĩa backup gắn ngoài) có `%util` 99,6%, `aqu-sz` 72,9 và
   `w_await` 181 ms: hàng đợi dài, mỗi lần ghi chờ gần 0,2 giây. `dm-0` có `%util` 91,2% nhưng `aqu-sz` 0,11: thiết
   bị luôn có việc nhưng không có ai xếp hàng, và nằm trên NVMe xử lý hàng chục request song song.
5. **Lọc cổng theo cột local.** `grep :8000` đếm cả 4 kết nối mà chính máy này mở **tới** cổng 8000 (Nginx cùng máy gọi
   API). Cột 4 là local, cột 5 là peer.

## Đọc fixture

| Fixture | Kết luận | Bằng chứng | Bước tiếp theo |
| --- | --- | --- | --- |
| `vmstat_cpu.txt` (4 CPU) | CPU bão hoà | `r` trung bình 10, tức 2,5 tiến trình chờ mỗi CPU; `us+sy` 98,6% | `pidstat -u 1` hoặc `top` tìm tiến trình; `perf top` tìm hàm |
| `vmstat_memory.txt` | Thiếu bộ nhớ | `si+so` 8 217 KiB/s, `free` 57–61 MB, `cache` co về 95 MB | `ps aux --sort=-rss`, `dmesg` tìm OOM killer, xem `MemoryMax` |
| `vmstat_disk.txt` | Đĩa | `wa` 41–50%, `b` 5–7, `bo` khoảng 98 MB/s | `iostat -x`, `iotop`/`pidstat -d` tìm ai ghi |
| `iostat_x.txt` | `sdb` bão hoà | `aqu-sz` 72,9, `w_await` 181 ms | Đổi lịch backup, ghi qua `ionice -c3`, đĩa nhanh hơn |
| `ss_tan.txt` | Ứng dụng rò socket | 43 `CLOSE-WAIT` trên 8000 | Peer đã đóng, ứng dụng chưa `close()`: lỗi code (không đóng connection trong nhánh lỗi) |
| `ss_ltn.txt` | 8000 và Redis 6379 từ chối kết nối mới | `Recv-Q` 129 > backlog 128; `511 = 511` | Ứng dụng `accept()` chậm (worker kẹt); tăng `somaxconn` chỉ hoãn vấn đề |

- `CLOSE-WAIT` không tự hết: socket nằm đó tới khi tiến trình đóng nó hoặc chết, và mỗi cái giữ một file descriptor;
  đủ nhiều thì `Too many open files`.
- `TIME-WAIT` 25 cái ở phía client gọi Postgres là bình thường (phía chủ động đóng giữ 60 giây). Hàng chục nghìn cái
  thì nghĩa là không dùng connection pool.

## USE method trong một bảng

| Tài nguyên | Utilization | Saturation | Errors |
| --- | --- | --- | --- |
| CPU | `us+sy` (vmstat), `%CPU` (top) | `r > ncpu`, load average so với số CPU, `PSI cpu` | Hiếm; `perf` cho lỗi phần cứng |
| Bộ nhớ | `free`, `used` (trừ page cache) | `si/so`, `PSI memory`, OOM kill | `dmesg` OOM, lỗi cấp phát |
| Đĩa | `%util` (chỉ đúng với đĩa tuần tự) | `aqu-sz`, `r_await`/`w_await`, `b` | `dmesg` I/O error, SMART |
| Mạng | Throughput so với băng thông (`sar -n DEV`) | `Recv-Q` của LISTEN, drop, retransmit (`nstat`) | `ip -s link` errors/drops |

Trên kernel 4.20+, `/proc/pressure/{cpu,memory,io}` (PSI) cho trực tiếp "bao nhiêu phần trăm thời gian có tiến trình
phải chờ tài nguyên này", gọn hơn suy từ `r` và `b`.
