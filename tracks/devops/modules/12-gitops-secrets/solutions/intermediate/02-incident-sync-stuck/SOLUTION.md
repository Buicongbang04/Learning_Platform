# Lời giải: sync kẹt vì hook PreSync phụ thuộc resource của phase Sync

## Nguyên nhân gốc

`migrate` là hook `PreSync`. ArgoCD chạy mọi hook PreSync trước khi apply bất kỳ resource thường nào của lần sync đó. Job đọc ConfigMap
`olist-config-<hash>` và gọi Postgres, cả hai là resource thường (phase `Sync`). Trên namespace trống:

1. ArgoCD tạo Job `migrate`; pod không tạo được container vì ConfigMap chưa có (`CreateContainerConfigError`). Nếu ConfigMap có sẵn, pod
   chạy rồi lỗi vì chưa có Service `postgres`.
2. Job không có `activeDeadlineSeconds`, và pod kẹt ở `CreateContainerConfigError` không bao giờ tính là failed, nên Job không bao giờ xong
   hay hỏng. Hook không xong thì thao tác sync `Running` mãi (triệu chứng 1, 2, 4).
3. Auto-sync không bắt đầu thao tác mới khi thao tác cũ chưa kết thúc: commit mới chỉ làm Application OutOfSync thêm, không được apply
   (triệu chứng 3). Đây là hành vi có chủ ý của ArgoCD: một lần sync là một thao tác có thứ tự, không bị ngắt giữa chừng.
4. Xoá namespace rồi tạo lại là quay về đúng điều kiện ban đầu (triệu chứng 5).

Staging không lộ ra vì khi hook được thêm vào, ConfigMap và Postgres đã có từ các lần sync trước; ConfigMap có hậu tố hash nhưng lần đó
cấu hình không đổi nên tên cũ vẫn đúng. Lỗi nằm im tới lần đầu chạy trên namespace trống, hay lần đầu đổi cấu hình cùng lúc với một hook.

## Sửa

`migrate.yaml`:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/hook: Sync
    argocd.argoproj.io/sync-wave: "1"
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation,HookSucceeded
spec:
  backoffLimit: 2
  activeDeadlineSeconds: 180
```

`api.yaml`: Deployment api có `argocd.argoproj.io/sync-wave: "2"`. `application.yaml` thêm:

```yaml
syncPolicy:
  retry:
    limit: 3
    backoff:
      duration: 10s
      factor: 2
      maxDuration: 2m
```

- Hook phase `Sync`, wave 1: chạy sau mọi resource wave 0 của phase Sync (ConfigMap, Postgres, Redis, Service) **và** sau khi chúng
  healthy (Deployment postgres Available nhờ readinessProbe `pg_isready`). ArgoCD chờ mỗi wave healthy rồi mới sang wave kế.
- api ở wave 2: chỉ được tạo khi `migrate` đã `Succeeded`, nên không có pod api nào nhận traffic trên schema cũ.
- `BeforeHookCreation`: Job tên cố định; lần sync sau xoá Job cũ trước khi tạo lại. `HookSucceeded` dọn Job khi xong. Đổi sang
  `generateName` cũng được, nhưng Job cũ sẽ chồng chất nếu không có policy xoá.
- `backoffLimit: 2`, `activeDeadlineSeconds: 180`: migration hỏng thì Job failed trong 3 phút, hook failed, thao tác sync `Failed`, auto-sync
  thử lại theo `retry` rồi dừng; commit sửa tiếp theo được sync thay vì xếp hàng sau một thao tác treo.

Cách khác cũng qua test: giữ `PreSync` cho `migrate` nhưng tự chứa (không phụ thuộc gì trong repo) và chuyển postgres ra ngoài phase Sync
(database managed, hay một Application khác sync trước bằng app-of-apps với sync wave). Không qua: đổi `migrate` sang `PostSync` (api chạy
trước migration) hay bỏ hẳn hook (Job thường không chạy lại khi template không đổi, và đổi template của Job là lỗi immutable).

## Gỡ khi đang kẹt trên cluster thật

- Huỷ thao tác: `kubectl -n <ns> patch application olist-shop --type merge -p '{"status":{"operationState":{"phase":"Terminating"}}}'`,
  hay `argocd app terminate-op olist-shop` (cần quyền admin của ArgoCD; trong lab, token của bạn không sửa được `status`, xem mục 0).
- Sau khi huỷ, commit bản sửa; auto-sync bắt đầu thao tác mới trên commit đó.
- Đừng xoá Job hook bằng tay khi thao tác còn chạy: ArgoCD gắn finalizer `argocd.argoproj.io/hook-finalizer` cho hook và chờ kết quả của
  nó; xoá Application trong lúc đó để lại Job kẹt finalizer, namespace kẹt Terminating (testkit gỡ finalizer này khi dọn lab).

## Postmortem mẫu (rút gọn)

- **Nguyên nhân gốc**: hook PreSync phụ thuộc resource của phase Sync; Job không có hạn nên hỏng thành treo.
- **Vì sao staging không thấy**: phụ thuộc đã tồn tại từ trước; lỗi chỉ lộ trên namespace trống.
- **Vì sao commit mới không cứu**: một thao tác sync phải kết thúc thì auto-sync mới bắt đầu thao tác khác.
- **Phát hiện sớm**: CI dựng namespace trống (hay cluster kind) và sync repo từ đầu cho mọi PR đổi hook hay wave; alert khi
  `operationState.phase` là `Running` quá 10 phút (so `operationState.startedAt` với giờ hiện tại); mọi Job hook bắt buộc có
  `activeDeadlineSeconds` (kiểm bằng policy hay test như test của bài).
