# Lời giải: job huấn luyện kẹt mãi dù cluster rảnh

## Nguyên nhân

Init container `fetch-data` xin `memory: 3Gi` (requests và limits). Kubernetes tính requests **hiệu dụng** của một pod là `max(tổng requests các container chính, requests lớn nhất của từng init container)`, vì init container chạy trước và tuần tự. Mỗi pod vì vậy xin `max(1Gi, 3Gi)` = **3Gi** bộ nhớ chứ không phải 1Gi. Job 2 worker xin 6Gi, trong khi ClusterQueue `ml-train` chỉ có 4Gi bộ nhớ danh nghĩa và không thuộc cohort nào để mượn.

Kueue thấy Workload **không bao giờ** vừa quota: condition `QuotaReserved=False`, reason `ExceedsMaxQuota`, message dạng `couldn't assign flavors to pod set main: insufficient quota for memory in flavor default-..., previously considered podsets requests (0) + current podset request (6Gi) > maximum capacity (4Gi)`. Job giữ `suspend: true`, nên không pod nào được tạo, scheduler không liên quan, node rảnh cũng vô ích. Người gửi job chỉ cộng requests của container `train` (2 × 1Gi = 2Gi < 4Gi) và bỏ quên init container.

## Chẩn đoán

1. `kubectl get job train-eta -o jsonpath='{.spec.suspend}'` → `true`: Job chưa được thả.
2. `kubectl get workloads`: Workload của Job có `ADMITTED` trống.
3. `kubectl describe workload <tên>`: đọc message của `QuotaReserved`, thấy 6Gi > 4Gi.
4. Tính lại: 2 pod × 3Gi; 3Gi đến từ init container.

## Sửa

Hạ requests/limits của `fetch-data` về mức nó thật sự dùng (`busybox echo`: 128Mi/256Mi). Mỗi pod giờ xin `max(1Gi, 128Mi)` = 1Gi, tổng 2Gi, vừa quota. Không đổi quota (hợp đồng) và không bỏ init container. Đổi quota cũng làm job chạy, nhưng là tăng tài nguyên của đội để che một con số sai.

## Ngăn lần sau

- Kiểm tĩnh trong CI cho manifest Job: tính requests hiệu dụng (gồm init container) × `parallelism`, so với quota của LocalQueue đích; chặn merge nếu vượt.
- Cảnh báo: Workload có `QuotaReserved=False` reason `ExceedsMaxQuota` (không bao giờ vừa, khác với chờ chỗ) báo ngay cho người gửi; metric `kueue_pending_workloads` theo ClusterQueue.
- Runbook "job không có pod" bắt đầu từ `kubectl get workloads`, không phải từ scheduler hay node.
