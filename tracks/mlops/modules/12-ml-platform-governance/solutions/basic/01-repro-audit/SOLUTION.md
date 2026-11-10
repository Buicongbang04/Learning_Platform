# Lời giải: audit tái lập

Mã nằm trong `audit.py` cạnh tệp này. Các quyết định đáng nhớ:

- **Audit trả "thiếu gì", không trả "ok/không".** Người nhận báo cáo cần hành động: thiếu `lockfile_hash` thì sửa pipeline train, thiếu `seed` thì sửa cấu hình. Một cờ boolean buộc họ tự đào lại.
- **"Có mặt" chưa phải "đáng tin".** `data_version = latest` hay `git_commit` rút gọn qua được kiểm tra "tag tồn tại" nhưng không dựng lại được gì: `latest` đổi theo thời gian, 7 ký tự có thể va chạm. Audit kiểm **hình dạng** của giá trị.
- **`git_dirty` thuộc mục commit.** Một hash sạch đi kèm cây bẩn là lời nói dối: checkout commit đó không cho lại đúng mã đã train. Xem bài lineage ở module 04, nơi tag này được ghi.
- **Truy ngược theo version, không theo "run mới nhất".** Model trong registry trỏ về đúng một run qua `run_id` của version; run mới hơn trong cùng experiment có thể là thử nghiệm khác.
- **Chỉ đọc.** Audit chạy trong cron hay CI trên mọi model; nó không được phép sửa thứ nó đang chứng nhận.

Lỗi hay gặp: `int(seed)` bắt `"4.0"` là hợp lệ khác ý định (ở đây `"4.0"` không phải số nguyên nên không đạt); dùng `startswith` cho hex nên `"abc... "` có dấu cách cuối lọt qua; đọc `git_dirty` thiếu tag thành "sạch".
