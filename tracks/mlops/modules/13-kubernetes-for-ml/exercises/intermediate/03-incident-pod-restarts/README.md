---
title: Sự cố - pod model bị kill lặp lại ngay sau deploy
level: intermediate
services: []
files:
  - path: starter/eta-api.yaml
    note: Manifest đang chạy, tìm và sửa lỗi
  - path: tests/test_incident.py
    note: Không sửa
  - path: tests/fixtures/eta-api.incident.yaml
    note: Bản gốc lúc sự cố
run:
  - bash setup/mlops/kind/up.sh
  - nice -n 15 uv run pytest tracks/mlops/modules/13-kubernetes-for-ml/exercises/intermediate/03-incident-pod-restarts -q
---

## Mục tiêu

Chẩn đoán một pod chết lặp lại trên Kubernetes theo thứ tự on-call: trạng thái pod, lý do container kết thúc lần trước, log, events, rồi đối chiếu với manifest; sửa tối thiểu và chứng minh bằng request thật.

## Đề bài

Sáng nay đội deploy bản mới của service ETA (`starter/eta-api.yaml`, model `/models/eta-v3.joblib`). Ngay sau deploy, pod liên tục bị kill và khởi động lại: cột `RESTARTS` tăng dần, có lúc trạng thái `CrashLoopBackOff`, pod chưa lần nào Ready. Log của mỗi lần chạy chỉ có một dòng `loading model from /models/eta-v3.joblib` rồi dừng, không có traceback. Bước build image không lỗi, service lab (`tracks/mlops/modules/13-kubernetes-for-ml/lab/service/`) không đổi.

Tìm nguyên nhân và sửa `starter/eta-api.yaml`. Hợp đồng (test kiểm):

- Vẫn deploy model v3 (`MODEL_PATH=/models/eta-v3.joblib`), giữ `image: eta-serve:dev`, giữ `livenessProbe` và `readinessProbe` kiểu `httpGet`.
- Container khai báo `resources.requests` và `resources.limits` cho cả `cpu` và `memory`; `requests` không lớn hơn `limits`. Ngân sách namespace: `limits` mỗi pod tối đa **2 CPU** và **1Gi** bộ nhớ.

Test chạy lại bản lúc sự cố (`tests/fixtures/eta-api.incident.yaml`) và đòi nó tái hiện triệu chứng (pod khởi động lại ít nhất 2 lần); chạy bản của bạn và đòi Deployment Available, không restart lần nào trong 30 giây theo dõi, `/predict` qua Service trả `model_version == "v3"` với dự đoán đúng.

## Tiêu chí đạt

- Bản lúc sự cố tái hiện triệu chứng; bản của bạn chạy ổn, không restart, trả đúng v3.
- Giữ hợp đồng ở trên.
- Chỉ ra được dòng lệnh hoặc trường trạng thái đã dẫn bạn tới nguyên nhân, và cách bạn chọn con số trong bản sửa.

## Gợi ý

### Gợi ý 1

Log rỗng không có nghĩa là không có thông tin. `kubectl --context kind-mlops -n <ns> describe pod <pod>`: đọc phần `Last State` của container, đặc biệt `Reason` và `Exit Code`.

### Gợi ý 2

`kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[0].lastState}'` cho cùng thông tin dạng JSON. Tra nghĩa của `Reason` và `Exit Code` trong tài liệu Kubernetes rồi mới đối chiếu với manifest.
