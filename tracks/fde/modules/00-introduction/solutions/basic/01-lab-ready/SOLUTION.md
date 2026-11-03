# Lời giải: Lab sẵn sàng

Lời giải đầy đủ ở `lab_ready.sh` cạnh tệp này. Chạy:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/00-introduction/exercises/basic/01-lab-ready -q
```

## Từng dòng và vì sao

- **`os`**: đọc `/etc/os-release` trong subshell (`$(. /etc/os-release && echo "$ID")`). Không dựa vào `lsb_release`
  (không phải bản cài nào cũng có) và không đọc `/etc/issue` (khách hay sửa banner đăng nhập).
- **`user`**: `id -un`, không dùng `$USER` (biến này không chắc có trong phiên SSH chạy lệnh, cron hay systemd).
- **`docker`**: `docker version --format '{{.Server.Version}}'` chỉ in được khi client **nói chuyện được với daemon**.
  `docker --version` thì chỉ là client, sẽ báo "có Docker" cả khi daemon chết hay user không thuộc nhóm `docker`, đúng
  kiểu báo cáo sai mà FDE hay nhận từ khách ("máy có Docker rồi anh ạ").
- **`compose`**: thử chạy `docker compose version` chứ không tìm tệp plugin; plugin có thể nằm ở
  `/usr/libexec/docker/cli-plugins`, `/usr/lib/docker/cli-plugins` hay `~/.docker/cli-plugins` tuỳ cách cài.
- **`egress`**: thử đường thẳng với `--noproxy '*'` trước; thất bại mà có `HTTPS_PROXY` thì thử qua proxy bằng URL
  `http://`, vì proxy TLS inspection làm HTTPS lỗi chứng chỉ dù đường vẫn thông. Mọi lệnh mạng có `--max-time` để máy
  air-gapped không treo tới khi hết 30 s.

## Chạy thử trên các hồ sơ khác (đo 2026-11-04)

| Hồ sơ | Output |
| --- | --- |
| `lab-open` | `os=ubuntu-22.04`, `user=fde`, `docker=29.1.3`, `compose=yes`, `egress=open` |
| `hospital` | `os=ubuntu-20.04`, `user=fde`, `docker=26.1.3`, `compose=no`, `egress=proxy` |
| `bank` | `os=rocky-8.10`, `user=fde`, `docker=missing`, `compose=no`, `egress=none` |

Cùng một script ra ba bức tranh rất khác nhau: đó là lý do FDE khảo sát máy **trước** khi hứa ngày cài (module 01).
Ở `bank` runtime là Podman rootless; phiếu năm dòng chưa hỏi chuyện đó, module 01 sẽ mở rộng thành báo cáo 13 trường.

## Lỗi hay gặp

- Dùng `#!/bin/bash` rồi viết `[[ ... ]]`: test chạy bằng `sh` (dash) nên lỗi cú pháp.
- `set -e` cộng một lệnh dò thất bại (vd. `docker version` khi không có daemon) làm script thoát giữa chừng, mất các
  dòng sau. Lệnh dò phải được bắt kết quả bằng `if` hay `||`.
- In thêm dòng "Đang kiểm tra..." ra stdout làm hỏng định dạng máy đọc; thông báo cho người đọc ghi ra stderr.
- Quên `--max-time`: trên máy không có mạng, `curl` chờ DNS/kết nối rất lâu.
