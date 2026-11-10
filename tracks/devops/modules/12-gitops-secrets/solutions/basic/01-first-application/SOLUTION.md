# Lời giải: Application đầu tiên

## Cách làm

`kustomization.yaml` thêm `configMapGenerator` `olist-config` với bốn literal. Kustomize sinh ConfigMap `olist-config-<hash>` và sửa tham
chiếu `configMapRef` trong Deployment api theo đúng tên đó. Đổi một literal là đổi hash, đổi tên, đổi pod template, nên Deployment rollout.
ConfigMap viết tay thì pod giữ cấu hình cũ tới lần khởi động sau.

`application.yaml`:

```yaml
spec:
  source:
    path: shop
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - ApplyOutOfSyncOnly=true
```

- `automated`: controller so trạng thái mong muốn (render từ commit cuối của `main`) với trạng thái thật. Khác nhau vì có commit mới thì
  tự sync. Không có `automated` thì Application chỉ báo `OutOfSync` và chờ người bấm sync.
- `prune: true`: object có trong lần sync trước nhưng không còn trong Git (ConfigMap `legacy-flags`, ConfigMap `olist-config-<hash cũ>`)
  bị xoá. Tắt prune thì chúng còn mãi, Application báo cần prune.
- `selfHeal: true`: khác biệt do sửa tay trên cluster (`kubectl scale`, `kubectl edit`) cũng làm sync, sau một khoảng chờ ngắn. Tắt
  self-heal thì auto-sync chỉ chạy khi Git đổi; drift nằm đó tới commit sau.
- `ApplyOutOfSyncOnly=true` (tuỳ chọn): mỗi lần sync chỉ apply object đang lệch, đỡ tải với app nhiều object.

## Vì sao test chấm như vậy

Ba bước của test là ba nguyên tắc GitOps nhìn từ ngoài: trạng thái khai báo trong Git (commit 1), Git là nguồn sự thật duy nhất nên cái
gì rời Git thì rời cluster (commit 2), và vòng reconcile liên tục kéo cluster về Git (drift). Test đọc trạng thái bằng token của lab,
chờ đúng SHA của commit cuối (`argocd_wait`) chứ không chỉ chờ `Synced`, vì ngay sau khi đẩy commit mới, Application còn báo `Synced` với
commit cũ trong vài giây.

## Sai lầm hay gặp

- `path: gitops/shop`: repo của lab có gốc là nội dung thư mục `gitops/`, nên path là `shop`.
- Ghi `namespace:` trong manifest hay trong kustomization: ArgoCD đặt namespace theo `destination` cho object không ghi namespace; ghi
  cứng thì lab khác namespace và AppProject từ chối.
- Bật `selfHeal` cho một Deployment có HPA: HPA đổi `replicas`, ArgoCD kéo về, hai bên giằng co. Bỏ `replicas` khỏi manifest hay
  `ignoreDifferences` cho `/spec/replicas`.
- Thêm finalizer `resources-finalizer.argocd.argoproj.io` khi chưa hiểu: xoá Application là xoá luôn mọi object của nó. Đúng ý khi dọn
  môi trường preview, nguy hiểm khi chỉ muốn đổi tên Application.

## Lab tay

Chạy test của bài, và ở một terminal khác quan sát `kubectl --kubeconfig ~/.kube/devops-lab.yaml get applications.argoproj.io -A -w` cùng
`kubectl --kubeconfig ~/.kube/devops-lab.yaml get events -A -w`: thấy lúc controller phát hiện commit mới, lúc prune, lúc self-heal kéo
replicas về. Muốn tự tay với repo của bạn, dùng cluster kind riêng dùng một lần như mục 0 của module.
