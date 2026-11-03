# Lời giải: backfill theo tháng

Mã nằm trong `backfill.py` cạnh tệp này.

## Backfill là gì và vì sao khó

Backfill là chạy lại pipeline cho **quá khứ**: sau khi sửa lỗi, thêm feature, hoặc dữ liệu về muộn. Điều làm nó nguy hiểm là
nó ghi vào đúng những chỗ mà kết quả cũ đang nằm. Ba nguyên tắc của lời giải:

- **Tham số hoá theo tháng logic.** Mọi thứ phụ thuộc thời gian (tệp đọc, khoá ghi) suy ra từ tham số `month`, không từ đồng hồ
  máy. Một pipeline đọc "dữ liệu tháng này" bằng `today()` không backfill được, vì "tháng này" luôn là tháng chạy.
- **Khoá ghi chứa tháng.** `model-2026-01.joblib` chỉ có thể bị ghi đè bởi đúng tháng 2026-01. Hai tháng khác nhau không bao giờ
  tranh một đường dẫn.
- **Idempotent và mặc định không ghi đè.** Chạy lại cùng lệnh không đổi kết quả; muốn tính lại phải nói rõ `overwrite=True`.
  Đây là dây an toàn cho người gõ nhầm khoảng tháng.

## Các quyết định

- **Một tháng lỗi không dừng cả đợt**, nhưng phải thấy được: `failed` mang thông báo, và flow nên fail hoặc cảnh báo ở cấp trên nếu
  `failed` khác rỗng (bài này trả về dict để test, ở production map sang trạng thái flow).
- **Tệp ghi qua tên tạm rồi đổi tên.** Hệ tệp cho phép `replace` nguyên tử trên cùng thư mục; tránh trạng thái nửa vời mà lần
  `skipped` sau coi là "đã xong". Điều kiện bỏ qua kiểm **cả hai** tệp vì cùng lý do.
- **Lưu `data_sha256` trong metadata.** Từ artifact truy ngược được dữ liệu đã dùng, và biết khi dữ liệu nguồn đã bị sửa sau lần
  chạy (hash khác) thì tháng đó cần `overwrite`.
- **Tuần tự vs song song.** Tuần tự dễ suy luận và đủ cho vài chục tháng. Song song (`.submit`, work pool) cần giới hạn đồng thời
  để khỏi đè tài nguyên dùng chung, và càng cần khoá ghi theo tháng.

## Lỗi hay gặp

- Dùng `date.today()` hoặc `datetime.now()` bên trong bước xử lý.
- Ghi tên tệp cố định (`model.joblib`) rồi "lưu bản sao" theo ngày.
- Backfill chạy với `overwrite` mặc định là true: một lệnh gõ vội có thể thay cả năm kết quả.
