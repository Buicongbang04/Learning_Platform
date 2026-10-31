---
title: "Sự cố: /var đầy 100% nhưng du chỉ thấy một nửa"
level: advanced
services: []
files:
  - path: starter/RUNBOOK.md
    note: Khung runbook, điền mọi TODO
  - path: tests/test_runbook.py
    note: Không sửa; kiểm khung và con số chẩn đoán, chất lượng chấm theo rubric
run:
  - uv run pytest tracks/devops/modules/01-linux-terminal/exercises/advanced/01-disk-full-deleted-files -q
---

## Mục tiêu

Xử lý một sự cố đĩa đầy theo cách của người trực senior: chẩn đoán bằng bằng chứng thay vì xoá bừa, giải phóng chỗ mà
không làm mất dữ liệu hay dừng dịch vụ lâu, tìm ra cơ chế gây lỗi, và để lại một runbook mà người trực sau làm theo
được lúc 3 giờ sáng.

## Đề bài

Bạn trực đêm. Đây là những gì đã xảy ra và những gì người trực trước đã chụp được trên `olist-app-02` (Ubuntu 24.04,
chạy API và worker của Olist Shop bằng systemd).

**Dòng thời gian**

- 27/10, một đồng nghiệp thêm cấu hình logrotate cho thư mục log của worker (trước đó log không được xoay). Worker
  đã chạy liên tục 9 ngày.
- 28/10 02:30 timer backup chạy, `pg_dump` ghi vào `/var/backups/olist-shop` và fail với `No space left on device`.
- 03:05 alert `DiskFull /var 100%`. API trả `500` cho mọi request upload ảnh sản phẩm; checkout vẫn chạy.
- 03:20 người trực trước tìm tệp lớn, thấy `/var/log/olist-shop/worker.log.1` khoảng 20 GB và
  `worker-access.log.1` khoảng 7,5 GB, xoá cả hai bằng `rm`. `du` giảm, `df` **không đổi**. Anh ấy bàn giao cho bạn.

**Output đã chụp lúc 03:40**

```text
$ df -h /var
Filesystem      Size  Used Avail Use% Mounted on
/dev/sdb1        59G   56G     0 100% /var

$ df -i /var
Filesystem      Inodes IUsed  IFree IUse% Mounted on
/dev/sdb1      3932160 98412 3833748    3% /var

$ sudo du -xsh /var
28G     /var

$ ls -la /var/log/olist-shop/
total 8
drwxr-x--- 2 olist olist    4096 Oct 28 03:20 .
drwxrwxr-x 14 root syslog   4096 Oct 28 00:00 ..
-rw-r----- 1 olist olist       0 Oct 28 00:00 worker-access.log
-rw-r----- 1 olist olist       0 Oct 28 00:00 worker.log

$ cat /etc/logrotate.d/olist-shop
/var/log/olist-shop/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 olist olist
}

$ systemctl show -p MainPID olist-worker
MainPID=2481

$ ps -o pid,ppid,user,etime,cmd -p 2481,2519
    PID    PPID USER     ELAPSED CMD
   2481       1 olist   9-04:12:51 /opt/olist-shop/.venv/bin/python -m olist_shop.worker
   2519    2481 olist   9-04:12:50 /opt/olist-shop/.venv/bin/python -m olist_shop.worker --child

$ sudo lsof -nP +L1
COMMAND    PID     USER   FD   TYPE DEVICE    SIZE/OFF NLINK    NODE NAME
rsyslogd   811   syslog    9w   REG   8,17   104857600     0  262201 /var/log/syslog.1 (deleted)
python3   2481    olist    3w   REG   8,17 21474836480     0  393228 /var/log/olist-shop/worker.log.1 (deleted)
python3   2481    olist    5w   REG   8,17  8053063680     0  393301 /var/log/olist-shop/worker-access.log.1 (deleted)
python3   2519    olist    3w   REG   8,17 21474836480     0  393228 /var/log/olist-shop/worker.log.1 (deleted)
python3   2519    olist    5w   REG   8,17  8053063680     0  393301 /var/log/olist-shop/worker-access.log.1 (deleted)
node      4410    olist   27u   REG  259,2  2147483648     0 1835041 /tmp/.npm-cache/_cacache/tmp/4a1f9c2e (deleted)

$ findmnt -no SOURCE,MAJ:MIN /var /
/dev/sdb1 8:17
/dev/nvme0n1p2 259:2
```

Viết `starter/RUNBOOK.md`, giữ nguyên 6 heading đánh số:

1. **Triệu chứng và tác động**: cái gì hỏng, ai bị ảnh hưởng, cái gì vẫn chạy.
2. **Chẩn đoán**: lệnh đã chạy và cách đọc; vì sao `df` và `du` lệch nhau; bảng `PID | Tiến trình | Tệp | Dung lượng
   (GiB)` liệt kê **mọi** tiến trình đang giữ dung lượng trên `/var`; và dòng
   `Tổng dung lượng thu hồi được: <số> GiB` (1 GiB = 1024³ byte).
3. **Khắc phục tức thời**: các bước có thứ tự, mỗi bước nói rõ rủi ro; có bước đo lại.
4. **Nguyên nhân gốc**: cơ chế, không phải "người trực xoá nhầm".
5. **Phòng ngừa**: ít nhất 3 việc.
6. **Kiểm chứng sau khắc phục**: dấu hiệu nào cho biết đã ổn và sẽ không tái diễn đêm mai.

## Tiêu chí đạt

- `uv run pytest tracks/devops/modules/01-linux-terminal/exercises/advanced/01-disk-full-deleted-files -q` pass: không
  còn TODO, đủ 6 phần đúng thứ tự, bảng có đúng các PID, con số thu hồi đúng, có lệnh chẩn đoán và bước `df`. Test chỉ
  kiểm khung; chất lượng chấm theo rubric trong `solutions/advanced/01-disk-full-deleted-files/SOLUTION.md`.
- Đạt ít nhất 70/100 điểm rubric khi tự chấm.
- Phương án khắc phục không làm mất job đang xử lý của worker, hoặc nói rõ vì sao chấp nhận mất.

## Gợi ý

### Gợi ý 1

Một tệp chiếm chỗ trên đĩa chừng nào inode của nó còn được tham chiếu: bởi tên trong thư mục (cột `NLINK`) **hoặc**
bởi một file descriptor đang mở. `rm` chỉ xoá tên. Trong output của `lsof`, đọc kỹ cột `DEVICE` (filesystem nào) và
`NODE` (inode nào): hai dòng cùng `NODE` trên cùng `DEVICE` là **một** tệp.

### Gợi ý 2

Có hai cách trả lại chỗ: làm tiến trình đóng file descriptor (restart, hoặc signal để ứng dụng mở lại tệp log), hoặc
cắt tệp về 0 byte qua đường dẫn `/proc/<pid>/fd/<số>` mà không cần dừng tiến trình. Cân nhắc cái giá của mỗi cách với
một worker đang chạy job, và với chính nội dung log (có cần giữ cho điều tra không). Rồi tự hỏi: vì sao worker vẫn ghi
vào `worker.log.1` sau khi logrotate đã đổi tên nó lúc 00:00, và đêm mai chuyện gì sẽ xảy ra nếu không ai `rm`?
