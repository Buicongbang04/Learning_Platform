# Lời giải: Dockerfile cho service sklearn

```dockerfile
FROM python:3.12.11-slim AS build
...
FROM python:3.12.11-slim
COPY --from=build /opt/venv /opt/venv
USER app
HEALTHCHECK ...
```

Xem `Dockerfile` trong thư mục này. Các quyết định:

- **Multi-stage với virtualenv**: stage `build` cài dependency vào `/opt/venv`; stage cuối chỉ chép thư mục đó. Với wheel thuần thì lợi ích chủ yếu là sạch (không pip, không cache, không công cụ build ở stage cuối); khi dependency cần biên dịch (gcc, header) thì lợi ích lớn hơn nhiều.
- **`--no-cache-dir`**: wheel đã tải nằm trong `~/.cache/pip`, tức vào layer và không bao giờ được dùng lại.
- **Ghim tag `3.12.11-slim`**: `3.12-slim` trôi theo bản vá, hai lần build cách nhau một tuần cho hai image khác nhau. Ghim cả digest còn chắc hơn.
- **Dependency đã ghim trong `requirements.txt`**: model joblib phụ thuộc phiên bản scikit-learn; load model bằng bản khác có thể lỗi hoặc, tệ hơn, cho kết quả khác.
- **`USER app` (uid 10001)**: tiến trình không có quyền ghi vào hệ thống tệp image; tránh uid trùng người dùng thật của host nếu mount volume.
- **`HEALTHCHECK` bằng Python**: image slim không có `curl`; `urllib` đủ cho `/healthz`.
- **Kích thước**: khoảng 550 MB, phần lớn là numpy/scipy/scikit-learn (khoảng 370 MB) trên nền 180 MB. Ngưỡng 600 MB bắt được image kèm pip cache hoặc base đầy đủ.
