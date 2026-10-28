# Lời giải: Phát hiện PII bằng regex và checksum

## Cách làm

1. **Regex rộng + checksum hẹp.** Regex chỉ bắt *hình dạng* (13–19 chữ số, `ddd.ddd.ddd-dd`), checksum mới
   quyết định có phải PII thật không. Nhờ Luhn và checksum CPF, mã đơn hàng, mã vận đơn dài 20 số hay
   CPF gõ sai không bị báo nhầm.
2. **Biên số** `(?<!\d)` và `(?!\d)` ngăn regex cắt một đoạn ở giữa dãy số dài hơn. Với phone, lookbehind
   loại thêm `+` để không bắt phần đuôi của `+84…` một lần nữa.
3. **Chống chồng lấn theo ưu tiên.** Chạy lần lượt `email > card > cpf > phone`; match nào chồng lên
   khoảng đã nhận thì bỏ. Vì vậy `0912345678@vnmail.vn` chỉ là email, `12345678909` chỉ là CPF.
4. **`redact`** thay từ cuối chuỗi về đầu để chỉ số `start/end` của các match phía trước không bị lệch.
5. **`scan_dataframe`** bỏ cột số, lấy mẫu `head(sample_size)` các giá trị không null, đếm số giá trị
   chứa mỗi loại (một giá trị có 2 email vẫn tính 1), so với `threshold`. Ngưỡng cao cho cột có cấu trúc,
   ngưỡng thấp (hoặc "bất kỳ match nào") cho cột free text như `review_comment_message`.

## Đánh đổi

- Regex không bắt được tên người, địa chỉ; cần NER (Presidio, spaCy) cho văn bản tự do.
- Sampling bằng `head` ổn định cho test nhưng có thể lệch; production nên lấy mẫu ngẫu nhiên có seed
  hoặc theo partition mới nhất.
- Kết quả scan nên là *đề xuất tag* để steward xác nhận, không tự động áp policy chặn truy cập ngay.
