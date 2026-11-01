# Lời giải: công cụ chuyển release bằng Python

Mã đầy đủ ở `release.py` cạnh tệp này.

## Cách làm

1. **Kiểm `--version` bằng whitelist trong `main`** và báo bằng `parser.error` (thoát `2`, in usage). Version đi vào
   đường dẫn, nên mọi thứ ngoài `[A-Za-z0-9._-]` bị chặn; ký tự đầu phải là chữ hoặc số để loại `.`, `..`, tên ẩn và tên
   trông như option. Whitelist an toàn hơn blacklist (`if ".." in v`): bạn không phải đoán hết mọi cách tấn công.
2. **Idempotent trước, tác dụng phụ sau.** Bản đang chạy rồi thì trả `0` ngay: chạy lại pipeline deploy không khởi động
   lại gì, không chạy check thừa.
3. **Chép qua thư mục tạm cùng filesystem rồi `rename`.** Bị dừng giữa lúc chép thì chỉ còn `.v2.tmp-<pid>` rác, không
   bao giờ có `releases/v2` thiếu tệp mà lần sau tưởng là đã chép xong rồi dùng lại.
4. **Symlink tạm + `os.replace`.** `rename(2)` thay đích trong một bước: mọi tiến trình mở `current/...` hoặc thấy bản
   cũ, hoặc bản mới. `unlink` rồi `symlink` để lại một khoảng (rất ngắn nhưng có thật) không có `current`, và request
   rơi đúng lúc đó trả `500`. Symlink tương đối (`releases/v2`) để có thể chép hay mount cả `<root>` sang chỗ khác.
5. **Check chạy không qua shell.** `shlex.split` tách chuỗi theo quy tắc của shell (giữ nháy), nhưng không có shell nào
   chạy: `;`, `|`, `$(...)` chỉ là ký tự thường trong argv. Bắt `TimeoutExpired`, `OSError` để mọi kiểu hỏng đều đi về
   một đường: rollback, log, thoát `1`. Không để traceback lọt ra: người trực đọc log, không đọc stack trace.
6. **`.history` chỉ ghi khi đã thành công**, và ghi nguyên tử. Lịch sử là nguồn sự thật cho rollback; một dòng ghi cho
   bản hỏng sẽ làm lần rollback sau đưa bạn về bản hỏng.
7. **Dry-run** dùng chung bước kiểm, chỉ dừng trước tác dụng phụ đầu tiên.

## `subprocess` an toàn

| Viết | Vấn đề |
| --- | --- |
| `subprocess.run(f"pg_dump {db}", shell=True)` | `db = "x; rm -rf ~"` chạy luôn lệnh thứ hai (command injection) |
| `subprocess.run(["pg_dump", db])` | Đúng: `db` là một tham số, không có shell |
| `subprocess.run(cmd)` không `timeout=` | Lệnh treo là công cụ treo theo, cron chồng lên nhau |
| `subprocess.run(cmd)` không kiểm `returncode` | Lỗi bị nuốt; dùng `check=True` hoặc kiểm tay |
| `os.system(...)`, `os.popen(...)` | Luôn qua shell, không lấy được stderr riêng; tránh |
| `capture_output=True` với lệnh in hàng GB | Ăn hết RAM; ghi thẳng ra tệp bằng `stdout=fh` |

`shell=True` chấp nhận được khi chuỗi lệnh là **hằng số do bạn viết** và bạn thật sự cần tính năng của shell (pipe,
glob, redirect). Ngay cả khi đó, thường viết lại bằng Python (`pathlib.glob`, nối hai `Popen`) dễ test hơn.

## Bài này cố ý đơn giản hoá

- **Không khởi động lại service.** Thật ra sau khi chuyển `current` phải `systemctl reload` hoặc restart (hoặc gửi
  `SIGHUP`/`SIGUSR2` cho server hỗ trợ reload êm như gunicorn), và check nên gọi `/readyz` của **tiến trình mới**.
- **Không dọn release cũ.** Công cụ thật giữ N bản gần nhất (Capistrano mặc định 5), không bao giờ xoá bản đang chạy
  hay bản ngay trước nó.
- **Không khoá.** Hai người deploy cùng lúc có thể giẫm lên `.history`; thêm `fcntl.flock` trên `<root>/.deploy.lock`.
- **Không chuyển dữ liệu dùng chung.** Tệp upload, `.env` thường nằm ở `<root>/shared/` và được symlink vào từng
  release.
- **Migration DB.** Rollback code không rollback schema; thay đổi schema phải tương thích hai chiều (expand/contract),
  bàn ở module 07.

Khi đi lên container và Kubernetes (module 10–11), `Deployment` thay vai trò của symlink: ReplicaSet cũ còn nguyên để
`kubectl rollout undo`, readiness probe thay cho `--check`.
