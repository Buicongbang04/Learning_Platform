---
title: Canary hai version trên KServe RawDeployment và rollback về 0%
level: intermediate
services: []
files:
  - path: starter/canary.yaml
    note: Bản canary đồng nghiệp viết, chưa chia được traffic
  - path: starter/rollback.yaml
    note: Bản rollback, còn trống
  - path: tests/test_canary.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh
  - nice -n 15 uv run pytest tracks/mlops/modules/13-kubernetes-for-ml/exercises/intermediate/02-kserve-canary-rollback -q
---

## Mục tiêu

Chạy canary model v2 cạnh v1 trên KServe ở chế độ RawDeployment (không Knative), đo tỉ lệ traffic thật từ trong cluster, và rút canary về 0% mà không đụng bản stable.

## Đề bài

Cluster chạy KServe RawDeployment: mỗi InferenceService là một Deployment + Service thường. Trường `canaryTrafficPercent` chỉ có tác dụng ở chế độ Serverless (Knative chia traffic theo revision); ở RawDeployment nó **bị bỏ qua** và InferenceService rolling update thẳng sang bản mới. `starter/canary.yaml` đang dựa vào trường đó.

Viết lại hai tệp (giữ `image: eta-serve:dev`):

1. `canary.yaml`: InferenceService `eta-stable` (model v1, **3 replica**) và `eta-canary` (model v2, **1 replica**), cả hai giữ `serving.kserve.io/autoscalerClass: none` và `minReplicas == maxReplicas`; một Service tên **`eta`**, cổng 80 → 8080, chọn pod của **cả hai** predictor (3 v1 + 1 v2). Kỳ vọng v2 nhận khoảng 25% request.
2. `rollback.yaml`: apply lên trên `canary.yaml` thì v2 nhận **0%** traffic. Không xoá InferenceService `eta-canary` (giữ spec để bật lại), không sửa `eta-stable`.

Không dùng `canaryTrafficPercent` trong tệp nào (test kiểm). `kubectl port-forward` chỉ nối tới **một** pod, nên test chạy một pod client trong namespace gửi 200 request tới `http://eta/v1/models/eta:predict` (mỗi request một kết nối mới) và đếm theo `model_version`: Trước khi đo, test kiểm Service `eta` chọn pod của cả hai InferenceService (sai thì fail ngay) và chờ đủ **4 endpoint Ready**. v2 phải nằm trong **10-45%**, có cả v1 và không request nào lỗi. Sau khi apply `rollback.yaml`, test chờ Service `eta` về đúng **3 endpoint Ready** (tối đa 120 giây, quá hạn là fail) rồi kiểm: 100 request đều là v1, Deployment `eta-stable-predictor` không đổi generation và vẫn 3 pod Ready.

## Tiêu chí đạt

- Tỉ lệ v2 trong 10-45% trên 200 request, không lỗi.
- Sau rollback: 100/100 request là v1, `eta-stable` không bị đụng, `eta-canary` vẫn còn.
- Nói được giới hạn của chia traffic theo số replica (độ mịn, phụ thuộc kube-proxy và kết nối giữ lâu).

## Gợi ý

### Gợi ý 1

`spec.predictor.labels` của InferenceService được gắn vào pod predictor. Service chọn pod theo nhãn, không quan tâm pod thuộc Deployment nào.

### Gợi ý 2

Có hai cách đưa canary về 0% mà vẫn giữ InferenceService: bỏ nhãn chung khỏi pod canary, hoặc annotation dừng của KServe (`serving.kserve.io/stop`). Cân nhắc cách nào bật lại nhanh hơn, cách nào giải phóng tài nguyên.
