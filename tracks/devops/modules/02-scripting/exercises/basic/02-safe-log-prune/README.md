---
title: Dọn log đã xoay vòng bằng find, có dry-run và chặn thư mục nguy hiểm
level: basic
services: []
files:
  - path: starter/prune.sh
    note: 4 TODO
  - path: tests/test_prune.py
    note: Không sửa
run:
  - bash tracks/devops/modules/02-scripting/exercises/basic/02-safe-log-prune/starter/prune.sh -n -d /tmp/olist-logs -a 7
  - uv run pytest tracks/devops/modules/02-scripting/exercises/basic/02-safe-log-prune -q
---

## Mục tiêu

Viết một script xoá tệp mà bạn dám cho chạy bằng cron trên production: tham số qua `getopts`, có `-n` (dry-run) để
xem trước, từ chối thư mục cấp cao, không theo symlink, xử lý được mọi tên tệp, và hiểu đúng cách `find -mtime` làm
tròn tuổi tệp.

## Đề bài

Máy app của Olist Shop xoay vòng log hằng ngày (`api.log` thành `api.log.1`, rồi `api.log.2.gz`...). Đĩa vẫn đầy vì
không ai xoá bản cũ. Viết `starter/prune.sh -d <thư mục> -a <số ngày> [-p <glob>] [-n]`:

| Option | Nghĩa |
| --- | --- |
| `-d <thư mục>` | Bắt buộc. Thư mục quét, đệ quy cả thư mục con |
| `-a <số ngày>` | Bắt buộc. Số nguyên `>= 1` |
| `-p <glob>` | Mẫu tên tệp cho `find -name`, mặc định `*.log.*` (không bao giờ khớp log đang ghi `api.log`) |
| `-n` | Dry-run: chỉ in, không xoá |

Quy tắc:

1. Chỉ xét **tệp thường** (`find -type f`): bỏ qua thư mục (kể cả thư mục tên khớp mẫu như `archive.log.d`) và
   symlink (không xoá symlink, không đụng tệp nó trỏ tới). Không đi sang filesystem khác (`-xdev`).
2. Tuổi tính **đúng như `find -mtime +<số ngày>`**: tuổi tính bằng ngày, làm tròn xuống, phải **lớn hơn** số ngày.
   Với `-a 7`, tệp 8,5 ngày tuổi bị xoá, tệp 7,5 ngày tuổi **không** bị xoá.
3. Mỗi tệp một dòng ra stdout: `deleted <đường dẫn>`, hoặc `would delete <đường dẫn>` khi có `-n`. Đường dẫn in đúng
   như `find "<thư mục>"` in ra, tức bắt đầu bằng chuỗi `-d` bạn truyền vào (truyền `olist` thì in `olist/api.log.3.gz`).
   Thứ tự dòng không quan trọng.
4. Dòng cuối của stderr là `total=<số tệp>` (đã xoá, hoặc sẽ xoá khi dry-run), kể cả khi `0`.
5. Tên tệp có dấu cách, bắt đầu bằng `-` (như `-rf.log.4`) phải xử lý đúng.
6. Xoá bằng `rm` và quét bằng `find` **gọi qua `PATH`**: không viết `/bin/rm`, `/usr/bin/find`, `command rm`, `\rm`
   (test tìm các chuỗi này). Khi thử thư mục nguy hiểm, test đặt `find` và `rm` giả lên đầu `PATH` để biết script có
   gọi chúng không.

| Tình huống | Exit | Output |
| --- | --- | --- |
| Thiếu `-d` hoặc `-a`; `-a` không phải số nguyên `>= 1`; option lạ; tham số vị trí thừa | `2` | stderr bắt đầu bằng `Usage:`; stdout rỗng; không xoá gì |
| Thư mục không tồn tại | `1` | Lỗi ra stderr, stdout rỗng |
| Đường dẫn thật (sau khi giải symlink và `..`) là `/` hoặc chỉ một cấp dưới `/` (`/tmp`, `/var`, `/home`...) | `1` | Lỗi ra stderr, stdout rỗng, **không gọi `find` hay `rm`** |
| Bình thường (kể cả không có tệp nào) | `0` | Như quy tắc 3, 4 |

Test thử từ chối với `/`, `/tmp`, `/var`, một symlink trỏ tới `/`, và đường dẫn `<symlink tới />/usr/../home`. Chạy
lần hai ngay sau lần một phải in `total=0`. Test chạy từ thư mục tạm của nó, nên đường dẫn tương đối trong test bắt
đầu từ đó.

Mọi test chạy script của bạn trong sandbox bubblewrap (xem [Cài đặt](../../../README.md#0-cài-đặt)): `/` chỉ đọc, `/tmp` thật bị che, thư mục làm việc và thư mục duy nhất ghi được là thư mục tạm của test, môi trường biến dựng lại từ đầu (chỉ có `PATH`, `HOME` trỏ vào thư mục tạm, `LANG`/`LC_ALL`, cộng các biến test đặt); `/run` và `~/.docker` bị che nên không gọi được Docker; mạng không bị tách để test
gọi được server giả trên `127.0.0.1`. Thiếu `bwrap` thì test skip. Sandbox mới là lớp bảo vệ máy bạn; `find`/`rm` giả chỉ để chấm.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/02-scripting/exercises/basic/02-safe-log-prune -q` pass toàn bộ, gồm
  `shellcheck -S style` sạch.
- Giải thích được vì sao `find ... | xargs rm` hỏng với tên có dấu cách, và hai cách đúng (`-print0` với
  `read -d ''`, hoặc `-exec rm -f -- {} +`).
- Nói được vì sao logrotate (`maxage`, `rotate`) hay `systemd-tmpfiles` thường là lựa chọn tốt hơn một script tự viết,
  và khi nào script vẫn cần.

## Gợi ý

### Gợi ý 1

`getopts ":d:a:p:n"`: chữ có `:` theo sau nhận giá trị (`$OPTARG`). Giải đường dẫn thật bằng `realpath -e -- "$dir"`.
Cẩn thận với `cd "$dir" && pwd -P`: qua symlink trỏ tới `/` nó có thể trả `//home`, và phép đếm dấu `/` ngây thơ sẽ
cho qua. Đếm số thành phần bằng cách bỏ mọi ký tự khác `/`: `parts="${real//[^\/]/}"`, rồi `${#parts}`.

### Gợi ý 2

```bash
while IFS= read -r -d '' file; do
  ...
done < <(find "$dir" -xdev -type f -name "$pattern" -mtime +"$days" -print0)
```

Dùng process substitution `< <(...)` thay cho `find ... | while`: vòng `while` sau pipe chạy trong subshell, biến
đếm tăng trong đó mất khi vòng kết thúc. Xoá bằng `rm -f -- "$file"`; `--` báo hết option, nên tên bắt đầu bằng `-`
không bị hiểu là option.
