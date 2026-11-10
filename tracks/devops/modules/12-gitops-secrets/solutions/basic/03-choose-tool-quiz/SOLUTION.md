# Lời giải: trắc nghiệm chọn công cụ GitOps và secret

| Câu | Đáp án | Giải thích ngắn |
| --- | --- | --- |
| gitops-pull | b | Mô hình pull: agent trong cluster đọc Git và tự apply, CI chỉ ghi repo. Kubeconfig admin không còn nằm trong CI, API server không phải mở cho bên ngoài. Webhook từ Git chỉ để báo "có commit mới", không mang manifest |
| argocd-or-flux | c | Nhiều team cần tự xem và bấm sync: ArgoCD bản đầy đủ có UI, SSO (Dex, OIDC), RBAC theo AppProject. Flux không có UI chính thức, hợp với team platform thích mọi thứ là CRD và CLI. CronJob tự viết thiếu health, diff, prune; Helm từ máy dev không phải GitOps |
| self-heal-drift | c | `automated` chỉ phản ứng khi Git đổi. Không bật `selfHeal`, drift do sửa tay làm Application OutOfSync nhưng không bị sửa tới commit sau hay lần sync tay. API server không biết gì về ArgoCD |
| prune-off | a | `prune: false` nghĩa là sync không xoá; ArgoCD đánh dấu object "cần prune" và Application OutOfSync. Sync tay với prune hay bật prune thì mới xoá |
| presync-order | b | Phase chạy theo thứ tự PreSync, Sync, PostSync; hook PreSync chạy trước mọi resource thường. Namespace trống thì ConfigMap, Redis chưa có: pod kẹt `CreateContainerConfigError` hay lỗi kết nối, sync kẹt |
| sops-what | c | `encrypted_regex` chỉ mã hoá giá trị dưới `data`/`stringData`; tên khoá, kind, metadata còn rõ nên review và diff vẫn có nghĩa. Base64 trong Secret không phải mã hoá |
| sops-recipients | b | Data key chỉ được bọc cho recipient của team; sidecar của ArgoCD không có khoá nào mở được nên `sops --decrypt` lỗi, render lỗi, Application báo ComparisonError. Repo-server không bao giờ đọc `~/.config/sops` của ai |
| key-rotation | d | Lịch sử Git còn mọi bản mã hoá cũ mà khoá đó mở được. Gỡ recipient và `updatekeys` chỉ bảo vệ bản mới; phải xoay giá trị. `filter-repo` không thu hồi được bản ai đó đã clone |
| sealed-vs-sops | a | SealedSecret chỉ controller của một cluster mở được (khoá riêng nằm trong cluster); muốn nhiều cluster phải seal nhiều lần hay chia khoá. SOPS mã hoá cho nhiều recipient (age, KMS, Vault transit), người và cluster cùng đọc được |
| eso-when | b | Nguồn sự thật đã là AWS Secrets Manager và có xoay tự động: Git chỉ nên chứa tham chiếu. External Secrets Operator đọc bằng IAM, ghi Secret của Kubernetes và làm mới định kỳ. ConfigMap không dành cho bí mật; Sealed Secrets không đọc secret manager |
| vault-token-ttl | b | `explicit_max_ttl` là trần cứng tính từ lúc tạo; gia hạn chỉ kéo dài tới trần đó. Sau 1 giờ token chết, app phải đăng nhập lại (Vault Agent làm việc này tự động) |
| kv-v2-paths | c | KV v2 đặt dữ liệu dưới `data/` và metadata dưới `metadata/`. Policy viết theo path của CLI (`secret/olist/api/*`) không khớp path API thật (`secret/data/olist/api/db`) nên bị từ chối. Basic 02 |
| secret-leak-first | a, b, d | Coi như đã lộ ngay khi public: xoay trước, kiểm log để biết có ai dùng chưa, điều phối qua kênh sự cố. Chờ xem rồi mới xoay là để cửa mở; viết lại lịch sử là việc dọn dẹp sau cùng |
| gitops-fit | a, b, d | GitOps kiểu pull mạnh nhất khi có nhiều cluster, cần audit qua PR, và cluster không mở API server cho CI. Một VM chạy cron không có agent reconcile nào để kéo; dùng Ansible hay pipeline thường (c sai) |
