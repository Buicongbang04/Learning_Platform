---
title: Kueue chia quota GPU cho hai đội, mượn và đòi lại
level: intermediate
services: []
files:
  - path: starter/queues.yaml
    note: ResourceFlavor, ClusterQueue, LocalQueue còn TODO
  - path: tests/test_team_queues.py
    note: Không sửa
run:
  - bash setup/mlops/kind/up.sh --senior
  - nice -n 15 uv run pytest tracks/mlops/modules/14-kubernetes-ml-production/exercises/intermediate/02-kueue-team-queues -q
---

## Mục tiêu

Dựng hàng đợi batch job cho hai đội dùng chung 4 GPU bằng Kueue: mỗi đội có quota danh nghĩa, được mượn phần đội kia chưa dùng nhưng có giới hạn, và chủ quota lấy lại được phần của mình. Chấm bằng trạng thái `Workload` thật trên cluster.

## Đề bài

Viết `starter/queues.yaml`. Tài nguyên cluster-scoped giữ hậu tố `__RUN__` (test tạo qua `mlopskit.cluster_scoped`, thay bằng run id, xoá khi xong); GPU viết `__GPU__` (test thay bằng extended resource giả, node có **4** đơn vị). LocalQueue không ghi `namespace` (test apply vào namespace tạm).

1. ResourceFlavor `pool-__RUN__`.
2. Hai ClusterQueue `team-a-__RUN__` và `team-b-__RUN__`, mỗi cái:
   - quota danh nghĩa trên flavor `pool-__RUN__`: `cpu` **2**, `memory` **2Gi**, `__GPU__` **2**;
   - cùng một cohort có tên chứa `__RUN__` (để không trùng cohort của lần chạy khác);
   - nhận job từ mọi namespace;
   - được **mượn tối đa 1 GPU** của cohort;
   - khi chính đội đó cần lại phần quota danh nghĩa đang bị đội kia mượn, Kueue được **đẩy workload đang mượn ra** bất kể ưu tiên.
3. Hai LocalQueue `team-a`, `team-b` trỏ đúng ClusterQueue của mình. (Một namespace cho gọn; ngoài đời mỗi đội một namespace.)

Test tạo các Job busybox (mỗi pod 100m CPU, 64Mi, và GPU) theo thứ tự và kiểm `Workload`:

| Bước | Job | Kỳ vọng |
| --- | --- | --- |
| 0 | `x1`–`x4` team-a, mỗi job 1 GPU, khi team-b chưa chạy gì | **Đúng 3** job được admit (2 danh nghĩa + mượn 1), job thứ tư chờ; test xoá cả 4 rồi đi tiếp |
| 1 | `b1` team-b, 1 GPU, chạy lâu | Admit |
| 2 | `a1` team-a, 2 GPU, chạy ~90 giây | Admit (trong quota danh nghĩa) |
| 3 | `a2` team-a, 1 GPU, chạy lâu | Admit nhờ **mượn** 1 GPU của team-b |
| 4 | `a3` team-a, 1 GPU | **Không** admit sau 10 giây (đã mượn hết hạn mức) |
| 5 | `b2` team-b, 1 GPU, chạy ~5 giây | Admit trong 90 giây, và ít nhất một job của team-a bị **đẩy ra** (Workload có condition `Evicted`) |
| 6 | `a3` | Admit trong 150 giây, khi cohort có chỗ trống |

Mọi yêu cầu ở đề được chấm bằng **hành vi trên cluster** theo bảng trên; phần đọc tĩnh `queues.yaml` chỉ kiểm tên object, quota danh nghĩa 2 GPU, LocalQueue trỏ đúng ClusterQueue, và tên cohort (nếu có) chứa `__RUN__`. Giới hạn mượn đặt bằng `borrowingLimit` bên mượn hay `lendingLimit` bên cho mượn đều được, miễn hành vi đúng. Bài chạy khoảng 1–2 phút.

## Tiêu chí đạt

- `queues.yaml` đúng yêu cầu; cả 6 bước đúng trên cluster.
- Giải thích được ở bước 5 vì sao Kueue chọn đẩy workload đó, và job bị đẩy ra cần gì để không mất công (liên hệ checkpoint ở module 15).

## Gợi ý

### Gợi ý 1

API `kueue.x-k8s.io/v1beta2` (Kueue v0.20): cohort khai bằng `spec.cohortName`; hạn mức mượn là `borrowingLimit` cạnh `nominalQuota` của từng resource; chính sách đẩy ra nằm ở `spec.preemption`. `namespaceSelector` bỏ trống nghĩa là **không** namespace nào được gửi job.

### Gợi ý 2

`kubectl --context kind-mlops -n <ns> get workloads` và `kubectl ... get clusterqueue -o wide` trong lúc test chạy; `describe workload` cho thấy message khi chưa admit hoặc bị đẩy ra.
