# Lời giải: cache-aside cho trang sản phẩm

## Cách làm

- `get`: `GET` trước. Redis trả `None` nghĩa là miss; chuỗi `"__none__"` nghĩa là "đã biết là không tồn tại".
  Miss thì gọi `loader`, rồi `SET key value EX ttl` trong **một lệnh** (không tách `SET` rồi `EXPIRE`, vì nếu
  process chết giữa hai lệnh sẽ để lại key không bao giờ hết hạn).
- **Negative caching**: nếu không cache kết quả rỗng, kẻ xấu (hoặc bug) gọi liên tục id không tồn tại sẽ đánh
  thẳng vào database (cache penetration). TTL ngắn (`negative_ttl`) để sản phẩm mới tạo sớm hiện ra.
- `update`: **ghi DB trước, xoá cache sau**. Nếu xoá cache trước, một request đọc chen vào giữa sẽ nạp lại
  giá trị cũ từ DB vào cache, và cache sai tới hết TTL. Nếu ghi DB lỗi, ta không đụng tới cache nên cache vẫn
  khớp với DB.
- Vì sao **xoá** chứ không `SET` giá trị mới? Hai request update A rồi B có thể tới Redis theo thứ tự B rồi A,
  làm cache giữ giá trị A trong khi DB là B. Xoá thì lần đọc kế tiếp luôn lấy từ DB.

## Mở rộng nên biết

- Vẫn còn một race hiếm: request đọc lấy giá trị cũ từ DB, update ghi DB và xoá cache, rồi request đọc mới ghi
  giá trị cũ vào cache. TTL giới hạn thời gian sai. Muốn chặt hơn: "delayed double delete", hoặc xoá cache bằng
  CDC từ DB.
- **Stampede**: thêm lock `SET lock:product:p1 1 NX EX 5` để chỉ một request nạp lại key nóng.
- **TTL jitter**: `ex=self.ttl + random.randint(0, 30)` để nhiều key không hết hạn cùng lúc.
- `json.dumps(..., default=str)` giúp không lỗi với `datetime`/`Decimal` (trả về chuỗi; nếu cần giữ kiểu thì
  dùng serializer khác như `orjson` hoặc lưu hash).
