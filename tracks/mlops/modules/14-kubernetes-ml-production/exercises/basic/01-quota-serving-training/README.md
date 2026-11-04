---
title: Tách quota serving và training bằng ResourceQuota và LimitRange
level: basic
services: []
files:
  - path: starter/serving.yaml
    note: ResourceQuota + LimitRange cho namespace serving, còn TODO
  - path: starter/training.yaml
    note: ResourceQuota + LimitRange cho namespace training, còn TODO
  - path: tests/test_quota.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh --senior
  - nice -n 15 uv run pytest tracks/mlops/modules/14-kubernetes-ml-production/exercises/basic/01-quota-serving-training -q
---

## Mục tiêu

Chia một cluster cho hai loại tải của cùng một đội: serving (latency, không cần GPU) và training (nhiều tài nguyên, cần GPU). Dùng ResourceQuota để giới hạn tổng, LimitRange để đặt mặc định và trần cho từng container, và kiểm bằng cách tạo pod thật xem API server nhận hay từ chối.

## Đề bài

Viết hai tệp, mỗi tệp apply vào một namespace riêng (không ghi `namespace` trong manifest; test tự tạo hai namespace `mlops-ex-<uuid8>`). Tên GPU viết là `__GPU__`: test tạo một extended resource giả trên node (`mlops.example/gpu-<uuid8>`, xem mục 3 lý thuyết) và thay vào.

`starter/serving.yaml`:

1. ResourceQuota `serving-quota`: tổng `requests.cpu` **2**, `requests.memory` **2Gi**, `limits.memory` **4Gi**, tối đa **10** pod, và **không cho xin GPU nào** (`requests.__GPU__`).
2. LimitRange `serving-defaults` cho `Container`: request mặc định **100m** CPU / **128Mi**, limit mặc định **500m** / **256Mi**, trần bộ nhớ mỗi container **1Gi**.

`starter/training.yaml`:

1. ResourceQuota `training-quota`: tổng `requests.cpu` **4**, `requests.memory` **8Gi**, `limits.memory` **16Gi**, tối đa **2 GPU**.
2. LimitRange `training-defaults` cho `Container`: request mặc định **250m** / **512Mi**, limit mặc định **1** CPU / **1Gi**, trần bộ nhớ mỗi container **4Gi**.

Test tạo pod busybox (`busybox:1.37`, đã có sẵn trong node) và kiểm:

- Serving: pod không khai `resources` được nhận và nhận đúng 4 giá trị mặc định; pod xin 1 GPU, pod có limit bộ nhớ 2Gi, pod xin 3 CPU đều bị từ chối (`Forbidden`).
- Training: hai pod mỗi pod 1 GPU được nhận, pod GPU thứ ba bị từ chối; pod không khai `resources` nhận request bộ nhớ 512Mi; container limit 6Gi bị từ chối, container request 3Gi / limit 4Gi được nhận.

## Tiêu chí đạt

- Cả hai namespace hành xử đúng mọi trường hợp ở trên, kiểm bằng pod thật trên cluster.
- Giải thích được vì sao namespace có quota CPU mà thiếu LimitRange thì pod không khai `resources` bị từ chối.

## Gợi ý

### Gợi ý 1

Extended resource chỉ đặt quota được ở dạng `requests.<tên-resource>`. `limits.<tên>` cho extended resource không được hỗ trợ.

### Gợi ý 2

Thử bằng tay: `kubectl --context kind-mlops -n <ns> describe quota` cho thấy `Used`/`Hard`. `kubectl ... get pod <tên> -o jsonpath='{.spec.containers[0].resources}'` cho thấy giá trị LimitRange đã điền vào.
