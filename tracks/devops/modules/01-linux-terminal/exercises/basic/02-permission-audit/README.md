---
title: Quét quyền tệp nguy hiểm trong thư mục release
level: basic
services: []
files:
  - path: starter/perm_audit.sh
    note: 3 TODO
  - path: tests/test_perm_audit.py
    note: Không sửa
run:
  - bash tracks/devops/modules/01-linux-terminal/exercises/basic/02-permission-audit/starter/perm_audit.sh tracks/devops/sample-app
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/basic/02-permission-audit -q
---

## Mục tiêu

Đọc được bit quyền như một người làm security review: phân biệt quyền ghi cho mọi người, setuid, setgid, sticky bit, và
biết tệp bí mật (khoá riêng, `.env`) để lộ cho group hay other nguy hiểm thế nào. Viết được một bước kiểm tự động bằng
`find`, có exit code dùng được trong CI.

## Đề bài

Trước khi đóng gói bản release Olist Shop để chép lên server, team muốn một bước kiểm quyền tệp. Viết
`starter/perm_audit.sh <thư mục>`, quét đệ quy thư mục và in mỗi phát hiện một dòng `<loại> <đường dẫn tương đối>`.

| Loại | Điều kiện |
| --- | --- |
| `world-writable` | Tệp thường mà other có quyền ghi (`o+w`) |
| `world-writable-dir` | Thư mục mà other có quyền ghi nhưng **không** có sticky bit (`/tmp` có sticky nên không tính) |
| `setuid` | Tệp thường có bit setuid |
| `setgid` | Tệp thường có bit setgid |
| `key-too-open` | Tệp thường tên `*.key` hoặc `id_*` (trừ `*.pub`) mà group hoặc other có **bất kỳ** quyền nào |
| `env-readable` | Tệp thường tên `.env` hoặc `*.env` mà other có bất kỳ quyền nào (`.env.example` không tính) |

Một tệp thoả nhiều điều kiện thì in nhiều dòng. Quy tắc đầu ra:

1. Đường dẫn tương đối so với thư mục quét, không có tiền tố `./` hay `/`, kể cả khi gọi với `.`.
2. Các dòng sắp theo thứ tự byte (`LC_ALL=C sort`) trên toàn dòng.
3. Không theo symlink: một symlink trỏ ra tệp `0666` bên ngoài không phải phát hiện.
4. Tên tệp và thư mục có dấu cách vẫn in đúng.
5. Không sửa quyền của tệp nào: đây là bước kiểm, không phải bước sửa.

Exit code:

| Tình huống | Exit | Output |
| --- | --- | --- |
| Không có tham số | `2` | stderr bắt đầu bằng `Usage:`, stdout rỗng |
| Thư mục không tồn tại | `2` | Thông báo lỗi ra stderr, stdout rỗng |
| Có ít nhất một phát hiện | `1` | Các dòng phát hiện ra stdout |
| Sạch | `0` | stdout rỗng |

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/basic/02-permission-audit -q` pass toàn bộ.
- `shellcheck starter/perm_audit.sh` không có cảnh báo.
- Giải thích được vì sao thư mục `0777` nguy hiểm còn `1777` thì chấp nhận được, và vì sao setuid trên một script
  Bash là dấu hiệu bất thường.
- Nói được exit code `1` khác `2` thế nào khi script chạy trong pipeline CI.

## Gợi ý

### Gợi ý 1

`find` có sẵn các phép thử cần dùng: `-type f`, `-type d`, `-name`, `! -name`, và `-perm`. `-perm -0002` nghĩa là
"có **đủ** các bit này", `-perm /0077` (GNU) nghĩa là "có **ít nhất một** bit trong số này". `find` mặc định không
theo symlink (`-P`). Trên macOS, `find` của BSD không có `-printf` và viết `-perm +0077` thay cho `/0077`; cài
`findutils` (`gfind`) để dùng cùng cú pháp với Linux.

### Gợi ý 2

`cd` vào thư mục quét bên trong một subshell rồi `find . ... -printf '<loại> %P\n'`: `%P` in đường dẫn đã bỏ phần
điểm bắt đầu, nên không còn `./`. Gom output của sáu lệnh `find` vào một biến, sắp một lần, rồi quyết định exit code
theo biến đó rỗng hay không.
