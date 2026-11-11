# Lời giải: connector file share → inbox

Lời giải ở `sync_share.py` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/07-customer-integration/exercises/basic/02-smb-connector -q
```

Đo 2026-11-11 trên máy của repo: ~12 s (boot `lab-open` 1024 MB + Samba ~8 s, 5 lần chạy connector < 1 s mỗi lần).

## Cách làm

1. **Trạng thái nằm ở connector, không ở inbox.** Worker chuyển tệp đi sau khi nạp, nên "tệp có trong inbox chưa" không
   trả lời được "đã giao chưa". Tệp state (JSON) lưu với mỗi đường dẫn: mtime (`LastWriteTime` của SMB), kích thước,
   sha256 của bản đã giao.
2. **Liệt kê một lượt** bằng `smbclient.scandir`: mỗi `DirEntry` mang sẵn `smb_info` (`last_write_time`,
   `end_of_file`) từ chính phản hồi `QUERY_DIRECTORY`, không mở thêm handle nào. Gọi `smbclient.stat()` cho từng tệp
   cũng đúng (Samba cho mở handle chỉ-đọc-thuộc-tính kể cả khi tệp không cho đọc nội dung) nhưng mỗi tệp thêm vài lượt
   round-trip: biến thể dùng `stat` qua được test nhưng mất ~73 s thay vì ~12 s, và trên share thật hàng chục nghìn
   tệp qua WAN thì khác biệt đó là hàng giờ. `DirEntry.stat()` còn bỏ mất `port` (gọi lại cổng 445).
3. **Cổng gác rẻ trước, băm sau.** mtime + kích thước trùng ⇒ bỏ qua, không mở tệp. Đổi ⇒ đọc và băm sha256 trong lúc
   chép; sha trùng bản đã giao ⇒ chỉ cập nhật mtime trong state (ai đó mở rồi lưu lại không sửa gì, hay công cụ sao lưu
   chạm mtime).
4. **Ghi an toàn**: chép vào tệp tạm `.<tên>.part` ngay trong thư mục đích (worker bỏ qua tên bắt đầu bằng `.`), xong
   mới `os.replace` (nguyên tử trong cùng filesystem). State ghi bằng tệp tạm + `fsync` + `os.replace` **sau mỗi tệp**:
   chết giữa chừng thì lần sau chỉ làm lại tệp dở dang.
5. **Xoá đúng tệp**: tệp có trong state mà không còn trong share ⇒ `deleted`; chỉ gỡ khỏi inbox khi tệp ở đúng đường dẫn
   đó còn đúng sha connector đã giao (người khác thả tệp trùng tên thì để yên). Không đụng `done/`, `failed/`. Tài liệu
   đã nạp vào quillo thì quillo 1.0.0 chưa có API xoá: danh sách `deleted` là đầu vào cho người vận hành (hoặc yêu cầu
   gửi product).
6. **Lỗi từng tệp không làm hỏng cả lượt**: `SMBOSError` (vd. `STATUS_ACCESS_DENIED`) ⇒ ghi `errors`, không ghi state cho
   tệp đó (lần sau thử lại), thoát `1` để cron/systemd báo động. Lỗi cả phiên (sai mật khẩu, mất kết nối) ⇒ thoát `2`,
   không in báo cáo.

## Biến thể sai (đã chạy thử với test)

- **Không có cổng mtime/kích thước, lần nào cũng đọc và so sha**: đúng về nội dung nhưng đọc lại cả share mỗi lần
  (tải mạng, khoá tệp Office đang mở), và hỏng ở lần 2 vì tệp bị tước quyền đọc ⇒ lỗi giả.
- **Dùng inbox làm trạng thái** ("chưa có trong inbox thì chép"): lần 2 giao lại hai tệp worker đã chuyển sang `done/`
  ⇒ quillo nạp trùng (với quillo, cùng nội dung là cùng `doc_id` nên chỉ tốn công; với hệ thống khác là bản ghi đôi).
- **Xoá mọi thứ trong inbox không có trên share**: xoá tệp người dùng thả vào, và nếu đi vào `done/` thì xoá luôn bằng
  chứng nạp.

## Ghi chú hiện trường

- mtime của SMB có độ phân giải 100 ns nhưng do **client ghi** đặt: máy trạm lệch giờ hay công cụ sao chép giữ mtime cũ
  thì một tệp đổi nội dung có thể giữ mtime cũ *và* cùng kích thước. Cổng mtime+size là đánh đổi có ý thức; khách cần
  chắc tuyệt đối thì chạy thêm một lượt băm toàn bộ theo lịch thưa (vd. cuối tuần).
- Tài khoản dịch vụ chỉ đọc (`svc-quillo`) là đúng: connector không cần ghi share, và IT khách sẽ hỏi.
- Đổi tên thư mục ở nguồn = xoá + thêm toàn bộ cây con: báo cho khách trước khi họ "sắp xếp lại thư mục" cuối quý.
