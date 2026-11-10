# Lời giải: container API restart liên tục

Có hai lỗi chồng nhau: lỗi đầu làm container thoát ngay, lỗi thứ hai làm nó không bao giờ được coi là sẵn sàng.

## Chẩn đoán theo thứ tự

**1. Trạng thái.** `docker compose ps -a` cho `Restarting (1)`: tiến trình thoát với mã 1 rồi `restart: always` dựng lại, vòng lặp vô hạn. Mã 1 là lỗi của chính chương trình, không phải bị kill (137) hay hết bộ nhớ.

**2. Log.** `docker compose logs api` kết thúc bằng `FileNotFoundError: [Errno 2] No such file or directory: '/models/model.joblib'` ngay khi khởi động, trước dòng `serving ...`. Service chưa bao giờ nghe cổng.

**3. Đối chiếu cấu hình với hợp đồng.** `MODEL_PATH=/models/model.joblib` đúng, nhưng volume là `./model:/models:ro` trong khi thư mục model của dự án là `./models`. Docker (bind mount kiểu viết tắt) âm thầm tạo thư mục rỗng `./model` trên host và mount nó, nên `/models` tồn tại nhưng trống. Image không chứa model, nên không có gì thay thế.

**Lỗi 1**: `./model:/models:ro` -> `./models:/models:ro`.

**4. Sau khi sửa.** Container ở lại, `/healthz` trả 200 nếu gọi tay, nhưng `docker compose ps` hiện `unhealthy` và `up --wait` thất bại. `docker inspect --format '{{json .State.Health}}'` cho log của healthcheck: `exec: "curl": executable file not found in $PATH`. Image `python:*-slim` không có `curl`, nên healthcheck luôn thất bại, bất kể service khoẻ.

**Lỗi 2**: dùng công cụ có sẵn trong image: `["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')"]`.

## Bài học

- `restart: always` che nguyên nhân: nó biến lỗi cấu hình thành vòng lặp. `unless-stopped` không khác nhiều; muốn lỗi cấu hình hiện ra thì dùng `on-failure:3` kèm alert, và luôn có healthcheck.
- Healthcheck cũng là code và phải được kiểm: chạy lệnh đó bên trong container (`docker compose exec api ...`) trước khi tin nó.
- Bind mount viết tắt tự tạo thư mục thiếu; dạng dài (`type: bind`, `bind.create_host_path: false`) báo lỗi ngay khi đường dẫn sai.
- Khi model là phần của image hay của volume, hợp đồng phải ghi rõ ai chịu trách nhiệm đặt file; service nên in đường dẫn nó cố đọc.
