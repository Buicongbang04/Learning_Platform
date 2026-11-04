---
title: PriorityClass và preemption cho serving, research, training
level: basic
services: []
files:
  - path: starter/priorityclasses.yaml
    note: Ba PriorityClass, còn TODO
  - path: tests/test_preemption.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh --senior
  - nice -n 15 uv run pytest tracks/mlops/modules/14-kubernetes-ml-production/exercises/basic/02-priority-preemption -q
---

## Mục tiêu

Biểu diễn chính sách ưu tiên của một nền tảng ML bằng PriorityClass và thấy scheduler thực thi nó: pod serving lấy GPU bằng cách đẩy pod training ra, còn pod research được xếp trước training nhưng không bao giờ đẩy ai.

## Đề bài

Viết `starter/priorityclasses.yaml` gồm ba PriorityClass. Tên giữ nguyên hậu tố `__RUN__`: PriorityClass là tài nguyên cluster-scoped, test tạo qua `mlopskit.cluster_scoped` để thay `__RUN__` bằng run id và xoá khi xong.

| PriorityClass | Yêu cầu |
| --- | --- |
| `ml-serving-__RUN__` | Cao nhất trong ba; được đẩy pod ưu tiên thấp hơn ra (`preemptionPolicy` mặc định hoặc `PreemptLowerPriority`) |
| `ml-research-__RUN__` | Thấp hơn serving, cao hơn training; **không bao giờ** đẩy pod khác ra |
| `ml-training-__RUN__` | Thấp nhất, lớn hơn 0 |

Cả ba: `value` là số nguyên dưới 1 000 000 000 (từ đó trở lên dành cho class hệ thống), **không** `globalDefault: true` (cluster dùng chung: class mặc định áp cho mọi pod mới của mọi người; test từ chối apply). Nên có `description`.

Test tạo GPU giả 2 đơn vị trên node, rồi:

1. Hai pod training, mỗi pod 1 GPU, chạy.
2. Một pod research 1 GPU: phải đứng `Pending` 15 giây, hai pod training vẫn chạy.
3. Một pod serving 1 GPU: phải chạy được trong 120 giây, đúng một pod training bị đẩy ra, pod research vẫn `Pending`.

## Tiêu chí đạt

- Ba class đúng thứ tự và chính sách; kịch bản trên chạy đúng trên cluster.
- Giải thích được vì sao pod research có ưu tiên cao hơn training mà vẫn không được chạy ở bước 2, và nó sẽ chạy khi nào.

## Gợi ý

### Gợi ý 1

Xem trường `preemptionPolicy` trong tài liệu "Pod Priority and Preemption" của Kubernetes (mục 7 lý thuyết): có hai giá trị.

### Gợi ý 2

Theo dõi bằng tay: `kubectl --context kind-mlops -n <ns> get pods -w` và `kubectl ... get events --sort-by=.lastTimestamp` (tìm sự kiện `Preempted`).
