# Lời giải: quét quyền tệp nguy hiểm trong thư mục release

Script đầy đủ ở `perm_audit.sh` cạnh tệp này.

## Cách làm

1. **Kiểm tham số trước**, lỗi dùng sai trả `2` (quy ước của nhiều công cụ Unix: `grep`, `diff`). Exit `1` dành cho
   "chạy đúng và có phát hiện", để pipeline CI phân biệt "script hỏng" với "release có vấn đề".
2. **Một hàm `report` bọc `find`**: `find . <điều kiện> -printf "<loại> %P\n"`. Sáu loại là sáu lệnh `find`, mỗi lệnh
   đọc như một câu: tệp thường, other ghi được; thư mục other ghi được và không có sticky; v.v.
3. **Chạy trong subshell `$( cd "$root"; ... )`** nên `cd` không ảnh hưởng phần còn lại, và `%P` cho đường dẫn tương đối
   sạch dù tham số là `.`, đường dẫn tuyệt đối hay có dấu cách.
4. **Sắp một lần với `LC_ALL=C`**: thứ tự theo byte giống nhau trên mọi máy; locale `en_US.UTF-8` bỏ qua dấu câu khi so
   nên `world-writable-dir` và `world-writable app/...` có thể đổi chỗ tuỳ máy.
5. **Không đụng quyền**: bước kiểm chỉ báo. Sửa tự động (`chmod o-w`) trong bước release dễ che mất nguyên nhân (ai,
   công cụ nào tạo ra tệp `0666`) và có thể làm hỏng thư mục cố ý dùng chung.

## Đọc bit quyền

| Bit | Số | Trên tệp | Trên thư mục |
| --- | --- | --- | --- |
| setuid | `4000` | Chạy với UID của **chủ tệp** (ví dụ `passwd` chạy như root) | Bị bỏ qua trên Linux |
| setgid | `2000` | Chạy với GID của group sở hữu | Tệp tạo mới thừa kế group của thư mục (thư mục dùng chung của team) |
| sticky | `1000` | Không còn ý nghĩa | Chỉ chủ tệp (hoặc chủ thư mục, root) được xoá hoặc đổi tên tệp trong đó, như `/tmp` |

- **`0777` so với `1777`**: thư mục ai cũng ghi được mà không có sticky thì bất kỳ user nào cũng xoá hoặc thay tệp của
  người khác, kể cả tệp cấu hình hay script mà service sẽ đọc. Sticky bit giữ lại quyền tạo tệp nhưng chặn xoá chéo.
- **setuid trên script**: Linux bỏ qua setuid trên script có shebang (vì race condition giữa lúc kernel đọc shebang và
  lúc interpreter mở tệp). Bit này trên một script trong release gần như chắc chắn là nhầm lẫn, còn trên một binary
  là một đường leo thang quyền phải có người duyệt.
- **Khoá riêng `0640`**: `ssh` từ chối dùng khoá có quyền group/other ("UNPROTECTED PRIVATE KEY FILE"), nhưng Nginx,
  Postgres hay app Python thì không, nên khoá TLS để `0640` với group `www-data` rộng là một lỗ thật.
- **`.env` `0644`**: mọi user trên máy, kể cả user của service khác bị chiếm quyền, đọc được mật khẩu database.

## Dùng trong thực tế

- Chạy trong CI trước bước đóng gói, và chạy định kỳ trên server với thư mục `/opt/olist-shop`, `/etc/olist-shop`.
- Nguyên nhân gốc hay gặp của `0666` là `umask 000` trong Dockerfile hoặc script deploy, và `chmod -R 777` "cho chạy
  được". Sửa `umask` (xem lý thuyết phần 2) thay vì sửa từng tệp.
- Quét toàn máy tìm setuid: `find / -xdev -type f -perm -4000 2>/dev/null` rồi so với danh sách đã biết; công cụ như
  Lynis, OpenSCAP hoặc CIS benchmark làm việc này có hệ thống.
