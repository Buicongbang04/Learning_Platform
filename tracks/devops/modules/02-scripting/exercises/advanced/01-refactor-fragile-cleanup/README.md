---
title: Sửa một script dọn release mong manh đang chạy bằng cron trên production
level: advanced
services: []
files:
  - path: starter/cleanup_releases.sh
    note: Bản gốc đang chạy trên production; viết lại tại chỗ
  - path: starter/REVIEW.md
    note: Ghi lại lỗi tìm thấy, điền mọi TODO
  - path: tests/test_refactor.py
    note: Không sửa; chạy script trong sandbox với rm giả
  - path: tests/fixtures/cleanup_releases.original.sh
    note: Bản gốc giữ nguyên để test chứng minh mỗi kiểm tra bắt được lỗi thật
run:
  - uv run pytest tracks/devops/modules/02-scripting/exercises/advanced/01-refactor-fragile-cleanup -q
  - shellcheck tracks/devops/modules/02-scripting/exercises/advanced/01-refactor-fragile-cleanup/starter/cleanup_releases.sh
---

## Mục tiêu

Đọc một script "vẫn chạy được mấy năm nay" bằng con mắt của người review: tìm những dòng sẽ xoá nhầm dữ liệu khi đầu
vào lệch một chút, viết lại cho an toàn mà giữ nguyên hành vi đúng, và chứng minh từng lỗi bằng một phép thử chạy
được, không chỉ bằng nhận xét.

## Đề bài

`starter/cleanup_releases.sh` chạy bằng cron mỗi đêm trên mọi máy app của Olist Shop. Nó giữ `KEEP` bản release mới
nhất trong `<deploy_root>/releases`, xoá phần còn lại, rồi dọn cache trong `<deploy_root>/tmp`. Tuần trước một máy
mới được dựng với crontab thiếu tham số, và sáng hôm sau `/tmp` của máy đó trống trơn. Đừng chạy bản gốc trên máy
bạn ngoài sandbox của test.

**Phần 1: viết lại `starter/cleanup_releases.sh` tại chỗ**, giữ cách gọi `cleanup_releases.sh <deploy_root> [keep]`:

| Yêu cầu | Chi tiết |
| --- | --- |
| Tham số | `keep` mặc định `3`, phải là số nguyên `>= 1`. Thiếu `deploy_root`, `deploy_root` rỗng, `keep` sai (`abc`, `0`, `-1`, `2x`), hoặc hơn 2 tham số: stderr bắt đầu bằng `Usage:`, exit `2`, không xoá gì |
| `deploy_root` không tồn tại hoặc không có thư mục `releases` | Lỗi ra stderr, exit `1`, không gọi `rm` |
| Chọn release để xoá | Các **thư mục** con trực tiếp của `releases/`, sắp theo mtime mới nhất trước; giữ `keep` bản đầu, xoá phần còn lại |
| Bản đang chạy | Không bao giờ xoá release mà symlink `<deploy_root>/current` trỏ tới, kể cả khi nó cũ hơn `keep` bản mới nhất (khi đó nó được giữ thêm, không tính vào `keep`) |
| Tên lạ | Tên có dấu cách (`r5 old`), bắt đầu bằng `-` (`-hotfix`); đường dẫn `deploy_root` có dấu cách |
| Output | stdout chỉ gồm các dòng `removed <tên release>`, mỗi release đã xoá một dòng, thứ tự tuỳ ý; thông điệp khác ra stderr |
| `tmp/` | Có thì xoá **mọi** thứ bên trong, kể cả tệp ẩn và thư mục con, nhưng giữ thư mục `tmp`; không có thì bỏ qua |
| Kết thúc | Exit `0` khi chạy bình thường, kể cả khi không có gì để xoá |
| Cách xoá | Chỉ bằng `rm` gọi qua `PATH`. Phần code (không tính comment) không được chứa `/bin/rm`, `/usr/bin/rm`, `command rm`, `\rm`, `find -delete`, `unlink`, `rmdir`, `PATH=`, `env -i`, `sudo`, `mv`, `python`/`python3`/`perl`, `truncate`. Đây là tín hiệu dạy học (xoá dữ liệu đi qua đúng một đường, dễ review), không phải lớp an toàn |
| Chất lượng | `shellcheck -S style` không có cảnh báo nào |

Test chạy script trong sandbox bubblewrap (xem [Cài đặt](../../../README.md#0-cài-đặt)): `/` chỉ đọc, `/tmp` thật
bị che, chỉ thư mục tạm của test ghi được, môi trường biến dựng lại từ đầu; thiếu `bwrap` thì test skip. Sandbox là
lớp bảo vệ máy bạn: dù script đổi `PATH` hay gọi `/bin/rm`, nó chỉ chạm được vào thư mục tạm đó (`/run` và `~/.docker` cũng bị che, nên
không nhờ được Docker; mạng không bị tách). Bên trong sandbox,
thư mục làm việc là thư mục tạm của test, chứa vài tệp mồi, và một `rm` giả đứng đầu `PATH` ghi lại mọi lần gọi, chỉ
xoá thứ nằm trong thư mục tạm, từ chối mọi đường dẫn khác. Một script coi là hỏng nếu nó xoá tệp mồi trong thư mục làm
việc, hay gọi `rm` với đường dẫn ngoài thư mục tạm. Mỗi kiểm tra được chứng minh bắt được một lỗi có thật bằng cách chạy
nó (cũng trong sandbox) lên `tests/fixtures/cleanup_releases.original.sh`; riêng lỗi thiếu tham số được chứng minh bằng
đọc mã, không chạy bản gốc.

**Phần 2: điền `starter/REVIEW.md`**:

1. Bảng lỗi: ít nhất 6 dòng, mỗi dòng đủ 5 cột (dòng hoặc đoạn trong bản gốc, lỗi, hậu quả trên production, cách sửa).
2. Cách kiểm chứng: ít nhất 150 ký tự, bạn đã tái hiện lỗi thế nào (an toàn, trong thư mục tạm) và kiểm bản sửa ra
   sao.
3. Điều bản sửa vẫn chưa làm: ít nhất một gạch đầu dòng.

Không còn chữ `TODO` nào trong `REVIEW.md`.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/02-scripting/exercises/advanced/01-refactor-fragile-cleanup -q` pass toàn bộ.
  Test kiểm hành vi và khung `REVIEW.md`; chất lượng review chấm theo rubric trong
  `solutions/advanced/01-refactor-fragile-cleanup/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Mỗi lỗi trong `REVIEW.md` chỉ được tới một dòng cụ thể của bản gốc và một đầu vào làm nó lộ ra.

## Gợi ý

### Gợi ý 1

Chạy `shellcheck` lên bản gốc trước: SC2086 (thiếu ngoặc kép), SC2164 (`cd` không kiểm lỗi), SC2012 (parse `ls`) là
ba họ lỗi chính. Rồi tự hỏi với từng biến: nếu nó rỗng thì sao, nếu có dấu cách thì sao, nếu bắt đầu bằng `-` thì sao,
nếu `cd` thất bại thì các dòng sau chạy ở thư mục nào.

### Gợi ý 2

Danh sách release theo mtime mà không parse `ls`:
`find "$root/releases" -mindepth 1 -maxdepth 1 -type d -printf '%T@\t%f\0' | sort -z -t $'\t' -k1,1nr | cut -z -f2-`,
đọc vào mảng bằng `mapfile -d '' -t releases < <(...)` (Bash 4.4+). Tên release đang chạy:
`basename -- "$(readlink -- "$root/current")"`. Xoá cả tệp ẩn trong `tmp/`: `shopt -s nullglob dotglob` rồi
`entries=("$root/tmp"/*)` và chỉ gọi `rm -rf -- "${entries[@]}"` khi mảng không rỗng.
