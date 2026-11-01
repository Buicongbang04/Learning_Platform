# Hướng làm: /var đầy 100% nhưng du chỉ thấy một nửa

Bài Advanced không có một đáp án duy nhất. Phần dưới gồm nguyên nhân, cách tính con số, một runbook mẫu, các quyết
định cần cân nhắc và rubric.

## Nguyên nhân (đề không nói)

Tệp log đã bị xoá tên nhưng worker vẫn giữ file descriptor mở, nên inode và toàn bộ block của nó vẫn nằm trên đĩa.
`du` đi theo cây thư mục nên không thấy; `df` hỏi filesystem còn bao nhiêu block trống nên thấy.

Chuỗi sự kiện:

1. Worker chạy 9 ngày, ghi vào `worker.log` không được xoay, tệp lớn dần tới khoảng 20 GB.
2. Lúc 00:00 ngày 28, lần rotate đầu tiên đổi tên `worker.log` thành `worker.log.1` và tạo `worker.log` rỗng (`create`).
   Đổi tên không đổi inode, nên worker vẫn ghi tiếp vào inode cũ, giờ mang tên `worker.log.1`. Cấu hình không có
   `postrotate` để báo worker mở lại tệp, và worker cũng không xử lý `SIGHUP` để mở lại. Bằng chứng: `worker.log`
   mới vẫn 0 byte sau hơn 3 giờ.
3. Lúc 03:20, `rm` xoá tên `worker.log.1`. Inode chỉ còn được giữ bởi FD của tiến trình 2481 và 2519 (2519 là tiến
   trình con, thừa hưởng FD qua `fork()`), nên dung lượng không được trả lại.
4. Dù không ai `rm`, đêm sau cũng tới đúng tình trạng này: `delaycompress` chỉ hoãn việc nén một ngày, lần rotate kế
   tiếp nén `.1` thành `.2.gz` rồi xoá `.1` trong khi worker vẫn ghi vào nó. Từ đó mọi dòng log mới đều đi vào một
   tệp không tên và không ai đọc được, cho tới khi đầy đĩa.

## Cách tính con số

Lọc `DEVICE` 8,17 (`/dev/sdb1` là `/var` theo `findmnt`), bỏ dòng `node` 4410 vì nằm ở `/tmp` trên `259,2`. Gộp theo
`NODE`:

| NODE | Tệp | Byte | GiB |
| --- | --- | --- | --- |
| 393228 | `worker.log.1` | 21 474 836 480 | 20,000 |
| 393301 | `worker-access.log.1` | 8 053 063 680 | 7,500 |
| 262201 | `/var/log/syslog.1` | 104 857 600 | 0,098 |

Tổng 27,6 GiB, khớp với khoảng lệch `df` 56G trừ `du` 28G. Hai lỗi hay gặp: cộng theo dòng (gấp đôi, 55,1 GiB) và
cộng cả tệp ở `/tmp` (29,6 GiB). Lệnh tự động:

```bash
sudo lsof -nP +L1 /var | awk 'NR > 1 && !seen[$6 FS $9]++ { sum += $7 } END { printf "%.1f GiB\n", sum / 2^30 }'
```

Truyền mount point (`lsof +L1 /var`) để lsof tự lọc filesystem. Không có `lsof`:
`sudo find /proc/[0-9]*/fd -lname '*(deleted)' -printf '%p -> %l\n'`.

## Runbook mẫu

```markdown
# Runbook: /var đầy trên olist-app-02

## 1. Triệu chứng và tác động

- `/var` 100%, `df` báo 56G dùng nhưng `du -xsh /var` chỉ 28G.
- Upload ảnh sản phẩm trả 500 (API ghi tệp tạm vào /var/lib/olist-shop); backup 02:30 fail, tức là đêm nay chưa có
  bản backup nào. Checkout vẫn chạy vì không ghi đĩa cục bộ.
- Inode chỉ dùng 3%, nên không phải hết inode.

## 2. Chẩn đoán

`df` và `du` lệch 28G: dung lượng bị giữ bởi tệp đã xoá tên nhưng còn được tiến trình mở. Kiểm bằng
`sudo lsof -nP +L1 /var` (NLINK 0 là tệp không còn tên nào), đọc cột DEVICE để chỉ lấy /var (8,17) và cột NODE để
gộp các FD cùng inode. PID 2519 là tiến trình con của 2481, thừa hưởng FD qua fork, nên cùng một inode xuất hiện hai lần.

| PID | Tiến trình | Tệp | Dung lượng (GiB) |
| --- | --- | --- | --- |
| 2481 | olist-worker (chính) | worker.log.1, worker-access.log.1 | 27,5 (dùng chung với 2519) |
| 2519 | olist-worker (con) | worker.log.1, worker-access.log.1 | cùng inode với 2481, không cộng thêm |
| 811 | rsyslogd | /var/log/syslog.1 | 0,1 |

Tổng dung lượng thu hồi được: 27,6 GiB

## 3. Khắc phục tức thời

1. Báo kênh sự cố: đang xử lý, chưa restart gì; checkout không ảnh hưởng.
2. Lấy lại chỗ mà không dừng worker: `sudo sh -c ': > /proc/2481/fd/3'` và `: > /proc/2481/fd/5` cắt hai tệp về 0
   byte. Rủi ro: mất 27,5 GiB log của ngày 27–28/10. Nếu cần giữ cho điều tra, chép 1 GB cuối trước:
   `sudo tail -c 1G /proc/2481/fd/3 > /srv/incident/worker-tail.log` (ra filesystem khác).
3. `df -h /var` phải còn khoảng 27G trống. Kiểm upload ảnh trả 200 lại.
4. Gửi `sudo systemctl kill -s HUP rsyslog` để rsyslog mở lại tệp, trả 0,1 GiB còn lại.
5. Chạy lại backup bằng tay: `sudo systemctl start olist-backup.service`, theo dõi `journalctl -u olist-backup -f`.
6. Worker vẫn ghi vào FD đã cắt (tệp không tên). Trong giờ thấp điểm sáng mai, `systemctl restart olist-worker`
   (worker trả job đang dở khi nhận SIGTERM, TimeoutStopSec 30s) để nó mở lại worker.log đúng tên.

## 4. Nguyên nhân gốc

Logrotate dùng `create`: đổi tên tệp đang mở rồi tạo tệp mới, nhưng không có `postrotate` báo worker mở lại tệp, và
worker không biết mở lại khi nhận SIGHUP. Worker tiếp tục ghi vào inode cũ dưới tên worker.log.1 suốt từ 00:00
(worker.log mới vẫn 0 byte). Lúc 03:20, `rm` chỉ xoá tên; inode vẫn được FD của worker giữ nên block không được trả.
Dù không ai rm, đêm sau logrotate cũng nén rồi xoá .1 và dẫn tới cùng tình trạng. Cấu hình logrotate mới được thêm
hôm qua mà không thử với một worker đang chạy.

## 5. Phòng ngừa

- Worker ghi log ra stdout để journald quản lý (StandardOutput=journal, giới hạn SystemMaxUse=), bỏ tệp log riêng. Chủ:
  team app, 2 tuần.
- Trong lúc chờ, thêm `postrotate systemctl kill -s HUP olist-worker` và xử lý SIGHUP trong worker (logging
  WatchedFileHandler); không dùng copytruncate vì mất dòng log giữa lúc chép và cắt.
- Alert khi `df` và `du` lệch quá 10%, và alert dự báo đầy bằng `predict_linear` trên metric node_exporter (module 13)
  thay cho ngưỡng 100%.
- Tách /var/log khỏi /var/lib và /var/backups (filesystem hoặc quota riêng) để log đầy không chặn backup và upload.
- Review thay đổi cấu hình logrotate như code: thử trên staging bằng `logrotate -f` với worker đang chạy, kiểm
  `lsof +L1` sau đó.
- Cập nhật runbook DiskFull: bước đầu tiên là so `df` với `du`, không `rm` tệp log đang được mở.

## 6. Kiểm chứng sau khắc phục

- `df -h /var` dưới 60% sau khi cắt tệp; `sudo lsof -nP +L1 /var` không còn dòng nào sau khi restart worker.
- Backup chạy lại thành công, có tệp mới trong /var/backups/olist-shop, `systemctl list-timers` hiện lần chạy kế tiếp.
- Sáng hôm sau, sau lần rotate 00:00: `ls -la /var/log/olist-shop` cho thấy worker.log mới có dữ liệu và
  `lsof +L1` vẫn rỗng.
```

## Các quyết định cần cân nhắc

- **Cắt tệp hay restart?** Cắt qua `/proc/<pid>/fd` trả chỗ ngay, worker không dừng, nhưng mất log và worker vẫn ghi
  vào tệp không tên (sẽ đầy lại sau vài ngày). Restart ngay sạch hơn nhưng giữa đêm, mỗi lần restart worker là một
  rủi ro (job dở, kết nối lại Redis). Cả hai đều chấp nhận được nếu nói rõ cái giá.
- **Không bao giờ** "dọn" bằng cách `rm` thêm tệp khác (backup cũ, tệp trong `/var/lib/postgresql`): không giải quyết
  được gì và có thể mất dữ liệu thật.
- **`copytruncate`** là cách nhanh nhất để logrotate không cần ứng dụng hợp tác, nhưng mất dòng log ghi giữa lúc chép
  và lúc cắt, và phải chép cả tệp lớn. Đẩy log ra stdout/journald là hướng đúng cho service mới và khớp với container
  (module 06).
- **Ai giữ FD?** Tiến trình con thừa hưởng FD; restart chỉ tiến trình chính mà con còn sống (không cùng cgroup) thì
  chỗ vẫn không trả. `systemctl restart` dừng cả cgroup nên an toàn.

## Rubric (100 điểm)

| Tiêu chí | Điểm | Đạt đủ khi |
| --- | --- | --- |
| Chẩn đoán đúng cơ chế | 20 | Nêu được inode còn được FD giữ, giải thích vì sao `du` không thấy và `df` thấy; loại trừ inode đầy |
| Con số chính xác | 10 | 27,6 GiB (hoặc 27,5 nếu bỏ syslog); gộp theo inode, lọc theo filesystem, nói rõ cách tính |
| Khắc phục an toàn | 20 | Có thứ tự, mỗi bước nêu rủi ro; không xoá thêm dữ liệu; có phương án giữ log nếu cần điều tra; không làm mất job của worker hoặc nói rõ vì sao chấp nhận |
| Khôi phục phần bị ảnh hưởng | 10 | Nhớ chạy lại backup bị fail và kiểm upload; báo cáo tác động |
| Nguyên nhân gốc | 15 | Logrotate `create` không có `postrotate` + worker không mở lại tệp; thấy được đêm sau sẽ tái diễn dù không ai `rm`; không đổ lỗi cho người trực |
| Phòng ngừa | 15 | Ít nhất 3 việc thay đổi hệ thống (không chỉ "cẩn thận hơn"), có chủ và hạn; có alert sớm |
| Kiểm chứng | 10 | Tín hiệu đo được, gồm kiểm sau lần rotate kế tiếp |

Từ 70 điểm là đạt; dưới 50 thường là runbook dừng ở "restart worker" mà không giải thích vì sao nó có tác dụng.
