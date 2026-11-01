# Lời giải: dừng tiến trình đúng cách bằng SIGTERM rồi mới SIGKILL

Script đầy đủ ở `graceful_stop.sh` cạnh tệp này.

## Cách làm

1. **Kiểm tham số trước mọi thứ.** PID phải là số nguyên lớn hơn 1, timeout là số nguyên không âm. Chặn `0` và `1`
   không phải chuyện hình thức: `kill -TERM 0` gửi tới **cả process group** đang chạy script, `kill -TERM -1` gửi tới
   mọi tiến trình bạn có quyền.
2. **Tách ba trường hợp bằng hai lệnh.** `ps -p` trả lời "có tiến trình này không", `kill -0` trả lời "có và tôi có
   quyền gửi không". Không tách thì script báo "đã dừng" cho một tiến trình root mà nó không chạm được tới.
3. **`alive` đọc trạng thái**, không chỉ kiểm tồn tại. `kill -0` thành công với zombie vì PID vẫn nằm trong bảng
   tiến trình; script chỉ dùng `kill -0` sẽ chờ hết timeout rồi gửi `SIGKILL` vô ích (zombie không nhận signal nào,
   nó đã chết).
4. **Vòng chờ có đếm**: `timeout * 10` lượt, mỗi lượt `sleep 0.1`. Thoát ngay khi tiến trình dừng, nên tiến trình dọn
   dẹp trong 1 giây làm script trả sau khoảng 1 giây chứ không phải 10.
5. **`SIGKILL` là đường cuối**, kèm một vòng chờ ngắn. Tiến trình vẫn còn sau `SIGKILL` thường đang ở trạng thái `D`
   (uninterruptible sleep, chờ I/O của kernel, ví dụ NFS treo); script báo riêng (exit `5`) để người trực biết đây là
   chuyện của kernel hoặc storage, không phải của ứng dụng.

## Trạng thái tiến trình trong `ps`

| STAT | Nghĩa | Gửi signal được không |
| --- | --- | --- |
| `R` | Đang chạy hoặc chờ CPU | Có |
| `S` | Ngủ, chờ sự kiện (interruptible) | Có |
| `D` | Ngủ không ngắt được, chờ I/O | Signal chỉ được xử lý khi I/O xong; `SIGKILL` cũng phải chờ |
| `T` | Bị dừng (`SIGSTOP`, debugger) | `SIGKILL` có tác dụng; signal khác chờ tới khi `SIGCONT` |
| `Z` | Zombie: đã chết, chờ cha gọi `wait()` | Không có tác dụng; xử lý bằng cách sửa hoặc dừng tiến trình cha |

Nhiều zombie là lỗi của **tiến trình cha** không gọi `wait()`. Trong container, tiến trình của bạn là PID 1 và phải tự
thu dọn con mồ côi; đó là lý do có `docker run --init` (tini) và `shareProcessNamespace` trong Kubernetes.

## Cùng một mẫu ở các tầng

| Tầng | Signal đầu | Thời gian chờ | Sau đó |
| --- | --- | --- | --- |
| systemd | `KillSignal=` (mặc định `SIGTERM`) | `TimeoutStopSec=` (mặc định 90 giây) | `SIGKILL` (`FinalKillSignal=`) |
| Docker | `STOPSIGNAL` trong Dockerfile | `docker stop -t` (mặc định 10 giây) | `SIGKILL` |
| Kubernetes | `SIGTERM` sau `preStop` hook | `terminationGracePeriodSeconds` (mặc định 30) | `SIGKILL` |

Lỗi hay gặp khi deploy: ứng dụng chạy qua `sh -c "python app.py"`, shell nhận `SIGTERM` nhưng không chuyển cho Python,
nên mọi lần dừng đều chờ hết thời gian rồi bị `SIGKILL`. Sửa bằng `exec` (`exec python app.py`) hoặc dạng exec của
`CMD`/`ExecStart`.
