# Lời giải: MLflow Tracking

## Cách làm

MLflow tách hai nơi lưu:

| Nơi lưu | Chứa gì | Trong bài |
| --- | --- | --- |
| Backend store (`tracking_uri`) | Experiment, run, params, metrics, tags, model registry | `sqlite:///.../mlflow.db` |
| Artifact store (`artifact_location` của experiment) | Tệp: model, biểu đồ, bảng, requirements | Thư mục trong `artifact_root` |

Lời giải dùng `MlflowClient(tracking_uri)` cho mọi thao tác. Fluent API (`mlflow.start_run()`,
`mlflow.log_metric`) tiện trong notebook nhưng dựa vào trạng thái toàn cục: tracking URI hiện tại,
run đang mở. Trong code thư viện, test hay pipeline chạy song song, trạng thái toàn cục là nguồn
lỗi khó tìm (ghi nhầm vào run của người khác, run không bao giờ được đóng).

- **Artifact location tường minh.** Không chỉ định thì SQLite backend đặt artifact vào `./mlruns`
  **của thư mục đang chạy**: chạy test từ gốc repo là có một thư mục `mlruns/` rác trong repo. Test
  cuối của bài kiểm đúng lỗi này.
- **Run lỗi phải đánh dấu FAILED.** Một run chết giữa chừng mà vẫn mang trạng thái `RUNNING` (hoặc tệ
  hơn, `FINISHED`) có thể chứa metric của một epoch tốt ngẫu nhiên và được chọn làm "best".
- **Params là chuỗi.** MLflow lưu param dạng chuỗi, nên không lọc `params.C > 0.1` được như số.
  Giá trị cần so sánh số thì ghi thêm làm metric hoặc tag có quy ước.

## Ghi gì vào một run

Tối thiểu để tái lập và so sánh được: params của model **và** của dữ liệu (khoảng ngày train,
tên/phiên bản bảng feature), metric trên validation, git commit (tag), và model kèm signature
(bài Intermediate 01). Thiếu phiên bản dữ liệu là lỗi phổ biến nhất: hai run có cùng params
nhưng khác dữ liệu sẽ trông như kết quả "không ổn định".

## Sai lầm hay gặp

- Chọn model tốt nhất bằng metric trên **test** rồi báo cáo chính metric đó: tracking chỉ ghi lại
  những gì bạn làm, không ngăn bạn overfit vào test.
- Log hàng nghìn metric mỗi step trong vòng lặp training: SQLite/DB chậm hẳn. Gom bằng
  `log_batch` hoặc chỉ log mỗi N step.
- Đổi tên metric giữa các run (`auc_val`, `val_auc`): truy vấn và biểu đồ so sánh hỏng. Thống nhất
  quy ước đặt tên trong team từ đầu.
