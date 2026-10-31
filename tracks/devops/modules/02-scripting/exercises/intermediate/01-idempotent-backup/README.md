---
title: Backup Postgres hằng ngày idempotent, có khoá, trap và retention
level: intermediate
services: []
files:
  - path: starter/backup.sh
    note: 6 TODO
  - path: tests/test_backup.py
    note: Không sửa; test đặt một pg_dump giả lên đầu PATH, không cần Docker
run:
  - uv run pytest tracks/devops/modules/02-scripting/exercises/intermediate/01-idempotent-backup -q
  - PGPASSWORD=olist bash tracks/devops/modules/02-scripting/exercises/intermediate/01-idempotent-backup/starter/backup.sh /tmp/olist-backups
---

## Mục tiêu

Viết script backup mà cron hay systemd timer gọi bao nhiêu lần cũng không hỏng: chạy lại trong ngày không tạo bản
thừa, không bao giờ để lại tệp dump dở dang dưới tên thật, hai bản chạy chồng nhau không giẫm lên nhau, bị dừng giữa
chừng thì tự dọn, và chỉ xoá bản cũ khi bản mới đã chắc chắn tốt.

## Đề bài

Viết `starter/backup.sh [-k số_bản_giữ] <thư_mục_backup>` sao lưu database Olist Shop bằng `pg_dump`:

1. **Tham số.** `-k` là số nguyên `>= 1`, mặc định `7`. Đúng một tham số vị trí (không rỗng) là thư mục backup.
   Ngày của bản backup lấy từ biến `BACKUP_DATE`, mặc định `date -u +%F` (ngày UTC, dạng `YYYY-MM-DD`). `BACKUP_DATE`
   không đúng dạng `YYYY-MM-DD` (đúng 4-2-2 chữ số) là lỗi, exit `2`.
2. **Kết nối.** Export `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE` với mặc định `localhost`, `25432`, `olist`,
   `olist` (giá trị có sẵn trong môi trường thì giữ nguyên) để `pg_dump` đọc. Không truyền host, port, user, database,
   mật khẩu bằng tham số dòng lệnh. Mật khẩu đến từ `PGPASSWORD` hoặc `~/.pgpass` có sẵn; không in nó ra.
3. **Quyền.** Tệp tạo ra (dump, checksum, khoá) chỉ chủ đọc ghi được (`0600`). Thư mục backup chưa có thì tạo (kể cả
   thư mục cha) với quyền `0700`.
4. **Khoá.** Giữ khoá `flock -n` trên tệp `<thư_mục>/.backup.lock` trong suốt thời gian chạy. Đang có bản khác giữ
   khoá: báo lỗi ra stderr, exit `75` ngay, không chờ, không đụng tệp nào khác.
5. **Idempotent.** Tên bản backup là `olist-<BACKUP_DATE>.dump`. Nếu tệp này **và** `olist-<BACKUP_DATE>.dump.sha256`
   đã có và checksum khớp: in `skip <thư_mục>/olist-<ngày>.dump`, exit `0`, không gọi `pg_dump`, không đổi tệp nào. Có
   tệp mà checksum sai hoặc thiếu tệp checksum: coi như hỏng, sao lưu lại.
6. **Dump an toàn.** Gọi `pg_dump` định dạng custom (`-Fc` hoặc `--format=custom`) ghi vào một **tệp tạm trong chính
   thư mục backup** (tên bắt đầu bằng dấu chấm, ví dụ tạo bằng `mktemp "<thư_mục>/.olist-<ngày>.dump.XXXXXX"`). Dump
   lỗi (exit khác `0`) hoặc tệp rỗng: báo lỗi ra stderr, exit `1`, stdout rỗng. Thành công: ghi checksum dạng của
   `sha256sum` (`<hash>  olist-<ngày>.dump`, hai dấu cách, tên tệp không kèm thư mục, để `sha256sum -c` chạy được trong
   thư mục backup), đổi tên tệp tạm thành tên thật bằng `mv`, in `created <thư_mục>/olist-<ngày>.dump`.
7. **Dọn dẹp.** Mọi đường thoát (lỗi, `SIGINT`, `SIGTERM`) không để lại tệp tạm nào. Trong một test, `pg_dump`
   giả ghi dở rồi gửi `SIGTERM` cho cả process group của nó (`kill -TERM 0`, giống systemd hay Ctrl+C dừng một
   service): script phải thoát với mã khác `0`, stdout rỗng, không còn tệp tạm, không có tệp `olist-<ngày>.dump`, và
   lần chạy ngay sau đó tạo được bản backup. Trong test khác, bản đang giữ khoá bị `SIGKILL` (không trap được); lần
   chạy sau đó phải lấy được khoá.
8. **Retention.** Chỉ sau khi tạo bản mới thành công: giữ `-k` tệp tên đúng mẫu `olist-YYYY-MM-DD.dump` mới nhất
   (so theo ngày trong tên), xoá các bản cũ hơn cùng tệp `.sha256` của chúng. Không đụng tệp nào khác trong thư mục
   (`notes.txt`, `olist-manual.dump`...). Khi dump lỗi hoặc khi `skip`, không xoá gì.

| Tình huống | Exit | stdout |
| --- | --- | --- |
| Tạo bản mới | `0` | `created <đường dẫn>` |
| Đã có bản hợp lệ của ngày đó | `0` | `skip <đường dẫn>` |
| `pg_dump` lỗi hoặc dump rỗng | `1` | rỗng |
| Option lạ, `-k` không hợp lệ, thiếu hoặc thừa tham số vị trí | `2` | rỗng; stderr bắt đầu bằng `Usage:`; không gọi `pg_dump` |
| `BACKUP_DATE` sai dạng | `2` | rỗng; lỗi ra stderr; không gọi `pg_dump` |
| Bản khác đang giữ khoá | `75` | rỗng; lỗi ra stderr |

`<đường dẫn>` là `<thư_mục>/olist-<ngày>.dump`, với `<thư_mục>` đúng như tham số bạn truyền (bỏ dấu `/` cuối nếu có).
Test truyền một đường dẫn có dấu cách (`.../my backups/olist`). Thông điệp log (thời điểm, đã xoá bản nào) ra stderr.

Test đặt một `pg_dump` giả lên đầu `PATH`. Nó ghi lại tham số và các biến `PG*` nó nhận được, và tuỳ chế độ sẽ ghi một
dump giả, ghi dở rồi trả lỗi, tạo tệp rỗng, hoặc ghi dở rồi chờ (để thử khoá và tín hiệu). Bài cần Linux: `flock`
(gói util-linux) và `sha256sum` (coreutils); thiếu thì test skip.

Mọi test chạy script của bạn trong sandbox bubblewrap (xem [Cài đặt](../../../README.md#0-cài-đặt)): `/` chỉ đọc, `/tmp` thật bị che, thư mục làm việc và thư mục duy nhất ghi được là thư mục tạm của test, môi trường biến dựng lại từ đầu (chỉ có `PATH`, `HOME` trỏ vào thư mục tạm, `LANG`/`LC_ALL`, cộng các biến test đặt). Thiếu `bwrap` thì test skip. `PGHOST`... của bạn
không lọt vào, nên test thấy đúng giá trị mặc định.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/02-scripting/exercises/intermediate/01-idempotent-backup -q` pass toàn bộ, gồm
  `shellcheck -S style` sạch.
- Khi Olist Shop đang chạy, `PGPASSWORD=olist bash starter/backup.sh /tmp/olist-backups` tạo bản dump thật, chạy lại in
  `skip`, và `pg_restore --list /tmp/olist-backups/olist-<ngày>.dump` đọc được (cần `pg_dump`/`pg_restore` 16 trên
  máy, hoặc chạy bằng `docker compose exec postgres`).
- Giải thích được vì sao tệp tạm phải nằm cùng thư mục với tệp đích, và vì sao retention phải chạy **sau** khi bản mới
  thành công.
- Nói được backup này còn thiếu gì để gọi là chiến lược backup: bản sao ngoài máy, mã hoá, kiểm restore định kỳ, RPO.

## Gợi ý

### Gợi ý 1

Khoá bằng file descriptor để khoá sống đúng bằng đời tiến trình: `exec 9>"$dir/.backup.lock"` rồi
`flock -n 9 || exit 75`. Tiến trình chết vì bất cứ lý do gì, kernel đóng fd và khoá tự nhả; không có "PID file cũ"
phải dọn. Kiểm checksum có sẵn: `(cd -- "$dir" && sha256sum --status -c -- "$name.sha256")`.

### Gợi ý 2

Đặt `tmp=""` trước, `trap cleanup EXIT` với `cleanup` xoá `$tmp` nếu khác rỗng, và `trap 'exit 130' INT`,
`trap 'exit 143' TERM` để tín hiệu đi qua đường `exit` (kích hoạt trap `EXIT`). Sau khi `mv` thành công, đặt lại
`tmp=""` để cleanup không xoá nhầm. Liệt kê bản cũ: `find "$dir" -maxdepth 1 -type f -name 'olist-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].dump' -printf '%f\n' | LC_ALL=C sort -r | tail -n +$((keep + 1))`.
