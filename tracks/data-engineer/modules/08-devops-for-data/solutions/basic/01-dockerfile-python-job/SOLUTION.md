# Lời giải: Dockerfile chuẩn cho job ingest

## Cách làm

1. **Pin base image** `python:3.12-slim`: build lại sau sáu tháng vẫn ra cùng phiên bản Python.
   `slim` nhỏ hơn bản đầy đủ khoảng 800 MB. Production nghiêm ngặt hơn có thể pin digest
   `python:3.12-slim@sha256:...`.
2. **Thứ tự layer**: `COPY requirements.txt` → `RUN pip install` → `COPY src/`. Sửa code không
   làm cài lại thư viện, build trong CI giảm từ vài phút xuống vài giây.
3. **`--no-cache-dir`**: pip không giữ cache wheel trong image (cache vô ích trong container, chỉ
   làm image to).
4. **Non-root**: `useradd --uid 10001 appuser` rồi `USER appuser`. UID cố định giúp khớp với
   `securityContext.runAsUser` trên Kubernetes.
5. **Exec form** `ENTRYPOINT ["python", "-m", "src.ingest_orders"]`: Python là PID 1 và nhận
   `SIGTERM` khi Kubernetes dừng Pod; shell form chạy qua `/bin/sh -c`, tín hiệu có thể không tới.
6. **Bỏ `ENV DB_PASSWORD`**: secret trong layer ai pull image cũng đọc được. Truyền lúc chạy:
   `docker run -e DB_PASSWORD=... image` hoặc Kubernetes Secret.
7. **`.dockerignore`**: build context nhỏ (không gửi `data/` vài GB cho daemon), không lỡ đưa `.env`
   vào image, và `COPY` không bị invalid cache vì `.git` thay đổi.

Thử thật (nếu có Docker và có `requirements.txt`, `src/`):

```bash
docker build -t olist-ingest:dev .
docker run --rm -e DB_PASSWORD=de olist-ingest:dev --date 2018-08-01
```
