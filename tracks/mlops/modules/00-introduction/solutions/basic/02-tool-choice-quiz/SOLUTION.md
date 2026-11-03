# Lời giải: chọn công cụ theo tình huống

- **tracking-single-user** (c): một người, vài chục run mỗi tuần: MLflow với SQLite/đĩa local là đủ và đổi sang server khi
  có người thứ hai. Dựng Postgres + MinIO + K8s trước là chi phí vận hành không mua được gì. Excel không tái lập được.
- **data-versioning-bigfiles** (b): DVC giữ hash trong Git, dữ liệu ở remote; `git checkout` + `dvc checkout` dựng lại.
  Git LFS tính phí/giới hạn theo dung lượng và không có khái niệm pipeline; thư mục theo ngày không gắn với commit; Feast
  không phải công cụ version dữ liệu thô.
- **orchestrator-existing-airflow** (d): dùng thứ đã vận hành được. Công cụ mới có giá nhân lực; cron không có retry,
  backfill, quan sát. Chuyển cả công ty sang công cụ khác vì một đội là sai thứ tự quyết định.
- **serving-realtime-small** (a): 200 req/s model nhỏ không cần Triton hay Ray; batch scoring chỉ đúng khi đầu vào biết
  trước, còn ở đây request đến theo yêu cầu.
- **monitoring-stack** (b): RED metric (rate, errors, duration) và phân phối dự đoán là metric chuỗi thời gian: Prometheus
  + Grafana + Alertmanager. MLflow không phải hệ thống alert; Evidently là báo cáo drift định kỳ, không thay monitoring service.
- **feature-skew** (d): cùng một feature viết hai lần ở hai nơi là nguồn skew kinh điển; feature store cho một định nghĩa
  dùng chung. Tăng cây hay đổi GPU không động tới nguyên nhân; DVC version dữ liệu chứ không bảo đảm logic tính giống nhau.
- **ci-for-ml** (a, b, d): CI cho code chạy mỗi PR và nhanh: lint, unit test, build image, smoke test, test hành vi trên mẫu
  nhỏ có seed. Train lại trên 3 năm dữ liệu là việc của pipeline training (CT), gỡ model là việc của CD/vận hành.
- **infra-cost-aware** (c): thêm thành phần khi có vấn đề đo được. Đội 3 người, 2 model: Compose + MLflow + orchestrator
  nhẹ. "Làm đúng từ đầu" bỏ qua chi phí vận hành của Kubeflow + Istio + Kafka; từ chối mọi thứ cũng sai.
