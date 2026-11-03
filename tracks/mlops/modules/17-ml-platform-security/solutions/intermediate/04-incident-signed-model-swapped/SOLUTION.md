# Lời giải: model đã ký vẫn bị thay mà cổng không chặn

**Nguyên nhân gốc.** `stage` verify **bản trong registry** rồi trả **bản sao trên đĩa node**, và chỉ chép bản sao ở lần đầu. Hai đối tượng
khác nhau:

1. Hôm thứ Ba (canary), `node-4` chép version 7 vào `cache_root/<khoá>`.
2. Tuần trước, người "thử sửa nóng" sửa `model.safetensors` ngay trong thư mục đó trên node.
3. Hôm nay, deploy lại version 7: `_check` verify bản trong registry (vẫn nguyên vẹn, nên log `signature OK` là thật), thấy thư mục cache đã
   có thì không chép lại, trả thư mục đã bị sửa. Serving nạp model bị sửa.

Năm node kia chưa từng chạy version 7 nên chép mới từ registry, đúng như bản đã ký. Đây là lỗi kiểm tra một thứ rồi dùng một thứ khác
(TOCTOU: time-of-check to time-of-use).

**Sửa.** Verify **chính bản sẽ được nạp**, ở **mọi** lần: thư mục cache verify được thì dùng lại; không thì xoá và chép lại; bản vừa chép
cũng verify trước khi đổi tên vào chỗ (chép vào thư mục tạm, verify, rồi `rename`, nên serving không bao giờ thấy bản dở dang hay bản chưa
kiểm). Bản registry không verify được thì `Rejected` và dọn thư mục tạm. `release.py` cạnh tệp này là bản sửa.

**Phòng lần sau.**

- **Quy tắc review:** mọi bước kiểm (chữ ký, quét, hash) phải chạy trên đúng byte mà bước sau dùng. Câu hỏi review: "giữa lúc kiểm và lúc
  dùng, ai có thể ghi vào chỗ này?"
- **Verify lúc nạp.** Serving (hoặc init container ngay trước nó) verify thư mục model trước khi nạp, không trông vào agent deploy. Lỗi verify
  làm pod không Ready, readiness probe chặn lưu lượng.
- **Không cho ghi.** Thư mục model trên node mount chỉ đọc cho serving; agent deploy là tiến trình duy nhất có quyền ghi; đăng nhập
  node production qua quy trình có ghi log và không có quyền ghi vào thư mục model. "Sửa nóng" đi qua pipeline (ký, quét) như mọi thay đổi.
- **Phát hiện.** Định kỳ băm thư mục model đang nạp trên từng node và so với manifest đã ký; khác là alert bảo mật. Metric "hash model đang
  phục vụ" theo node giúp thấy ngay một node lệch.
- **Content-addressed.** Đặt tên thư mục cache theo hash của nội dung (hoặc của manifest đã ký) và verify khi đọc; container image chứa model
  với digest ghim cũng cho cùng tính chất.

**Bài học.** Chữ ký chỉ bảo vệ những byte mà bạn thật sự verify. "Đã ký" là thuộc tính của một bản; mỗi bản sao mới cần được kiểm lại ở nơi
nó được dùng.
