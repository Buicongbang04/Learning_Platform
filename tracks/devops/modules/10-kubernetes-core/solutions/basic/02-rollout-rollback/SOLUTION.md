# Lời giải: rollout và rollback không mất capacity

Lời giải: `api.yaml`, `release.sh`, `rollback.sh`.

## Strategy

- `maxUnavailable: 0`, `maxSurge: 1`: controller chỉ scale ReplicaSet cũ xuống khi một pod mới đã Ready (và đã Ready
  `minReadySeconds` giây). Bản mới lỗi thì có đúng một pod mới kẹt, bốn pod cũ vẫn phục vụ. Với mặc định 25%, `maxUnavailable` của
  4 replica là 1 (làm tròn xuống), nên controller xoá một pod cũ ngay khi bắt đầu; với 3 replica 25% làm tròn xuống thành 0, tình cờ
  an toàn. Viết số tuyệt đối để không phụ thuộc số replica.
- `progressDeadlineSeconds: 60`: quá 60 giây không tiến triển thì Deployment có condition `Progressing=False`,
  `reason=ProgressDeadlineExceeded`; `rollout status` thoát mã khác 0. Mặc định là 600 giây: pipeline đợi 10 phút mới biết.
  Deadline **không** tự rollback; nó chỉ báo.
- `revisionHistoryLimit: 5`: giữ 5 ReplicaSet cũ (scale 0) để quay lui. Đặt 0 là mất `rollout undo`.

## release.sh

Pause, đổi env, ghi change-cause, resume: controller chỉ tạo **một** ReplicaSet mới, và annotation đã có trên Deployment khi
ReplicaSet đó được tạo, nên `rollout history` ghi đúng `release 1.2` cho đúng revision mà không phụ thuộc thời điểm. `kubectl set env` với nhiều cặp trong một
lệnh cũng chỉ là một revision. `--record` đã bị bỏ, đừng dùng.

Script không tự rollback: rollout kẹt với `maxUnavailable: 0` không gây mất capacity, người trực có thời gian xem log của pod mới
(`kubectl logs deploy/api` chọn một pod bất kỳ, nên dùng `kubectl logs -l app.kubernetes.io/name=api --prefix`) rồi mới quyết định.
Pipeline nào tự rollback thì phải ghi lại rõ vì sao, nếu không lỗi bị che đi.

## rollback.sh và ReplicaSet

`kubectl rollout undo` chép pod template của revision đích vào Deployment. Template đó có cùng `pod-template-hash` với ReplicaSet cũ,
nên controller scale ReplicaSet cũ lên lại chứ không tạo cái mới; revision đó nhận số mới nhất (ví dụ revision 2 thành revision 4,
số 2 biến mất khỏi history). `--to-revision=1` dùng số trong `kubectl rollout history`.

## Đọc thêm

- Blue/green và canary trên Kubernetes thuần: hai Deployment (`api-blue`, `api-green`) và đổi selector của Service (blue/green),
  hay hai Deployment cùng nhãn chung và tỉ lệ replica (canary thô). Canary theo phần trăm request cần Gateway API (trọng số của
  `HTTPRoute`), service mesh (module 15) hay Argo Rollouts.
- `kubectl rollout pause` còn dùng để gom nhiều thay đổi (image, env, resources) thành một revision.
