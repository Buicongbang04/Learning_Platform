# Lời giải: image thân thiện cache

Ba lỗi của starter:

1. **`COPY . .` trước `pip install`**: bất kỳ tệp nào trong context đổi (kể cả notebook) làm layer `COPY` đổi, kéo theo `pip install` chạy lại. Sửa: `COPY requirements.txt` rồi `pip install`; code chép sau cùng.
2. **Không có `.dockerignore`**: `notebooks/` (150 MB CSV) và `__pycache__` nằm vào context, rồi vào image. Ngoài kích thước còn là rủi ro bảo mật: `.env`, khoá và dữ liệu khách hàng lọt vào layer và không xoá được bằng lệnh `RUN rm` ở layer sau (layer cũ vẫn chứa nó).
3. **Một stage, base không ghim, không `--no-cache-dir`**: stage cuối mang cả cache pip. Sửa bằng multi-stage với `--no-cache-dir`.

Thứ tự trong `Dockerfile` lời giải: ít đổi nhất (dependency) đến hay đổi nhất (code), model đứng trước code vì đổi theo nhịp retrain chứ không theo từng commit. Muốn kiểm cache thật: build, sửa `app/serve.py`, build lại và xem các bước cài đặt báo `CACHED`.
