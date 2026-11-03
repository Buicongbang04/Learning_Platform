---
title: startupProbe cho model nạp chậm
level: basic
services: []
files:
  - path: starter/eta-api.yaml
    note: Deployment đang bị restart lúc khởi động
  - path: tests/test_startup_probe.py
    note: Không sửa
  - path: tests/fixtures/eta-api.original.yaml
    note: Bản gốc, test dùng để tái hiện
run:
  - bash setup/mlops/kind/up.sh
  - nice -n 15 uv run pytest tracks/mlops/modules/13-kubernetes-for-ml/exercises/basic/02-startup-probe -q
---

## Mục tiêu

Phân biệt ba probe (startup, readiness, liveness) và cấu hình chúng cho service phải nạp model lâu trước khi mở cổng.

## Đề bài

Ở staging, model được tải từ object storage nên service mất khoảng **40 giây** mới mở cổng 8080 (biến `MODEL_FETCH_SECONDS` trong lab giả lập thời gian tải này; test luôn đặt nó là 40, giá trị bạn ghi sẽ bị ghi đè). Với manifest hiện tại, pod bị kubelet giết và khởi động lại trước khi kịp nạp xong, mãi không Ready.

Sửa `starter/eta-api.yaml` (giữ `image: eta-serve:dev`, model v1) theo các luật mà test kiểm:

1. Thêm `startupProbe` kiểu `httpGet`. Ngân sách của nó, `initialDelaySeconds + periodSeconds × failureThreshold`, phải **từ 80 đến 300 giây** (gấp đôi thời gian nạp, chịu được máy chậm, nhưng không vô hạn).
2. Giữ `livenessProbe` kiểu `httpGet` và nó vẫn phải phát hiện service treo nhanh: `initialDelaySeconds` ≤ 15 và `initialDelaySeconds + periodSeconds × failureThreshold` ≤ 60 giây. Nới liveness để che thời gian nạp là không đạt.
3. Giữ `readinessProbe` kiểu `httpGet`.

Test: chạy bản gốc (`tests/fixtures/eta-api.original.yaml`) và đòi nó tái hiện triệu chứng (pod restart); chạy bản của bạn và đòi Deployment Available, **không** restart lần nào, `/predict` trả `model_version == "v1"`.

## Tiêu chí đạt

- Bản gốc tái hiện restart; bản của bạn Ready mà `restartCount` bằng 0.
- Ngân sách startupProbe trong [80, 300] giây; liveness ≤ 60 giây; còn đủ ba probe `httpGet`.
- Giải thích được vì sao `initialDelaySeconds` lớn trên liveness là cách sửa kém hơn.

## Gợi ý

### Gợi ý 1

`kubectl --context kind-mlops -n <ns> describe pod ...`: phần Events ghi probe nào thất bại và kubelet làm gì sau đó.

### Gợi ý 2

Khi có startupProbe, kubelet chưa chạy liveness và readiness cho tới khi startupProbe thành công lần đầu.
