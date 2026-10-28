# Lời giải: workflow CI

## Cách làm

- **Trigger**: `push` chỉ trên `main` (tránh chạy hai lần cho cùng commit khi đã có PR) và
  `pull_request` cho mọi nhánh, để mọi thay đổi đều được test trước khi merge.
- **`permissions: contents: read`**: mặc định `GITHUB_TOKEN` có thể có quyền ghi vào repo. CI chỉ
  cần đọc code. Đây là nguyên tắc least privilege; nếu một action bên thứ ba bị chiếm quyền, nó
  không đẩy được commit hay tạo release.
- **`timeout-minutes`**: mặc định là 360 phút. Một test treo (vd. chờ kết nối DB mãi) sẽ đốt 6 giờ
  runner; 15 phút là đủ cho repo nhỏ.
- **Pin major version của action** (`@v4`, `@v5`). Tổ chức khắt khe hơn pin theo commit SHA.
- **`python-version: "3.12"`** để trong ngoặc: YAML đọc `3.10` không ngoặc thành số `3.1`.
- **`cache: pip`** dùng `requirements.txt` làm khoá cache, cài lại nhanh hơn nhiều.
- `concurrency` (thêm, không bắt buộc): push mới lên cùng nhánh huỷ lần chạy cũ, tiết kiệm runner.

## Mở rộng

Thêm step `ruff check .`, matrix nhiều phiên bản Python, hoặc Postgres service container cho
integration test (xem bài advanced 02).
