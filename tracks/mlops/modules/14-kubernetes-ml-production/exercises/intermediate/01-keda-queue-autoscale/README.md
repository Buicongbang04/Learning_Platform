---
title: KEDA scale worker suy luận theo hàng đợi, về 0 và đo cold start
level: intermediate
services: []
files:
  - path: starter/scaledobject.yaml
    note: ScaledObject cần hoàn thiện
  - path: tests/fixtures/batch-inference.yaml
    note: Hàng đợi + worker có sẵn, không sửa
  - path: tests/test_keda_autoscale.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh --senior
  - nice -n 15 uv run pytest tracks/mlops/modules/14-kubernetes-ml-production/exercises/intermediate/01-keda-queue-autoscale -q -s
---

## Mục tiêu

Autoscale một worker suy luận batch theo **custom metric của service** (số job chưa xong trong hàng đợi) bằng KEDA: không có việc thì 0 pod, có việc thì lên nhiều pod, hết việc thì về 0. Đo cold start thật của đường 0 → 1.

## Đề bài

`tests/fixtures/batch-inference.yaml` (không sửa) dựng hai thành phần từ image lab `ml-lab:dev` (`lab/service/lab.py` của module; test build và nạp vào kind):

- Deployment + Service `batch-queue` (cổng 8080, luôn 1 pod): hàng đợi job. `GET /pending` trả `{"pending": <số job chưa xong>}`, tính cả job đang chạy.
- Deployment `batch-worker`: mỗi pod nạp model 5 giây khi khởi động, rồi lấy từng job, xử lý 0,5 giây mỗi job.

Viết `starter/scaledobject.yaml`: ScaledObject `worker-autoscale` trỏ `batch-worker` với:

1. `minReplicaCount: 0`, `maxReplicaCount: 4`.
2. `pollingInterval` từ 1 đến 10 giây, `cooldownPeriod` từ 1 đến 30 giây (giữ bài trong ngân sách thời gian).
3. Đúng **một** trigger kiểu `metrics-api` đọc `GET /pending` của Service `batch-queue`, mục tiêu mỗi worker gánh **10** job chưa xong. KEDA operator chạy ở namespace `keda`, nên URL phải có tên namespace đầy đủ: viết `__NAMESPACE__` ở chỗ tên namespace, test thay bằng namespace tạm của nó.

`test_scaledobject_contract` đọc tĩnh `scaledobject.yaml` để giữ ngân sách (mục 1, 2 và loại trigger). Phần còn lại kiểm trên cluster: HPA `keda-hpa-worker-autoscale` do KEDA tạo phải có `maxReplicas` 4 và trỏ `batch-worker`, rồi kịch bản dưới đây.

Test (khoảng 1–3 phút):

1. Apply fixture và ScaledObject, chờ ScaledObject `Ready` và `batch-worker` về **0** replica khi hàng đợi rỗng.
2. Enqueue 160 job. Đòi: xử lý xong cả 160 trong 240 giây, số replica cao nhất **≥ 3**, ít nhất 3 pod worker khác nhau đã xử lý job.
3. Đọc cold start do hàng đợi đo (từ lúc enqueue khi đang 0 replica tới lúc job đầu tiên được lấy), đòi có số đo hợp lệ (0–120 giây) và in ra (chạy với `-s` để thấy).
4. Hết việc thì `batch-worker` về lại **0** replica trong 150 giây.

## Tiêu chí đạt

- ScaledObject đúng yêu cầu; kịch bản 0 → nhiều → 0 chạy đúng trên cluster.
- Ghi lại cold start đo được và tách được nó thành các thành phần (chờ KEDA hỏi, xếp pod, khởi động container, nạp model). Chỉ ra thành phần nào lớn nhất và một cách giảm.
- Giải thích được vì sao trigger không thể là metric do chính pod worker xuất.

## Gợi ý

### Gợi ý 1

Tài liệu scaler `metrics-api` của KEDA (mục 7 lý thuyết): các khoá `url`, `valueLocation`, `targetValue`, `activationTargetValue` nằm trong `metadata` của trigger. Tên Service đầy đủ có dạng `<service>.<namespace>.svc.cluster.local`.

### Gợi ý 2

Theo dõi bằng tay: `kubectl --context kind-mlops -n <ns> get scaledobject,hpa,deploy -w`. HPA tên `keda-hpa-worker-autoscale` do KEDA tạo; cột `TARGETS` cho thấy giá trị metric KEDA đọc được.
