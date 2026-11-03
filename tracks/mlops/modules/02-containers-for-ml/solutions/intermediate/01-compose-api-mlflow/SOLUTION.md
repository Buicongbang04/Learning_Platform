# Lời giải: Compose API + MLflow

Xem `compose.yaml` và `api.env`. Các điểm chính:

- **`depends_on` với `condition: service_healthy`**: nếu thiếu `condition`, Compose chỉ đảm bảo container `mlflow` đã *khởi động*, không phải server đã nghe cổng; API gọi MLflow sớm sẽ lỗi kết nối. Healthcheck của `mlflow` gọi `/health` bằng Python vì image slim không có `curl`; `start_period` tránh đếm retry trong lúc server khởi động.
- **Named volume `mlflow-data`**: dữ liệu sống sót qua `docker compose down` (không `-v`) và không dính quyền của host như bind mount. Hai đường dẫn của MLflow (`--backend-store-uri`, `--default-artifact-root`) đều nằm dưới `/mlflow-data`; nếu để mặc định (`./mlruns` trong thư mục làm việc) dữ liệu nằm trong layer ghi của container và mất khi tạo lại container.
- **`MLFLOW_ALLOW_FILE_STORE=true`**: từ MLflow 3.x file store ở chế độ bảo trì, server từ chối chạy nếu không bật tường minh; một dấu hiệu rằng nên dùng backend SQL.
- **`--allowed-hosts`**: MLflow 3.x từ chối request có header `Host` lạ (chống DNS rebinding). API gọi bằng `mlflow:5000` nên phải cho phép tường minh; thiếu thì API nhận 403 dù mạng thông.
- **File store chỉ hợp cho một người**: không có giao dịch nhiều ghi đồng thời, truy vấn chậm khi số run tăng và model registry cần backend SQL. Module 04 chuyển sang Postgres + MinIO.
- **`env_file`**: cấu hình tách khỏi `compose.yaml`; đổi `MLFLOW_TRACKING_URI` không cần sửa định nghĩa dịch vụ. Trong network của Compose, MLflow có tên `mlflow`, nên địa chỉ là `http://mlflow:5000`, không phải `localhost`.
- **Cổng không cố định** (`"8000"`): Docker chọn cổng host trống; nhiều dự án chạy cùng lúc, không đụng cổng của máy.
- Profile (`profiles: [tools]`) là cách thêm dịch vụ tuỳ chọn (UI, smoke test) mà `docker compose up` mặc định không bật.
