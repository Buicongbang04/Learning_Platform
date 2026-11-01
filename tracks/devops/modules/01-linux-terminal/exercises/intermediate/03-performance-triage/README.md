---
title: Phân loại nút thắt hiệu năng từ output vmstat, iostat và ss đã chụp
level: intermediate
services: []
files:
  - path: starter/triage.py
    note: 7 TODO
  - path: tests/test_triage.py
    note: Không sửa
  - path: tests/fixtures/vmstat_cpu.txt
    note: Output đã chụp, có thêm vmstat_memory, vmstat_disk, vmstat_ok, iostat_x, ss_tan, ss_ltn
run:
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/intermediate/03-performance-triage -q
---

## Mục tiêu

Đọc output của `vmstat`, `iostat -x` và `ss` theo USE method (Utilization, Saturation, Errors) để nói được nút thắt
nằm ở CPU, bộ nhớ, đĩa hay ở chính ứng dụng, và biết ba cái bẫy làm người trực kết luận sai: dòng "từ lúc khởi động",
`%util` trên thiết bị song song, và lọc cổng nhầm phía.

## Đề bài

Trong các sự cố hiệu năng của Olist Shop, người trực đã chụp output vào `tests/fixtures/`. Viết bảy hàm trong
`starter/triage.py` để biến output thành kết luận.

**vmstat** (`vmstat 1 6` hoặc tương tự):

1. `parse_vmstat(text)`: trả list dict `{tên cột: int}` lấy tên cột từ dòng tiêu đề (`r b swpd ... us sy id wa st`,
   procps mới có thêm `gu`). Bỏ dòng `procs ...`, bỏ dòng tiêu đề kể cả khi nó lặp lại giữa output, và **bỏ mẫu dữ
   liệu đầu tiên**: dòng đó là trung bình từ lúc máy khởi động, không phải hiện tại.
2. `use_summary(samples, ncpu)`: trung bình trên các mẫu của `cpu_util` (`us + sy`), `run_queue_per_cpu`
   (`r / ncpu`), `iowait` (`wa`), `blocked` (`b`), `swap_io` (`si + so`). Không có mẫu nào hoặc `ncpu <= 0` thì
   `ValueError`.
3. `diagnose(samples, ncpu)`: trả một trong bốn chuỗi, xét **theo thứ tự**:
   - `"memory"` nếu `swap_io >= SWAP_IO_LIMIT` (100 KiB/s). Đang swap thì CPU và đĩa bận chỉ là hệ quả.
   - `"cpu"` nếu `run_queue_per_cpu > 1`: số tiến trình chờ CPU nhiều hơn số CPU, tức là bão hoà.
   - `"disk"` nếu `iowait >= IOWAIT_LIMIT` (20) hoặc `blocked >= BLOCKED_LIMIT` (1).
   - `"ok"` trong các trường hợp còn lại.

**iostat** (`iostat -x 1 2`):

4. `parse_iostat(text)`: dict `{device: {tên cột: float}}` của **báo cáo cuối cùng** (báo cáo đầu cũng là trung bình
   từ lúc khởi động). Đọc cột theo tên tiêu đề vì mỗi phiên bản sysstat một kiểu: bản mới có `aqu-sz`, bản cũ
   (`Device:` có dấu hai chấm) gọi là `avgqu-sz`; luôn trả khoá `aqu-sz` cho cả hai.
5. `saturated_devices(text, util=90.0, queue=1.0)`: tên device có `%util >= util` **và** `aqu-sz >= queue`, sắp theo
   tên. `%util` chỉ nói "có ít nhất một request đang chạy" trong bao nhiêu phần trăm thời gian; với NVMe, RAID hay
   device-mapper xử lý song song, `%util` 91% vẫn có thể còn dư nhiều, nên phải nhìn thêm hàng đợi.

**ss**:

6. `socket_states(text, port=None)`: `Counter` số socket theo trạng thái (`ESTAB`, `CLOSE-WAIT`...) từ `ss -tan`. Có
   `port` thì chỉ đếm socket có cổng **local** bằng `port` (socket của client nối **tới** cổng đó không tính). Địa chỉ
   có thể là `10.0.1.12:8000`, `[::]:8000` hoặc `[::ffff:10.0.1.12]:8000`.
7. `listen_overflow(text)`: từ `ss -ltn`, địa chỉ `Local Address:Port` của socket `LISTEN` có accept queue đầy, tức
   `Recv-Q >= Send-Q` với `Send-Q > 0` (với socket LISTEN, `Recv-Q` là số kết nối chờ `accept()`, `Send-Q` là backlog
   tối đa). Sắp theo chuỗi.

Sau khi test pass, đọc lại fixture và trả lời: trong `ss_tan.txt`, 43 socket `CLOSE-WAIT` trên cổng 8000 nói gì về
ứng dụng (gợi ý: phía nào chưa gọi `close()`)? Trong `ss_ltn.txt`, cổng nào đang từ chối kết nối mới?

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/intermediate/03-performance-triage -q` pass toàn bộ.
- Giải thích được bằng số liệu của fixture vì sao `vmstat_memory.txt` là `"memory"` dù `wa` trên 39%.
- Nói được vì sao `dm-0` với `%util` 91,2% không bị coi là bão hoà còn `sdb` thì có.
- Phân biệt được `CLOSE-WAIT` nhiều (lỗi ứng dụng) với `TIME-WAIT` nhiều (thường bình thường ở phía chủ động đóng).

## Gợi ý

### Gợi ý 1

Một dòng dữ liệu vmstat là dòng mà mọi từ đều là số và số từ bằng số cột tiêu đề. Gom mọi dòng như vậy, rồi trả
`rows[1:]`. `statistics.fmean` tính trung bình một generator. Với iostat, gặp dòng bắt đầu bằng `Device` (bỏ `:`) thì
nhớ tiêu đề mới và **xoá** kết quả cũ: hết vòng lặp, thứ còn lại là báo cáo cuối.

### Gợi ý 2

Cổng là phần sau dấu `:` **cuối cùng** của địa chỉ: `address.rsplit(":", 1)[-1]` đúng cho cả IPv4, `[::]:8000` và
`[::ffff:...]:8000`. Cột 4 (`parts[3]`) của `ss` là địa chỉ local, cột 5 là địa chỉ peer; dòng đầu là tiêu đề.
