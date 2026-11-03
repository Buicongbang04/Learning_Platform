# Lời giải: Argo Workflow prepare → train → evaluate

Xem `workflow.yaml`.

- **Parameter** cho giá trị nhỏ (seed, số dòng, ngưỡng): đi qua spec, hiện trong UI, dùng làm điều kiện (`when`). **Artifact** cho tệp (dữ liệu, model): executor đẩy lên kho artifact (MinIO/S3) khi bước kết thúc và kéo xuống pod của bước sau. Không nhét dữ liệu vào parameter: parameter nằm trong object Workflow ở etcd, giới hạn kích thước.
- `evaluate` phụ thuộc cả `prepare` (tập test) và `train` (model). Thiếu phụ thuộc vào `prepare` vẫn chạy được vì `train` đã chờ `prepare`, nhưng khai rõ giúp DAG đúng ý khi sau này `train` đổi.
- `retryStrategy` trên `train` với `retryPolicy: OnError` thử lại khi pod lỗi hạ tầng (node mất, bị evict), không thử lại khi code lỗi logic (`OnFailure` hoặc `Always` mới thử lại cả khi exit code khác 0). Bước tốn kém thì thêm `backoff`.
- Output parameter `metrics` lấy từ tệp (`valueFrom.path`). Test đọc nó từ `status.nodes` và so với MAE tính lại: chứng minh evaluate đọc **đúng** model của lần chạy này, không phải chỉ "Workflow xanh".

- Parameter đi vào bước `prepare` qua `env` rồi `int(...)`: Argo thay `{{...}}` bằng chuỗi trước khi chạy, nên dán thẳng vào `source` biến một giá trị như `0); import os; os.system(...)` thành code. Workflow chạy với `securityContext` mức pod (non-root, seccomp); `spec.templateDefaults.script.securityContext` đặt một lần cho mọi bước script: không leo quyền, bỏ mọi capability; pod Argo vẫn cần token ServiceAccount để executor ghi kết quả.

Mở rộng ngoài bài: thêm bước `register` có `when: "{{tasks.evaluate.outputs.parameters...}}"` để chỉ ghi model vào registry khi đạt ngưỡng; chạy hằng đêm bằng `CronWorkflow`; giới hạn tài nguyên mỗi bước bằng `podSpecPatch` hay `resources` trong template.
