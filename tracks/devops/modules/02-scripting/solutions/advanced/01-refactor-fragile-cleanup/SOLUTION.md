# Hướng làm: sửa script dọn release mong manh

Bài Advanced không có một đáp án duy nhất. Dưới đây là danh sách lỗi của bản gốc, một bản viết lại tham khảo (đã chạy
qua toàn bộ test của bài và `shellcheck -S style`), các quyết định cần cân nhắc và rubric.

## Lỗi trong bản gốc

| # | Đoạn | Lỗi | Hậu quả | Cách sửa |
| --- | --- | --- | --- | --- |
| 1 | `#!/bin/bash`, không có `set -euo pipefail` | Lỗi không dừng script | Mọi lỗi dưới đây chạy tiếp thay vì dừng | `set -euo pipefail`, kiểm tham số tường minh |
| 2 | `DEPLOY_ROOT=$1` không kiểm | Thiếu tham số thì `DEPLOY_ROOT` rỗng | `cd /releases` lỗi, rồi `rm -rf /tmp/*` xoá sạch `/tmp` của máy (đúng sự cố trong đề) | `[[ -n $1 ]] \|\| usage`; kiểm `-d "$root/releases"` |
| 3 | `cd $DEPLOY_ROOT/releases` không kiểm lỗi | `cd` thất bại, script ở nguyên thư mục cũ (thường là `$HOME` của cron) | Vòng lặp `ls -t` xoá tệp trong `$HOME` | Không `cd`; làm việc với đường dẫn tuyệt đối, hoặc `cd -- "$dir" \|\| exit 1` |
| 4 | `$(ls -t \| tail ...)` | Parse output của `ls`, tách theo khoảng trắng | Release `r5 old` thành `r5` và `old`: xoá **bản mới nhất** `r5` | `find -printf` + NUL + `mapfile -d ''` |
| 5 | `rm -rf $r` | Thiếu `--` và ngoặc kép | Release `-hotfix` thành option của `rm`; glob trong tên được mở rộng | `rm -rf -- "$dir/$name"` |
| 6 | `KEEP=${2:-3}` không kiểm, dùng trong `$((KEEP+1))` | `abc` trong số học Bash là biến chưa đặt, bằng `0` | `KEEP=abc` thành `tail -n +1`: **xoá mọi release** | `[[ $keep =~ ^[1-9][0-9]*$ ]] \|\| usage` |
| 7 | Không biết `current` | Chỉ xét mtime | Sau một lần rollback, bản đang chạy là bản cũ và bị xoá; service chết ở lần restart sau | Đọc `readlink current`, bỏ qua bản đó |
| 8 | `rm -rf $DEPLOY_ROOT/tmp/*` | Không ngoặc kép, glob không khớp tệp ẩn | Đường dẫn có dấu cách bị tách; `.cache` còn lại; root rỗng thành `/tmp/*` | `shopt -s dotglob nullglob`, mảng, ngoặc kép |
| 9 | `echo "done"` ra stdout, không exit code có nghĩa | Cron gửi mail mỗi đêm hoặc nuốt mất; lỗi vẫn exit `0` | Không ai biết script đã hỏng | stdout chỉ cho dữ liệu, log ra stderr, exit code đúng |

## Bản viết lại tham khảo

```bash
#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob dotglob

usage() {
  echo "Usage: $0 <deploy_root> [keep>=1]" >&2
  exit 2
}

die() {
  echo "cleanup_releases: $*" >&2
  exit 1
}

[[ $# -ge 1 && $# -le 2 && -n "$1" ]] || usage
deploy_root="${1%/}"
keep="${2:-3}"
[[ "$keep" =~ ^[1-9][0-9]*$ ]] || usage
[[ -d "$deploy_root/releases" ]] || die "không thấy thư mục $deploy_root/releases"

current=""
if [[ -L "$deploy_root/current" ]]; then
  current="$(basename -- "$(readlink -- "$deploy_root/current")")"
fi

mapfile -d '' -t releases < <(
  find "$deploy_root/releases" -mindepth 1 -maxdepth 1 -type d -printf '%T@\t%f\0' \
    | sort -z -t $'\t' -k1,1nr \
    | cut -z -f2-
)

for ((i = keep; i < ${#releases[@]}; i++)); do
  name="${releases[$i]}"
  if [[ "$name" == "$current" ]]; then
    echo "giữ $name vì current đang trỏ tới" >&2
    continue
  fi
  rm -rf -- "$deploy_root/releases/$name"
  printf 'removed %s\n' "$name"
done

if [[ -d "$deploy_root/tmp" ]]; then
  entries=("$deploy_root/tmp"/*)
  if ((${#entries[@]})); then
    rm -rf -- "${entries[@]}"
  fi
fi
echo "cleanup_releases: xong" >&2
```

## Quyết định cần cân nhắc

- **Viết lại hay vá từng dòng?** Script 15 dòng thì viết lại nhanh hơn và dễ review hơn; script 500 dòng thì vá từng
  lỗi một, mỗi lỗi một commit kèm test, vì viết lại toàn bộ sẽ đánh mất các hành vi ngầm mà người khác đang dựa vào.
- **Giữ hay đổi giao diện?** Bài giữ `cleanup_releases.sh <root> [keep]` để crontab trên mọi máy không phải sửa. Đổi
  sang `getopts` (`-k 3 -n`) sạch hơn nhưng phải đổi crontab cùng lúc, tức là một đợt thay đổi có phối hợp.
- **mtime có đáng tin?** `touch`, `rsync` không giữ mtime, hay restore từ backup đều làm sai thứ tự. Tên release theo
  thời gian (`20261101T0200Z`) và sắp theo tên đáng tin hơn; công cụ deploy (bài Intermediate 02) giữ lịch sử riêng
  còn tốt hơn nữa.
- **Thêm dry-run.** Script xoá dữ liệu nên có `-n`; bài không bắt buộc để giữ giao diện, nhưng bạn nên nêu trong
  REVIEW.md mục 3.
- **Khoá.** Cron và một người chạy tay cùng lúc: thêm `flock -n` như bài Intermediate 01.
- **Có cần script không?** Công cụ deploy (Capistrano `keep_releases`, Ansible `deploy_helper`) đã làm việc này; dọn
  `tmp/` thì `systemd-tmpfiles` làm được bằng khai báo.

## Cách kiểm chứng an toàn

Không bao giờ thử một script xoá tệp mà bạn nghi là hỏng trên thư mục thật. Test của bài dùng hai lớp, và cả hai
dùng được cho mọi script tương tự. Lớp an toàn là **sandbox**: bubblewrap mount `/` chỉ đọc, che `/tmp` thật bằng một
tmpfs, chỉ cho ghi vào thư mục tạm của test, và dựng lại môi trường biến từ đầu; script có đổi `PATH`, gọi `/bin/rm`
hay Python để xoá thì cũng chỉ chạm được vào thư mục tạm. Lớp quan sát là **`rm` giả** đứng đầu `PATH`, ghi lại mọi
lần gọi để test biết script định xoá gì. Một `rm` giả một mình không phải lớp an toàn: chỉ cần script đặt lại `PATH`
(chuyện bình thường khi làm cứng script cho cron) là nó bị bỏ qua. Cách khác: container dùng một lần với thư mục mount
chỉ đọc (`docker run --rm -v "$PWD":/w:ro ...`), hay thay `rm` bằng `echo rm` để xem lệnh sẽ chạy. Chạy bản gốc không
tham số trong sandbox, nó xoá sạch `/tmp` **của sandbox**: đó chính là sự cố trong đề.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Script qua toàn bộ test | 30 | Mọi test `test_refactored_script` pass, `shellcheck -S style` sạch |
| Độ phủ lỗi trong REVIEW.md | 25 | Tìm ra ít nhất 7 trong 9 lỗi ở bảng trên, gồm cả lỗi 2 (biến rỗng thành `/tmp/*`), 4 (parse `ls`) và 6 (`KEEP` không phải số) |
| Hậu quả cụ thể | 15 | Mỗi lỗi nêu đầu vào cụ thể và thứ bị xoá nhầm, không chỉ "có thể gây lỗi" |
| Cách kiểm chứng | 15 | Tái hiện được lỗi mà không có nguy cơ xoá thật; có lệnh hoặc test chạy lại được |
| Điều chưa làm | 10 | Nêu được ít nhất 2 trong: dry-run, khoá, thứ tự theo mtime không đáng tin, giám sát/alert, chuyển sang công cụ deploy |
| Trình bày | 5 | Bảng gọn, mỗi dòng một lỗi, sửa gắn với lỗi |

Từ 70 điểm là đạt. Script dùng `rm -rf "$1"/...` mà không kiểm `$1` rỗng, hay xoá bản `current`, thì tối đa 40 điểm dù
REVIEW.md tốt.
