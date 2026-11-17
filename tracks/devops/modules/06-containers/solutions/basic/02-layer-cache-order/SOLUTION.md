# Lời giải: thứ tự layer và `.dockerignore`

## Dockerfile

```dockerfile
FROM python:3.12.16-slim-trixie
ENV PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY export_orders.py .

USER 10001
CMD ["python", "export_orders.py"]
```

## `.dockerignore`

```text
*
!requirements.txt
!export_orders.py
```

## Vì sao

**Cache key đi theo chuỗi.** BuildKit tính key của mỗi bước từ key của bước trước cộng nội dung của bước đó. Với `COPY . .`,
nội dung là checksum mọi tệp trong context; đổi một ký tự trong `export_orders.py` (hay sửa `notes.md`, hay `.env` đổi token)
là bước `COPY` đổi key, và `RUN pip install` sau nó buộc chạy lại dù `requirements.txt` không đổi. Chép riêng
`requirements.txt` trước thì bước cài chỉ phụ thuộc tệp đó. Đo trong test: `CreatedAt` của bước `pip install` giống hệt giữa
hai lần build (lấy từ cache), còn với starter thì hai thời điểm cách nhau vài giây.

**Thứ tự theo tần suất thay đổi.** Ít đổi đặt trước: image nền, gói hệ thống, manifest dependency, cài dependency; hay đổi đặt
sau: mã nguồn, cấu hình build. Với lock file (`uv.lock`, `poetry.lock`, `package-lock.json`) cũng vậy: chép lock file trước,
cài, rồi chép code.

**Hai lớp chống lộ bí mật.** `.dockerignore` loại tệp khỏi build context: tệp không bao giờ rời máy dev tới builder (với builder
từ xa, context được gửi qua mạng). `COPY` đích danh từng tệp là lớp thứ hai: kể cả khi ai đó sửa `.dockerignore`, `.env` cũng
không được chép. Dạng allowlist (`*` rồi `!...`) chặn luôn những tệp chưa ai nghĩ tới.

**Bí mật đã lọt thì phải xoay vòng.** Xoá `.env` ở một layer sau không xoá nó khỏi layer trước: ai pull image đều đọc được bằng
`docker save` hoặc công cụ như `dive`. Token đã vào image đã đẩy lên registry coi như lộ: thu hồi, cấp mới, rồi mới sửa
Dockerfile. Bí mật cần lúc build (token kéo gói private) dùng `RUN --mount=type=secret,id=...`, không dùng `ARG`/`ENV` (giá trị
nằm trong `docker history`).

## Đi xa hơn

- `RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt` giữ cache tải gói giữa các lần build khi
  `requirements.txt` đổi, mà cache không nằm trong image.
- Trong CI, runner thường mới tinh nên cache cục bộ rỗng. Dùng cache ngoài: `--cache-to type=registry,ref=...,mode=max` và
  `--cache-from` (hoặc `type=gha` trên GitHub Actions). Module 07 làm việc này.
- Cache dùng chung giữa mọi build trên máy và không tự dọn: `docker builder du` để xem, `docker builder prune` để dọn.
