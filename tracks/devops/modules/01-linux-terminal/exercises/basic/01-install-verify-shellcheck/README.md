---
title: Cài shellcheck từ release chính thức và chứng minh đã kiểm
level: basic
services: []
files:
  - path: starter/install-log.md
    note: Nhật ký cài, điền mọi TODO
  - path: starter/shellcheck.sha256
    note: 2 dòng sha256sum (tarball và binary)
  - path: tests/test_install.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/basic/01-install-verify-shellcheck -q -rs
---

## Mục tiêu

Cài một công cụ dòng lệnh như cách làm trên server production: tải đúng bản từ nguồn chính thức, kiểm checksum **trước**
khi chạy, cài vào user space không cần `sudo`, xác nhận bản đang chạy chính là bản đã kiểm, và ghi lại đủ để người
khác làm lại hoặc gỡ được.

## Đề bài

Làm theo phần `## 0. Cài đặt` trong README của module (mục shellcheck), rồi ghi lại bằng chứng vào hai tệp trong
`starter/`.

**`starter/install-log.md`** giữ nguyên các heading và các dòng `- Tên: giá trị`, thay mọi `TODO`:

| Dòng hoặc phần | Điền gì | Test kiểm |
| --- | --- | --- |
| `- Phiên bản:` | Phiên bản đã cài, ví dụ `0.11.0` | Không thấp hơn `0.9.0`; trùng với `shellcheck --version` của bản đang chạy |
| `- Nền tảng:` | `<os>.<arch>` như trong tên tarball, ví dụ `linux.x86_64`, `linux.aarch64`, `darwin.aarch64` | Trùng với phần tương ứng trong URL và với máy đang chạy test |
| `- URL tải:` | URL tarball `.tar.xz` | Đúng dạng `https://github.com/koalaman/shellcheck/releases/download/vX.Y.Z/shellcheck-vX.Y.Z.<os>.<arch>.tar.xz`, cùng phiên bản với dòng trên |
| `- Đường dẫn cài:` | Đường dẫn binary, viết `~/.local/bin/shellcheck` hoặc đường dẫn tuyệt đối | Nằm trong `.local/bin`; trỏ tới đúng tệp mà `which shellcheck` trả về; nằm trong thư mục home |
| `## Lệnh đã chạy` | Các lệnh bạn đã chạy, theo thứ tự | Có bước kiểm `sha256sum -c` (hoặc `shasum -a 256 -c`) **đứng trước** bước `install`/`cp`/`mv` binary; không có `sudo` |
| `## Kết quả kiểm checksum` | Output của bước kiểm | Có dòng `<tên tarball>: OK` |
| `## Kết quả xác nhận` | Output của `which shellcheck` và `shellcheck --version` | Có dòng `ShellCheck - shell script analysis tool` và `version: <phiên bản>` |
| `## Cách gỡ` | Lệnh gỡ | Có lệnh `rm` xoá binary shellcheck |

**`starter/shellcheck.sha256`** đúng định dạng của `sha256sum` (`<64 ký tự hex><hai dấu cách><tên tệp>`), hai dòng:

1. Hash của tarball, tên tệp là tên tarball. Test so với hash đã ghim của release chính thức (bảng ở `## 0. Cài đặt`).
   Bạn cài phiên bản mới hơn bản đã ghim thì test chỉ kiểm định dạng dòng này, vì chưa có hash chuẩn để so.
2. Hash của binary đã cài, tên tệp là `shellcheck`. Test tự tính SHA-256 của tệp mà `which shellcheck` trỏ tới và so
   với dòng này: nếu bạn cài một tệp khác tệp đã kiểm (bản apt cũ còn đứng trước trong `PATH`, tệp bị sửa sau khi
   cài), test fail.

Toàn bộ log không được có kiểu cài "tải script rồi pipe thẳng vào shell" (một dòng `curl` hoặc `wget` có `|` nối vào
`sh`, `bash`, `zsh`, có hoặc không có `sudo`). Lệnh `curl ... | jq` để đọc JSON thì được.

Chưa cài shellcheck, hoặc bản trong `PATH` cũ hơn `0.9.0`, thì mọi test **skip** kèm lời nhắc; skip không tính là đạt.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/basic/01-install-verify-shellcheck -q -rs` pass
  toàn bộ, không skip.
- `which -a shellcheck` chỉ ra đúng một bản, hoặc bản trong `~/.local/bin` đứng đầu và bạn biết vì sao.
- Giải thích được checksum chống được gì (tải hỏng, mirror bị tráo) và **không** chống được gì (release gốc bị chiếm
  quyền), và vì sao hash nên lấy từ một kênh khác với kênh tải tệp.
- Giải thích được vì sao kiểu cài pipe script vào `sudo bash` bị cấm trong khoá này.

## Gợi ý

### Gợi ý 1

`uname -m` cho kiến trúc (`x86_64`, `aarch64`; macOS Apple Silicon báo `arm64`, tarball ghi `aarch64`). Đặt các giá
trị vào biến (`SC_VERSION`, `SC_FILE`) rồi dùng lại, vừa đỡ gõ sai vừa dán được nguyên khối vào log. `~/.local/bin`
chưa có trong `PATH` thì thêm `export PATH="$HOME/.local/bin:$PATH"` vào `~/.bashrc` rồi mở shell mới.

### Gợi ý 2

Tạo `shellcheck.sha256` bằng chính các tệp đã có: chép tệp `.sha256` dùng để kiểm tarball sang `starter/`, rồi nối thêm
hash binary bằng `(cd ~/.local/bin && sha256sum shellcheck) >> starter/shellcheck.sha256`. Chạy `cd` trong subshell
`( ... )` để tên tệp trong output chỉ là `shellcheck`, không kèm đường dẫn. Test fail ở dòng binary thì chạy
`which -a shellcheck`: thường là còn một bản khác đứng trước trong `PATH`, gõ `hash -r` sau khi sửa `PATH`.
