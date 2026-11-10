# Lời giải: hiện trường "installer dừng ở xưởng"

Lời giải ở `install.sh` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/04-restricted-hosts/exercises/basic/02-installer-stops -q
```

Đo 2026-11-11 trên máy của repo: 60 s. Starter trên `lab-open`: thoát 0 (1114 tệp); trên `factory`: thoát 126 ngay bước
lập chỉ mục.

## Hai nguyên nhân, cả hai là baseline của máy xưởng

**1. `/tmp` là tmpfs `noexec`.** `findmnt /tmp` trên `factory`: `tmpfs … rw,nosuid,nodev,noexec,relatime,size=524288k`.
Installer cũ `mktemp -d` (mặc định `/tmp`), giải nén bundle vào đó rồi chạy `"$src/bin/fieldsync"`: `execve` bị từ chối
trên mount noexec, kể cả với script có shebang.

```
/home/fde/fs/install.sh: 16: /tmp/tmp.91MhoSpMlZ/fieldsync-1.4.0/bin/fieldsync: Permission denied
```

Mã 126 ("tìm thấy nhưng không chạy được"), không phải 127 ("không tìm thấy"). Trên `lab-open` `/tmp` nằm trên `/`,
chạy được, nên QA không bao giờ thấy.

**2. `nofile` cứng 1024.** Đổi riêng thư mục tạm (ví dụ `mktemp -d "$HOME/stage.XXXXXX"`) thì installer đi tiếp và chết ở:

```
OSError: [Errno 24] Too many open files: '/home/fde/stage.Lcn0Ji/fieldsync-1.4.0/assets/qc-01/32f88ba5ba.txt'
```

`fieldsync build-index` mặc định giữ **mọi** tệp mở cùng lúc (khoá đọc để chụp ảnh nhất quán) và tự nâng soft limit lên
hard limit như nhiều chương trình Go/Java. Trên `lab-open`: `ulimit -Sn` 1024, `ulimit -Hn` 1048576, nên nâng được và
1100–1400 tệp vừa. Trên `factory` IT đặt cả soft lẫn hard 1024 (`/etc/security/limits.d/`: `* soft nofile 1024`,
`* hard nofile 1024`; systemd `DefaultLimitNOFILE=1024:1024` cho cả service hệ thống lẫn user manager). User không nâng
hard được; nâng bằng root là đổi đúng thứ khách nói không đổi.

## Cách sửa

1. **Thư mục làm việc cạnh chỗ cài**, không ở `/tmp`: `mktemp -d "$HOME/.fieldsync-stage.XXXXXX"`. Cùng filesystem với
   `$HOME/fieldsync` nên bước cài là `mv` (đổi tên), không chép lần hai. Preflight `findmnt -no OPTIONS --target` báo lỗi
   rõ nếu cả chỗ đó cũng noexec.
2. **Đọc `ulimit -n` và thích nghi.** Nếu số tệp ≤ `ulimit -n` − 64 thì một đợt (giữ nguyên hành vi trên máy lab), không
   thì `--max-open $((nofile - 64))`. Biên 64 cho stdin/stdout/stderr, thư viện Python, tệp `index.json`. Giới hạn thấp tới
   mức không còn chỗ (dưới 80) thì dừng và nói cần nhờ IT việc gì. Lần chạy thứ hai của test dưới `ulimit -n` 400–700 kiểm
   đúng điểm này: một con số cố định ≥ giới hạn đó sẽ hỏng.
3. **Đánh đổi có chấp nhận được không?** `--max-open` làm ảnh chỉ nhất quán trong từng đợt. Lúc cài, `assets/` vừa được
   giải nén từ bundle vào thư mục riêng của installer, không ai ghi vào: nhất quán giữa các đợt không mất gì. Ghi điều này
   vào ticket gửi product (nên mặc định theo `ulimit -n` thay vì "mọi tệp").
4. Cài đè giữ bản cũ tới phút cuối: dựng bản mới trong thư mục stage, đổi tên `$HOME/fieldsync` cũ sang stage, đổi tên bản
   mới vào chỗ; lỗi thì trả bản cũ về. `trap` dọn stage khi thoát.

Các cách khác cũng đạt test: gọi `python3 "$src/bin/fieldsync"` (chạy interpreter từ `/usr/bin`, đọc script như dữ liệu)
và vẫn để stage trong `/tmp` (đạt, nhưng chỉ đúng với công cụ là script: binary thật trong bundle sẽ vẫn gãy); dùng
`TMPDIR` trỏ vào `$HOME`; `--max-open` nhỏ cố định (vd. 100: luôn an toàn, chậm hơn không đáng kể); `sudo prlimit --pid $$
--nofile=4096:4096` (máy `factory` có sudo, không đổi tệp cấu hình nào nên test vẫn đạt, nhưng đây là nâng giới hạn bằng
root mà khách không cho phép trên giấy: phải hỏi trước). Không đạt: sửa `/etc/fstab`, `mount -o remount,exec /tmp`, thêm
tệp vào `limits.d`, đổi `DefaultLimitNOFILE`.
