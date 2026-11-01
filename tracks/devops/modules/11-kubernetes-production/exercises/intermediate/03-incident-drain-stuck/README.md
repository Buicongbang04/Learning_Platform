---
title: Sự cố - đêm bảo trì, drain worker treo và storefront thiếu pod
level: intermediate
services: []
files:
  - path: starter/k8s/storefront.yaml
    note: Deployment, Service, PodDisruptionBudget của storefront
  - path: tests/fixtures/incident/storefront.yaml
    note: Bản lúc sự cố, test dùng để tái hiện triệu chứng
  - path: tests/test_incident_drain_stuck.py
    note: Không sửa; có marker kube_nodes
run:
  - uv run pytest tracks/devops/modules/11-kubernetes-production/exercises/intermediate/03-incident-drain-stuck -q -rs
---

## Mục tiêu

Chẩn đoán một sự cố ở tầng node và scheduling như người trực ca bảo trì: đọc output của drain, trạng thái PodDisruptionBudget, event
`FailedScheduling` của từng node, tìm mọi nguyên nhân gốc, rồi sửa manifest của ứng dụng (không sửa node) sao cho lần bảo trì sau drain
xong mà không mất capacity.

## Đề bài

Tuần trước platform team dành `devops-lab-worker2` cho pool frontend: node đó mang taint `olist.io/pool=frontend:NoSchedule`.
`devops-lab-worker` vẫn là node dùng chung. Storefront (nginx, 4 replica) là ứng dụng frontend. Đêm qua, cửa sổ bảo trì
`devops-lab-worker`:

1. Trước giờ bảo trì, dashboard đã báo storefront `1/4` available từ lúc đổi pool; không ai để ý vì trang vẫn trả lời.
2. `kubectl drain devops-lab-worker --ignore-daemonsets --delete-emptydir-data --timeout=120s` lặp lại một dòng lỗi về eviction trong
   suốt 2 phút, rồi thoát với mã lỗi; node đứng ở trạng thái `SchedulingDisabled`.
3. Người trực thử xoá tay vài pod storefront `Pending` cho "lên lại", pod mới vẫn `Pending`.
4. Trưởng nhóm cấm dùng `--disable-eviction` hay `--force` và cấm sửa taint của node: pool frontend là quyết định của platform team.

Sửa `starter/k8s/storefront.yaml` để storefront đủ 4 pod trải trên cả hai worker trong giờ thường, và drain `devops-lab-worker` xong
mà lúc nào cũng còn ít nhất 3 pod available. Giữ nguyên thiết kế: 4 replica; ràng buộc trải đều `maxSkew: 1` theo
`kubernetes.io/hostname` với `whenUnsatisfiable: DoNotSchedule`; không chạy trên control plane; có PodDisruptionBudget. Viết postmortem
ngắn (không chấm tự động): nguyên nhân gốc từng triệu chứng, cách phát hiện trước đêm bảo trì.

**Cách test chấm.** Bài thao tác node nên tệp test có marker `kube_nodes`; testkit giữ khoá node suốt bài, các bài thao tác node khác chờ
tới lượt. Hai `KubeLab` chạy lần lượt; mỗi lab trước tiên taint `devops-lab-worker2` bằng `lab.node_action` như platform team, và khi
đóng thì gỡ taint, uncordon, chờ CoreDNS, Gateway, metrics-server available lại.

| Lab | Làm | Kiểm |
| --- | --- | --- |
| Tái hiện | Apply `tests/fixtures/incident/` (giống starter), chờ 30 giây, drain `devops-lab-worker` | Có pod storefront `Pending`; event `FailedScheduling` nhắc taint `olist.io/pool: frontend` và topology spread; drain thất bại với lỗi về disruption budget |
| Bài của bạn | Apply `k8s/`, `rollout status` 120 giây | Đủ 4 pod, mỗi worker ít nhất 1 |
| | Đọc Deployment | Như ràng buộc ở trên; toleration nào cũng có `key` |
| | Đọc PDB | Khi đủ 4 pod, `status.disruptionsAllowed` đúng bằng 1 |
| | `node_action` drain `devops-lab-worker`, theo dõi mỗi giây | Drain thành công; `availableReplicas` thấp nhất trong lúc drain ≥ 3; sau drain đủ 4 pod, cả 4 trên `devops-lab-worker2` |

Khoảng 3 phút khi đã sửa, 5 phút trên starter (drain chờ hết 120 giây). Không chạy bài này song song với bài khác dùng cluster.

## Tiêu chí đạt

- Mọi test pass, kể cả ca tái hiện.
- Postmortem chỉ ra nguyên nhân gốc của từng triệu chứng và một cách phát hiện tự động cho mỗi cái.
- Giải thích được vì sao xoá tay pod `Pending` không giúp gì, và vì sao `--disable-eviction` sẽ "chữa" được triệu chứng 2 nhưng làm sự
  cố tệ hơn.

## Gợi ý

### Gợi ý 1

Tái hiện trong namespace riêng bằng kubeconfig admin (không chạy khi test đang chạy, và gỡ taint, uncordon ngay sau đó):
`kubectl taint nodes devops-lab-worker2 olist.io/pool=frontend:NoSchedule`, apply starter, rồi đọc `kubectl get pdb`, `kubectl get pods
-o wide`, `kubectl get events --field-selector reason=FailedScheduling`. Message của scheduler liệt kê lý do loại **từng** node.

### Gợi ý 2

`kubectl explain pod.spec.topologySpreadConstraints` có hai trường quyết định node nào được tính khi đo độ lệch; node đang cordon mang
một taint. `kubectl explain pdb.spec`: `minAvailable` và `maxUnavailable` khác nhau thế nào khi số replica bằng đúng `minAvailable`?
