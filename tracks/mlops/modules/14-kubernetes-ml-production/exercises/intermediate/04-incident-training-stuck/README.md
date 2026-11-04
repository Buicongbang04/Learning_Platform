---
title: Sự cố - job huấn luyện kẹt mãi dù cluster rảnh
level: intermediate
services: []
files:
  - path: starter/training.yaml
    note: Manifest đang dùng, tìm và sửa lỗi
  - path: tests/test_training_job.py
    note: Không sửa
  - path: tests/fixtures/training.incident.yaml
    note: Bản gốc lúc sự cố
run:
  - bash setup/mlops/kind/up.sh --senior
  - nice -n 15 uv run pytest tracks/mlops/modules/14-kubernetes-ml-production/exercises/intermediate/04-incident-training-stuck -q
---

## Mục tiêu

Chẩn đoán một job huấn luyện không chạy trên cluster có hàng đợi Kueue theo thứ tự on-call: trạng thái Job, object trung gian mà controller sinh ra, message của nó, rồi đối chiếu với manifest. Sửa tối thiểu và chứng minh job chạy xong.

## Đề bài

Đội ML gửi job huấn luyện `train-eta` (2 worker chạy song song, mỗi worker 1 GPU) vào hàng đợi `training` của đội (`starter/training.yaml`, cùng ResourceFlavor, ClusterQueue `ml-train-__RUN__`, LocalQueue). Từ sáng tới giờ job không chạy:

- `kubectl get jobs` thấy `train-eta` với `COMPLETIONS 0/2`, tồn tại đã nhiều giờ;
- `kubectl get pods` trong namespace **không có pod nào**, không có sự kiện lỗi nào của pod;
- cluster gần như rảnh: node còn trống phần lớn CPU, bộ nhớ và cả 4 GPU, không job nào khác của đội đang chạy;
- người gửi job khẳng định đã "tính kỹ, job nằm gọn trong quota của đội".

Tìm nguyên nhân và sửa `starter/training.yaml`. Hợp đồng (test kiểm):

- Phần hàng đợi do đội platform quản lý: ResourceFlavor, ClusterQueue `ml-train-__RUN__` (cpu 4, memory 4Gi, GPU 2) và LocalQueue `training` **giữ nguyên từng trường**, không thêm ClusterQueue, cohort hay tài nguyên nào khác. Manifest chỉ có thêm đúng Job `train-eta`.
- Job vẫn gửi qua hàng đợi (nhãn `kueue.x-k8s.io/queue-name: training`); giữ `parallelism`, `completions`, `completionMode`; giữ đủ các container và init container hiện có với đúng `image` và `command`; mỗi worker vẫn xin đúng 1 GPU (`requests` và `limits`).

`__RUN__` và `__GPU__` như các bài Kueue khác (test thay bằng run id và extended resource giả, node có 4 GPU giả). Test chạy lại bản lúc sự cố (`tests/fixtures/training.incident.yaml`) và đòi nó tái hiện triệu chứng: sau khoảng 20 giây Job vẫn đứng yên, không pod nào. Chạy bản của bạn và đòi Job được chạy trong 90 giây và xong cả 2 worker trong 180 giây.

## Tiêu chí đạt

- Bản lúc sự cố tái hiện triệu chứng; bản của bạn chạy xong, giữ hợp đồng.
- Chỉ ra được lệnh và trường trạng thái đã dẫn bạn tới nguyên nhân, và vì sao phép tính "nằm gọn trong quota" của người gửi job sai.
- Đề xuất một cách để lỗi kiểu này bị chặn hoặc lộ ra sớm hơn lần sau.

## Gợi ý

### Gợi ý 1

Không có pod thì scheduler không liên quan. Hỏi: với hàng đợi này, pod được tạo ra **khi nào**, và object nào giữ quyết định đó?

### Gợi ý 2

`kubectl --context kind-mlops -n <ns> get workloads`, rồi `describe` workload của Job: đọc kỹ message của condition chưa đạt, đặc biệt con số trong đó. Rồi tự tính lại con số ấy từ manifest theo đúng cách Kubernetes tính requests của một pod.
