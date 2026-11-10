# Lời giải: tách quota serving và training

Lời giải ở `serving.yaml` và `training.yaml`.

- **GPU trong quota** chỉ viết được `requests.<tên>`: Kubernetes không overcommit extended resource, requests luôn bằng limits. `requests.<gpu>: "0"` ở serving nghĩa là mọi pod xin GPU bị từ chối ngay ở admission (`exceeded quota`), không phải nằm `Pending`.
- **Quota CPU/RAM bắt mọi pod khai các trường đó.** Có `requests.cpu` trong quota mà pod không khai thì API server từ chối (`must specify requests.cpu`). LimitRange điền `defaultRequest`/`default` trước khi quota kiểm, nên pod "không khai" vẫn được nhận và được tính đúng. Đó là lý do hai object luôn đi cặp.
- **`max` của LimitRange** chặn từng container (2Gi ở serving, 6Gi ở training bị từ chối), còn quota chặn tổng. Pod xin 3 CPU ở serving bị quota chặn vì tổng `requests.cpu` 2.
- `limits.memory` trong quota giới hạn mức overcommit bộ nhớ của namespace: tổng limit có thể lớn hơn tổng request (QoS Burstable), nhưng có trần.

Ngoài đời: quota của namespace serving nên lớn hơn đỉnh autoscale (`maxReplicas × requests`), nếu không HPA muốn thêm pod mà quota chặn, triệu chứng là ReplicaSet có event `exceeded quota` chứ không phải pod Pending. Training thường dùng Kueue (mục 4) thay vì chỉ ResourceQuota, vì quota từ chối pod ngay chứ không xếp hàng.
