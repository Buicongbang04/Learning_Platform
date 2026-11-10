# Lời giải: Manifest sha256 cho bundle

Lời giải ở `manifest.py` cạnh tệp này:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/02-packaging-delivery/exercises/basic/01-bundle-manifest -q
```

## Cách làm

- `_walk(root)` đi cây bằng `os.walk`, phân loại từng mục bằng `lstat` (không theo link): thư mục bỏ qua, tệp thường và
  symlink được ghi nhận, tệp đặc biệt (FIFO, socket, device) thì `ValueError`. Symlink tới thư mục nằm trong `dirs` của
  `os.walk`, nên phải duyệt cả `dirs` lẫn `names`.
- `make_manifest` từ chối symlink, băm theo khối 1 MiB (`while chunk := handle.read(...)`), nên RAM không phụ thuộc kích
  thước tệp.
- `verify_manifest` kiểm đường dẫn **trước** khi ghép với `root`: tuyệt đối, có `..`, có `\` đều bị loại mà không mở
  tệp. Sau đó so kích thước rồi mới băm (tệp cụt bị bắt ngay mà không đọc hết), symlink coi như sai.

## Vì sao từng quy tắc

| Quy tắc | Lỗi ngoài hiện trường nó chặn |
| --- | --- |
| Có `size` cạnh `sha256` | Installer tính được dung lượng cần **trước** khi giải nén; so kích thước là cách rẻ nhất bắt tệp chép thiếu |
| Báo tệp thừa | Ai đó "tiện tay" chép thêm `debug.py` hay `.env` vào bundle; tệp lạ chạy được trên máy khách là sự cố bảo mật |
| Từ chối `..`/đường dẫn tuyệt đối | Manifest là dữ liệu từ bên ngoài; `verify` mà đi đọc `/etc/shadow` hay ghi ra ngoài thư mục cài là lỗ hổng kiểu "zip slip" |
| Từ chối symlink | `models -> /mnt/share/models` chạy ở lab, ở khách trỏ vào hư không, hoặc tệ hơn là vào dữ liệu của khách |
| Manifest không tự băm | Băm chính nó là vòng lặp; tính toàn vẹn của manifest đến từ **chữ ký** hoặc sha256 của cả bundle gửi qua kênh khác (xem README module) |

Thêm một điều bài không chấm nhưng nên làm: so sánh digest bằng `hmac.compare_digest` không cần ở đây (không có bí mật),
nhưng **in** đủ danh sách vấn đề thay vì dừng ở lỗi đầu tiên giúp người ở hiện trường đoán được nguyên nhân (thiếu cả thư
mục `models/` ⇒ chép thiếu; sai một tệp lớn ⇒ USB hỏng).
