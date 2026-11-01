---
title: Dừng tiến trình đúng cách bằng SIGTERM rồi mới SIGKILL
level: basic
services: []
files:
  - path: starter/graceful_stop.sh
    note: 4 TODO
  - path: tests/test_graceful_stop.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/basic/03-graceful-stop -q
---

## Mục tiêu

Hiểu vòng đời dừng một tiến trình như systemd, Docker và Kubernetes làm: gửi `SIGTERM`, cho thời gian dọn dẹp, hết hạn
mới `SIGKILL`. Phân biệt tiến trình còn sống, zombie và tiến trình của user khác, thay vì phản xạ `kill -9`.

## Đề bài

Worker của Olist Shop đang xử lý job khi bị dừng: nếu bị `kill -9`, job đang dở mất và khoá trong Redis không được
nhả. Viết `starter/graceful_stop.sh <pid> [timeout_giây]`:

1. Gửi `SIGTERM` tới `<pid>`.
2. Chờ tối đa `timeout_giây` (mặc định `10`), kiểm khoảng mỗi 0,1 giây. Tiến trình dừng thì in ra stdout
   `stopped <pid> SIGTERM` và thoát ngay, không chờ hết timeout.
3. Hết timeout mà tiến trình còn sống: gửi `SIGKILL`, chờ nó biến mất (tối đa 5 giây), in `killed <pid> SIGKILL`.

Tiến trình ở trạng thái **zombie** (cột `STAT` của `ps` bắt đầu bằng `Z`) đã chết, chỉ chờ tiến trình cha đọc exit
status, nên tính là đã dừng.

| Tình huống | Exit | Output |
| --- | --- | --- |
| Thiếu tham số, PID không phải số nguyên, PID `<= 1`, timeout không phải số nguyên `>= 0` | `2` | stderr bắt đầu bằng `Usage:` |
| Không có tiến trình `<pid>` | `1` | Thông báo lỗi ra stderr, stdout rỗng |
| Có tiến trình nhưng không có quyền gửi signal (của user khác) | `4` | Thông báo lỗi ra stderr, không gửi gì |
| Dừng trong thời gian chờ | `0` | `stopped <pid> SIGTERM` |
| Phải `SIGKILL` | `3` | `killed <pid> SIGKILL` |

Từ chối PID `1` (init/systemd) và `0` (`kill 0` gửi tới cả process group của chính bạn) là chủ ý: script dừng tiến
trình không bao giờ được nhắm vào chúng.

Test tạo các tiến trình Python thật: một tiến trình dọn dẹp mất 1 giây rồi thoát, một tiến trình bỏ qua `SIGTERM`,
một tiến trình con của chính pytest (thành zombie khi chết), và tìm một tiến trình của user khác (thường là root) để
thử trường hợp không có quyền; máy không có tiến trình nào như vậy thì test đó skip. Bài cần Linux vì test đọc
`/proc`.
Khác các bài còn lại của track, test chạy script **ngoài** sandbox bubblewrap vì script phải gửi signal tới PID thật
của máy mà sandbox (tách PID namespace) che mất; bù lại test chạy script trong session riêng (một `kill 0` viết nhầm
không chạm tới pytest) với môi trường dựng lại từ đầu.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/basic/03-graceful-stop -q` pass toàn bộ.
- `shellcheck starter/graceful_stop.sh` không có cảnh báo.
- Giải thích được vì sao `kill -0 <pid>` vẫn thành công với một zombie, và vì sao `kill -9` một zombie không làm nó
  biến mất.
- Nói được tương ứng của bài này trong systemd (`KillSignal=`, `TimeoutStopSec=`), Docker (`docker stop -t`) và
  Kubernetes (`terminationGracePeriodSeconds`).

## Gợi ý

### Gợi ý 1

`ps -p <pid>` trả exit `0` khi có tiến trình đó (kể cả zombie); `kill -0 <pid>` không gửi signal mà chỉ kiểm tiến
trình có tồn tại **và** bạn có quyền gửi. Kết hợp hai lệnh để tách "không có" (exit 1) với "không có quyền" (exit 4).

### Gợi ý 2

Trạng thái lấy bằng `ps -o stat= -p "$pid"` (dấu `=` bỏ dòng tiêu đề). Viết hàm `alive` trả thành công khi có trạng
thái và trạng thái không bắt đầu bằng `Z`, rồi vòng chờ `while alive; do ...; sleep 0.1; done` có đếm số lần. Kiểm
số nguyên bằng `[[ $x =~ ^[0-9]+$ ]]`.
