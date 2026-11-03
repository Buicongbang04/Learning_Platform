# Lời giải: config và logging JSON

## Cách làm

`load_settings` gom giá trị theo lớp rồi cập nhật dần: YAML trước, env sau, rồi mới dựng `Settings`. Mọi chuyển kiểu đi qua một hàm `_coerce(name, value, base)` để lỗi luôn nêu tên trường. Khoá lạ bị chặn bằng phép hiệu tập hợp với `fields(Settings)`.

`JsonFormatter` tách `extra` bằng cách loại các thuộc tính chuẩn của `LogRecord` (lấy một lần từ một `LogRecord` rỗng), rồi che mọi khoá khớp `password|token|secret|key`.

## Vì sao

- **Đường dẫn trong YAML tính từ thư mục của tệp YAML**, không từ cwd: nếu không, cùng một cấu hình chạy từ `make` ở gốc repo và từ Airflow ở thư mục khác sẽ trỏ tới hai nơi khác nhau, kiểu lỗi chỉ lộ ở production.
- **Khoá lạ là lỗi**: `sed: 3` bị bỏ qua âm thầm nghĩa là bạn tưởng đã đổi seed mà chưa.
- **Env thắng YAML**: container và CI đổi giá trị bằng env mà không sửa tệp trong image.
- **Che bí mật theo tên trường** là lưới an toàn rẻ; không thay được việc không đưa bí mật vào log.
- **Một dòng một JSON** để Loki, CloudWatch hay `jq` đọc được mà không cần regex.

## Lỗi hay gặp

- Gọi `logging.basicConfig` ở mức import của thư viện, ghi đè cấu hình của ứng dụng.
- `configure_logging` thêm handler mỗi lần gọi: log nhân đôi sau mỗi lần reload.
- Parse `ETA_SEED` bằng `int()` ngoài hàm chung nên lỗi báo `ValueError: invalid literal` không nói trường nào.
