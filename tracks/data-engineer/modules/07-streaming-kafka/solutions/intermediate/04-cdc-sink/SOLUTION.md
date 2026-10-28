# CDC sink và atomic checkpoint

Bảng orders và checkpoint nằm trong cùng database. Transaction commit cả hai hoặc không commit gì.
Khi record tới lại sau crash, offset đã có trong checkpoint làm hàm trả False trước khi sửa dữ liệu.

Khóa checkpoint gồm topic và partition: offset 10 ở partition 0 không so được với offset 10 ở partition 1.
Giữ checkpoint sau delete giúp bỏ qua bản cũ khi replay, tránh làm sống lại đơn đã xóa. Đây là dedup
theo vị trí Kafka của lab, không thay cho source ordering khi đổi topic/partition hoặc tạo lại topic.

Snapshot dùng op r, cùng cách upsert với c/u. Delete lấy ID từ key; tombstone value None chỉ tiến offset.
Dữ liệu sai không tiến checkpoint, consumer dừng để sửa; lab chưa tự bỏ qua dữ liệu lỗi vào DLQ.

Lỗi checkpoint được test bằng trigger SQLite cố tình chặn INSERT, để chứng minh rollback cả upsert trước đó.
Khi đưa vào Kafka thật, commit offset riêng từng record đã hoàn tất; không commit vị trí poll của record chưa xử lý.
