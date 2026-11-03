# Lời giải: registry, alias, rollback

Mã trong `registry.py`; đáp án trắc nghiệm trong `quiz-answers.yaml`.

## Điểm mấu chốt

- **Alias là con trỏ, version là bất biến.** Rollback không "xoá model lỗi" mà dời con trỏ về version cũ, nên một thao tác
  duy nhất, tức thì, đảo ngược được, và để nguyên version lỗi cho điều tra (UI vẫn cho xem run, metric, artifact của nó).
- **Ghi đường lui lên version mới lúc promote.** Lúc rollback người trực không phải nhớ "trước đó là v mấy". Tag
  `previous_champion` là một chuỗi ngắn nhưng nó là thứ giúp rollback lúc 3 giờ sáng chạy đúng. Đổi lại, chỉ lùi được
  một bước; muốn lùi sâu hơn thì dùng lịch sử version hoặc audit log của registry.
- **Phân giải alias một lần rồi nạp theo số version.** `models:/tên@champion` được phân giải lại mỗi lần nạp; nếu đồng thời
  ai đó đổi alias, log "đã nạp v2" có thể sai. Trả cặp `(model, version)` từ cùng một lần phân giải làm số liệu trong log,
  trong response và trong metric luôn khớp model thật (bài module 07 dùng lại ý này).
- **Chờ `READY`.** `create_model_version` trả ngay khi version còn `PENDING_REGISTRATION`; promote một version chưa READY
  làm service nạp lỗi. Có timeout để không treo vô hạn.
- **`model_id` với MLflow 3.** Model log bằng `log_model` là "logged model" có id riêng; đăng ký qua `runs:/<run>/model` như
  MLflow 2 sẽ trỏ vào chỗ không có `MLmodel`.

## Cái bẫy của stack này

Server chạy `--serve-artifacts` nhưng MinIO nằm trong mạng Docker. Client tự bật tải "multipart" qua presigned URL trỏ tới
`minio:9000`, tên miền chỉ container thấy, nên `load_model` treo cho tới khi hết thời gian thử lại. Đặt
`MLFLOW_ENABLE_PROXY_MULTIPART_DOWNLOAD=false` để client tải qua proxy của server. Đây là lý do chọn proxy artifact
(`--serve-artifacts`) cho môi trường học, và là một ví dụ về chuyện "chạy được trên server, treo ở client".

## Đáp án trắc nghiệm

- *why-server-store* (a): file store không có registry, không an toàn khi nhiều tiến trình ghi, và MLflow 3 đã đưa nó vào
  chế độ bảo trì. Database không làm train nhanh hơn, và tag git không phụ thuộc backend.
- *pick-tool-selfhost* (b): ràng buộc "dữ liệu không rời mạng nội bộ" loại SaaS; bảng tính không có registry hay truy vấn.
- *pick-tool-saas* (c): đội nhỏ không có người vận hành, dữ liệu công khai, cần so sánh run: SaaS hợp lý. Ràng buộc đổi
  thì đáp án đổi, đó là ý của câu trước.
- *serve-by-alias* (d): "version lớn nhất" là đúng cách gây sự cố ở bài tập sự cố; số version cứng bắt phải deploy lại.
- *resolve-then-load* (c): tính nhất quán giữa version báo cáo và version nạp, không phải tốc độ.
- *rollback-mechanics* (a, b): xoá version lỗi không cần thiết (c sai) và service đang chạy không tự nạp lại (d sai): service
  phải có cơ chế refresh hoặc restart, xem bài sự cố tiếp theo và module 07.
