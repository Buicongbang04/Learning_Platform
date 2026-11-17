# Lời giải: support bundle

## Hướng làm

`support_bundle.sh` thu mọi thứ vào một thư mục tạm riêng (`mktemp -d`, `umask 077`, `trap` dọn khi thoát kể cả khi bị
Ctrl-C), cho **mọi** output đi qua cùng một hàm `redact` trước khi ghi, rồi đóng gói ra `<out>.part` và `mv` thành tệp
cuối (người nhận không bao giờ thấy bundle dở dang).

- `collect <tệp> <lệnh…>` chạy lệnh, gộp stdout+stderr, ghi lỗi (lệnh, mã thoát) vào `errors.txt` rồi vẫn chạy tiếp:
  lượt `support` không vào được Docker vẫn ra bundle đủ phần còn lại.
- `redact` (sed -E) che theo **dạng**, không theo giá trị: userinfo trong URL (`scheme://user:***@host`), credential sau
  `Authorization: Bearer|Basic|Token|Negotiate`, và giá trị của khoá có tên chứa `password`, `passwd`, `pwd`, `secret`,
  `token`, `apikey`/`api_key`, `private_key`, `credential` (cả dạng `KEY=giá trị` trong JSON của `docker inspect`, nhờ
  dừng ở dấu `"`). Giữ nguyên dòng, tên khoá, user, host, cổng.
- Không thu những nguồn rủi ro cao thay vì cố che chúng: không `env`, không `systemctl show`/`systemctl cat` (in
  `Environment=` của unit), không sao chép thư mục `/etc/docbridge/tls/` hay `/var/lib/docbridge/data/`.
- Log ứng dụng: `tail -n 5000 | tail -c 1900000` (≥ 1000 dòng cuối, ≤ 2 MB); journal: `journalctl -u docbridge -n 500`;
  log container: `docker logs --tail 500`. Che cả `systemctl status` vì nó in vài dòng journal cuối (có DSN).

Mã: `support_bundle.sh` cạnh tệp này.

## Vì sao bản của đồng nghiệp không gửi được

| Dòng | Vấn đề |
| --- | --- |
| `env > env.txt` | Biến môi trường của người chạy (có thể có token, proxy có mật khẩu) |
| `systemctl show docbridge` | In `Environment=DOCBRIDGE_SMTP_PASSWORD=…`, DSN có mật khẩu |
| `cp docbridge.conf` | Mật khẩu ERP, token quillo, proxy có userinfo nguyên văn |
| `cp docbridge.log` | Log hàng chục MB, có URL có mật khẩu và header `Authorization` |
| `docker inspect` | `Config.Env` có `CACHE_ADMIN_PASSWORD` |
| `/tmp/bundle` cố định | Để lại thư mục trong `/tmp`, hai lần chạy ghi đè nhau, user khác đọc được |

## Phương án khác (vẫn đúng ràng buộc của bài)

- Che bằng `awk` thay `sed -E`: được, miễn là POSIX `sh` gọi công cụ có sẵn.
- Ghi bundle ra stdout (`tar -czf - …`) để khách chuyển hướng tới nơi còn chỗ: tốt khi đĩa có thể đầy, nhưng bài yêu cầu
  đường dẫn tệp ra nên vẫn phải ghi `<out>`.
- `docker inspect --format '{{json .Config}}'` thay vì cả object: nhỏ hơn, nhưng test cần `Config.Env` trong output
  `docker inspect` (object hoặc mảng object), nên phải giữ cấu trúc đó.

## Kiểm thử của bài

Test gieo 12 secret ngẫu nhiên mỗi lượt (cấu hình 3, `Environment=` của unit 2, log giữa và cuối, `Authorization: Bearer`
và `Basic`, private key, env và log của container, một tệp dữ liệu) và so **từng đoạn 10 ký tự** của mọi secret đã gieo
(lượt 2 so cả secret của lượt 1, vì journal còn giữ dòng cũ) với mọi tệp trong bundle, nên che một nửa giá trị (`abcd****`) vẫn trượt. Các biến thể sai đã thử (mỗi biến thể chạy 2 lần, đều trượt): bỏ
quy tắc userinfo; xoá dòng có secret thay vì che; `docker inspect` không che; chép cả log.
