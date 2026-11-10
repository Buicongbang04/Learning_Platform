# Lời giải: drain worker treo và storefront thiếu pod

Lời giải nằm trong `k8s/storefront.yaml`; ba chỗ đổi.

## Nguyên nhân gốc

1. **Thiếu toleration cho pool frontend.** Từ khi `devops-lab-worker2` mang taint `olist.io/pool=frontend:NoSchedule`, storefront chỉ còn
   xếp được lên `devops-lab-worker`. Cộng với nguyên nhân 2, chỉ 1 pod chạy (`1/4`), 3 pod `Pending`. Sửa: toleration đúng key, value,
   effect của pool (`key: olist.io/pool, operator: Equal, value: frontend, effect: NoSchedule`). Storefront là frontend nên thuộc pool
   này; nhưng toleration chỉ cho phép, không ép (muốn ép thì thêm nodeAffinity tới nhãn của pool). Không dùng toleration rỗng `operator:
   Exists`: nó tolerate cả taint `unschedulable` của cordon, pod sẽ quay lại đúng node đang drain.
2. **Topology spread đếm cả node không xếp được.** `whenUnsatisfiable: DoNotSchedule` với mặc định `nodeTaintsPolicy: Ignore`: node có taint
   mà pod không tolerate vẫn là một miền trong phép đo độ lệch. Lúc sự cố, `devops-lab-worker2` (không tolerate) là miền có 0 pod, nên
   `devops-lab-worker` chỉ được giữ 1 pod (thêm pod thứ hai là lệch 2). Khi drain, `devops-lab-worker` bị cordon (taint
   `node.kubernetes.io/unschedulable`), lại thành một miền 0 pod mãi mãi: pod thay thế không được xếp ở node còn lại. Message: `0/3 nodes are
   available: 1 node(s) didn't match pod topology spread constraints, 1 node(s) had untolerated taint {node-role.kubernetes.io/
   control-plane: }, 1 node(s) had untolerated taint {olist.io/pool: frontend}`. Sửa: `nodeTaintsPolicy: Honor`, giữ nguyên `maxSkew: 1`,
   `DoNotSchedule`. Control plane đã không được tính nhờ `nodeAffinityPolicy` mặc định `Honor` cộng affinity `DoesNotExist`.
3. **PDB `minAvailable: 4` với 4 replica.** Ngân sách gián đoạn luôn là 0: không eviction nào được phép, kể cả khi đủ pod. Drain lặp `Cannot
   evict pod as it would violate the pod's disruption budget` tới hết `--timeout`. Sửa: `maxUnavailable: 1` (hay `minAvailable: 3`):
   mỗi lúc đuổi một pod, pod thay thế Ready rồi mới tới pod kế. `maxUnavailable` tự đúng khi số replica đổi (HPA), `minAvailable` cố định
   thì không.

## Vì sao các cách chữa cháy không giúp

- Xoá pod `Pending`: ReplicaSet tạo pod giống hệt, scheduler loại node với cùng lý do.
- `--disable-eviction` xoá pod thẳng, bỏ qua PDB: drain xong, nhưng storefront xuống còn số pod trên node kia (lúc sự cố là 0), và pod
  thay thế vẫn `Pending` vì nguyên nhân 1 và 2. Mất trang trong lúc bảo trì.
- Gỡ taint của pool: chữa triệu chứng bằng cách phá quyết định của platform team; pod lạ sẽ lấn vào pool frontend.

## Postmortem mẫu (rút gọn)

- **Phát hiện sớm**: alert khi Deployment `available < desired` quá 10 phút (`kube_deployment_status_replicas_unavailable`, module 13), alert
  khi PDB có `disruptionsAllowed == 0` lâu (`kube_poddisruptionbudget_status_pod_disruptions_allowed`), và khi có pod `Pending` quá 5 phút.
- **Trước bảo trì**: chạy `kubectl drain --dry-run=server` và kiểm `kubectl get pdb -A` không còn `ALLOWED DISRUPTIONS 0`.
- **Quy trình đổi pool**: thông báo cho team ứng dụng, có policy (Kyverno, ValidatingAdmissionPolicy) cảnh báo PDB có `minAvailable` bằng
  replicas, kiểm lại spread khi thêm taint.

## Lab tay: gỡ lỗi control plane và node (mục 6 của module, không chấm tự động)

**Sự cố 1, đáp án.** Khối gây sự cố sửa static pod manifest của kube-scheduler thành `--leader-elect=ture`. Kubelet tạo lại pod
scheduler từ manifest, tiến trình thoát ngay (`Error: invalid argument "ture" for "--leader-elect" flag: strconv.ParseBool`), pod mirror
`kube-scheduler-devops-ts-control-plane` ở `CrashLoopBackOff`. Pod mới của `web` đứng `Pending`, `NODE <none>`, **không có event nào**:
`FailedScheduling` là do chính scheduler ghi, scheduler chết thì không ai ghi. Bằng chứng: `kubectl -n kube-system get pods`, `docker exec
devops-ts-control-plane crictl ps -a --name kube-scheduler` (Exited, ATTEMPT tăng), `crictl logs` của container đó. Sửa: sửa đúng tệp trong
`/etc/kubernetes/manifests/` (hay chép bản lưu về); `kubectl edit` pod mirror không có tác dụng vì nguồn sự thật của static pod là tệp trên
node, kubelet ghi đè mirror.

**Sự cố 2, đáp án.** `systemctl stop kubelet`. Sau khoảng 40 giây node `NotReady`, mọi điều kiện `Unknown` với `NodeStatusUnknown: Kubelet
stopped posting node status`. Pod vẫn hiện `Running` vì không ai cập nhật trạng thái, và container vẫn chạy thật (`crictl ps`): dừng kubelet
không dừng container, kể cả API server (static pod) nên `kubectl` còn dùng được. Không còn làm được: tạo, xoá, restart container trên node đó,
probe, cập nhật status. Trên cluster nhiều node, node controller thêm taint `node.kubernetes.io/unreachable`; pod có toleration mặc định 300
giây nên khoảng 5 phút sau bị đánh dấu xoá và tạo lại ở node khác (pod StatefulSet thì không, vì sợ chạy hai bản). Chẩn đoán: `systemctl
status kubelet` (inactive), `journalctl -u kubelet` (dòng `Stopped kubelet.service`). Sửa: `systemctl start kubelet`; trong thực tế tìm vì sao
nó dừng (OOM, đĩa đầy, chứng chỉ, cấu hình lỗi trong `/var/lib/kubelet/config.yaml`).

**Rubric (10 điểm)**

| Điểm | Tiêu chí |
| --- | --- |
| 1 | Tạo và xoá cluster `devops-ts` đúng khối, kubeconfig riêng, không đụng `devops-lab` |
| 2 | Sự cố 1: chỉ ra pod Pending không có event và giải thích vì sao (ai ghi FailedScheduling) |
| 2 | Sự cố 1: bằng chứng từ `crictl ps -a`, `crictl logs` hay pod mirror, sửa đúng tệp manifest, nói được vì sao `kubectl edit` vô ích |
| 2 | Sự cố 2: đọc đúng điều kiện node, giải thích vì sao pod vẫn Running và container vẫn chạy |
| 2 | Sự cố 2: bằng chứng từ `systemctl status`, `journalctl -u kubelet`; nói được hậu quả trên cluster nhiều node (taint unreachable, 300 giây) |
| 1 | Ghi chép theo thứ tự: triệu chứng, giả thuyết, lệnh, output, kết luận |
