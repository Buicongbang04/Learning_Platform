# Lời giải: dọn log đã xoay vòng bằng find

Script đầy đủ ở `prune.sh` cạnh tệp này.

## Cách làm

1. **`getopts` rồi kiểm.** Giá trị mặc định đặt trước vòng lặp, kiểm bắt buộc và kiểu sau vòng lặp. `[[ $days =~
   ^[1-9][0-9]*$ ]]` loại cả `0`, `-1`, `7x`, và chuỗi rỗng.
2. **Chặn thư mục cấp cao trước khi chạm vào gì.** `realpath -e` giải mọi symlink và `..`, trả lỗi nếu đường dẫn không
   tồn tại. Đếm số dấu `/` trong kết quả: dưới 2 nghĩa là `/` hoặc `/xxx`. Đây là lưới an toàn cuối, không thay cho việc
   cấu hình đúng; nhưng một biến rỗng trong cron (`-d "$LOG_DIR"` khi `LOG_DIR` chưa được đặt, cộng một bản sửa vội
   đổi thành `-d "$LOG_DIR/"`) là chuyện xảy ra thật.
3. **Để `find` làm phần lọc.** `-xdev` không đi sang filesystem khác (một NFS mount trong thư mục log), `-type f` bỏ
   thư mục và symlink, `-name` so mẫu chỉ trên tên, `-mtime +N` theo đúng ngữ nghĩa làm tròn của `find`.
4. **`-print0` và `read -d ''`.** Byte NUL là ký tự duy nhất không thể có trong đường dẫn Unix; dấu cách, tab, xuống
   dòng đều có thể. `IFS=` giữ khoảng trắng đầu cuối, `-r` giữ dấu `\`.
5. **`rm -f -- "$file"`.** `--` để tên `-rf.log.4` không thành option. Với tên do `find "$dir"` sinh ra, đường dẫn luôn
   bắt đầu bằng `$dir`, nên chỉ nguy hiểm khi `$dir` bắt đầu bằng `-`; thói quen `--` vẫn đáng giữ vì bạn sẽ chép đoạn
   này sang chỗ khác.
6. **Dry-run đi cùng đường code với chạy thật**, chỉ khác bước `rm`. Dry-run viết thành nhánh riêng dễ lệch dần khỏi
   chạy thật, và mất giá trị đúng lúc cần nó.

## `find -mtime` làm tròn thế nào

`find` tính tuổi = (bây giờ − mtime) / 86400, **bỏ phần lẻ**, rồi so sánh: `-mtime +7` là tuổi nguyên `> 7`, tức ít nhất
8 ngày tròn. `-mtime 7` là đúng 7 (từ 7 tới dưới 8 ngày), `-mtime -7` là dưới 7. Muốn tính theo phút dùng `-mmin`, muốn
mốc theo đầu ngày dùng `-daystart`. Người viết `-mtime +7` nghĩ "cũ hơn 7 ngày" thường giữ log thêm gần một ngày so với
ý mình; với chính sách lưu trữ có ràng buộc pháp lý (GDPR: xoá đúng hạn; PCI DSS: giữ ít nhất 1 năm), phải biết điều đó.

## Khi nào không viết script này

| Công cụ | Hợp khi | Ghi chú |
| --- | --- | --- |
| logrotate (`rotate 14`, `maxage 30`, `compress`) | Log của service ghi ra tệp | Đã có sẵn trên mọi distro; xoay **và** xoá trong một chỗ; `copytruncate` hay `postrotate` + `SIGHUP`/`USR1` để service mở tệp mới |
| `systemd-tmpfiles` (`e /var/log/olist - - - 14d`) | Dọn thư mục theo tuổi, có systemd | Khai báo, không phải code; chạy bằng timer có sẵn |
| journald (`SystemMaxUse=`, `MaxRetentionSec=`) | Log đi qua journal | Không có tệp để xoá |
| Script như bài này | Thư mục do ứng dụng tự đặt tên tệp, cần dry-run, cần log ra nơi khác trước khi xoá | Phải tự lo khoá, giám sát, test |

Bài học lớn hơn của bài: một script xoá tệp cần **dry-run**, **danh sách những gì đã xoá**, **chặn đầu vào nguy
hiểm** và **test chạy trên thư mục giả**. Thiếu một trong bốn thì sớm muộn sẽ có người xoá nhầm.
