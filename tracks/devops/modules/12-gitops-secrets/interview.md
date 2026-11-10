# Câu hỏi phỏng vấn: GitOps & secrets

## GitOps là gì, và nó khác pipeline CI chạy `kubectl apply` ở đâu?

GitOps là cách vận hành trong đó trạng thái mong muốn của hệ thống được khai báo trong Git, và một agent trong hệ thống tự kéo trạng
thái đó về rồi liên tục reconcile (OpenGitOps: declarative, versioned and immutable, pulled automatically, continuously reconciled).
Pipeline `kubectl apply` đạt hai nguyên tắc đầu nhưng thiếu hai nguyên tắc sau:

- **Credential**: kiểu push cần kubeconfig có quyền ghi cluster nằm trong CI; kiểu pull thì CI chỉ ghi repo, credential cluster không rời
  cluster, API server không phải mở cho runner.
- **Reconcile liên tục**: pipeline chạy một lần rồi thôi; ai đó `kubectl edit` sau đó thì không ai biết. Agent GitOps thấy drift ngay
  (OutOfSync) và sửa nếu bật self-heal.
- **Nguồn sự thật**: "production chạy gì" là commit mà Application báo Synced; rollback là `git revert`.

## Giải thích `automated`, `prune` và `selfHeal` trong sync policy của ArgoCD. Khi nào bạn tắt từng cái?

- `automated`: Git đổi (commit mới) thì tự sync. Tắt khi muốn mọi lần deploy có người bấm (production ở tổ chức cần duyệt lúc deploy chứ
  không chỉ lúc merge), hay tạm thời khi điều tra sự cố.
- `prune`: xoá object không còn trong Git. Tắt (hay `PruneLast`, hay `Prune=false` trên từng object) cho production khi một PR lỡ xoá
  Service hay PVC sẽ gây mất dịch vụ ngay; khi đó Application báo OutOfSync và người quyết định prune.
- `selfHeal`: drift do sửa tay cũng làm sync. Tắt khi có controller khác hợp lệ cùng sửa object (HPA với `replicas`, operator ghi
  annotation) mà chưa cấu hình `ignoreDifferences`; hay trong lúc sự cố cần sửa nóng. Bật self-heal là cam kết "mọi thay đổi đi qua Git",
  nên phải có đường khẩn cấp được ghi trong runbook.

## Sync wave và hook hoạt động thế nào? Kể một lỗi bạn từng gặp với chúng.

Một lần sync chạy theo phase (PreSync, Sync, PostSync; SyncFail khi lỗi), trong phase theo wave tăng dần (mặc định 0), trong wave theo kind
rồi tên; ArgoCD chờ mọi object của một wave healthy mới sang wave kế. Hook là object có annotation `argocd.argoproj.io/hook`, thường là Job,
chạy mỗi lần sync; `hook-delete-policy` quyết định khi nào xoá (mặc định `BeforeHookCreation`).

Lỗi điển hình: Job smoke test là hook PostSync dùng image có tag gõ sai. Pod kẹt `ImagePullBackOff`, mà pod kẹt như vậy không bao giờ làm
Job failed; Job không có `activeDeadlineSeconds` nên thao tác sync `Running` mãi, và commit sửa tag cũng không vào được vì auto-sync chờ thao
tác cũ kết thúc. Gỡ: admin huỷ thao tác (`argocd app terminate-op`), commit bản sửa. Phòng: mọi Job hook có `backoffLimit` nhỏ và
`activeDeadlineSeconds`, Application có `retry` giới hạn, alert khi thao tác `Running` quá 10 phút, và CI thử sync repo trên namespace trống.

## Application `Synced` nhưng `Degraded`, và một Application khác `OutOfSync` mãi dù vừa sync xong. Bạn gỡ thế nào?

Sync và health là hai trục. `Synced` + `Degraded`: ArgoCD đã áp đúng Git, và thứ trong Git hỏng (rollout vượt `progressDeadlineSeconds`,
Job failed, pod CrashLoop). Đi xuống object: `kubectl describe`, event, log; sửa trong Git.

`OutOfSync` mãi: có trường live khác manifest dù vừa apply. Xem diff của từng object (`status.resources`, `argocd app diff`). Nguyên nhân hay
gặp: controller khác ghi trường đó (HPA ghi `replicas`, cert-manager ghi `caBundle` vào webhook), mutating webhook thêm sidecar, API server
chuẩn hoá giá trị (`cpu: 1000m` thành `1`), hay CRD có default. Sửa: bỏ trường khỏi manifest, `ignoreDifferences` (kèm
`RespectIgnoreDifferences=true` để sync cũng không ghi đè), hay bật server-side diff để so sánh theo đúng cách API server merge.

## ArgoCD hay FluxCD? Bạn chọn thế nào cho một công ty 30 team ứng dụng?

Cả hai đạt nguyên tắc GitOps và là dự án CNCF graduated. Khác ở mô hình người dùng:

- ArgoCD có UI, SSO, RBAC theo AppProject, sync và rollback từ UI, quản nhiều cluster từ một chỗ; hook và wave để sắp thứ tự. Helm được
  render thành manifest (không có release Helm).
- Flux là bộ controller CRD, không UI chính thức, mỗi cluster thường tự quản mình; `HelmRelease` dùng Helm SDK thật; SOPS và image automation
  có sẵn.

30 team ứng dụng muốn tự xem trạng thái và bấm sync: ArgoCD, mỗi team một AppProject gắn nhóm SSO, sync bằng impersonation. Team platform
nhỏ quản add-on của nhiều cluster edge, không ai cần UI: Flux hợp hơn. Không nên chạy cả hai cho cùng một tập object.

## AppProject dùng để làm gì? Nếu chỉ dùng project `default` thì rủi ro gì?

AppProject là ranh giới đa tenant: repo nào được dùng (`sourceRepos`), đích nào (`destinations`: cluster và namespace), kind cluster-scoped
nào được tạo (`clusterResourceWhitelist`), kind nào bị cấm trong namespace, ai làm gì trong ArgoCD (`roles`), khung giờ cấm sync
(`syncWindows`), và ServiceAccount nào thực sự apply (`destinationServiceAccounts`).

Project `default` cho phép mọi repo, mọi cluster, mọi namespace, mọi kind: ai tạo được Application là deploy được ClusterRoleBinding
`cluster-admin` hay ghi vào namespace của team khác. Nên khoá `default` ngay sau khi cài. Ngoài ra, nội dung AppProject chưa đủ: phải kiểm soát
ai ghi được Application và AppProject, vì ví dụ ArgoCD 3.5 không đối chiếu `operation.sync.source` của Application với `sourceRepos`.

## Cấu trúc repo GitOps cho staging và production thế nào? Vì sao không dùng nhánh cho từng môi trường?

Repo GitOps tách repo code; `base/` chứa thứ chung, `envs/<môi trường>/` là overlay chỉ chứa khác biệt (namespace, image, replica, cấu
hình), `apps/` chứa Application cho từng môi trường cộng một Application gốc (app-of-apps) hay một ApplicationSet. Mọi Application theo
`main`.

Nhánh cho môi trường: promote là merge, mà merge kéo theo mọi thay đổi khác trên nhánh nguồn, kể cả thứ chưa muốn lên production; hai nhánh
lệch dần (hotfix chỉ vào production); và câu hỏi "staging khác production chỗ nào" phải trả lời bằng `git diff` giữa hai nhánh lẫn lộn
lịch sử. Thư mục trên một nhánh: `diff envs/staging envs/production` là đủ, promote là một PR nhỏ sửa đúng một dòng.

## Promote một bản từ staging lên production nên làm thế nào cho chắc chạy đúng thứ đã test?

Build một lần, promote cùng một artifact. CI build image một lần, ghi digest; bot cập nhật overlay staging; khi staging đạt (smoke, e2e,
soak), một PR chép **digest** đó vào overlay production; người duyệt theo CODEOWNERS; sync window chặn lúc đóng băng. Không build lại cho
production, không dùng tag trôi. Tag dễ đọc cho người nhưng ghi đè được; digest bất biến. Sau sync, theo dõi SLO một khoảng; vượt ngưỡng
thì `git revert` PR promote. Công cụ như Kargo hay Argo CD Image Updater tự động hoá phần cập nhật overlay.

## Kubernetes Secret có an toàn để commit vào Git không? Các cách đưa secret vào GitOps?

Không. Secret là base64, ai đọc repo là đọc được giá trị, và lịch sử Git giữ mãi mọi bản clone. Ba hướng:

1. Mã hoá trong Git: SOPS (theo trường, nhiều recipient: age, KMS, Vault transit), Sealed Secrets (mã hoá bằng public key của controller
   trong cluster).
2. Tham chiếu trong Git: External Secrets Operator hay Secrets Store CSI Driver đọc từ AWS Secrets Manager, GCP Secret Manager, Azure Key
   Vault, Vault.
3. App tự lấy lúc chạy: Vault Agent, SDK của secret manager.

Dù cách nào, khi giá trị đã vào Kubernetes Secret thì nó nằm trong etcd và trong pod: RBAC trên `secrets` và encryption at rest vẫn cần.

## SOPS mã hoá thế nào? Thêm một người vào team, và một người rời team, bạn làm gì?

Mỗi tệp có một data key ngẫu nhiên; mọi giá trị (theo `encrypted_regex`, thường chỉ `data`/`stringData`) mã hoá AES256-GCM bằng data key;
data key được bọc riêng cho từng recipient trong khối `sops`; một MAC trên toàn bộ giá trị phát hiện sửa trái phép. `.sops.yaml` chọn
recipient theo đường dẫn tệp.

Thêm người: thêm public key của họ vào `.sops.yaml`, `sops updatekeys` mọi tệp khớp rule; chỉ data key được bọc lại. Người rời team: gỡ
recipient và `updatekeys` chỉ bảo vệ bản mới; mọi commit cũ vẫn mở được bằng khoá của họ. Nếu họ có thể còn khoá và bản clone (hay khoá có
thể lộ), xoay luôn các giá trị. Đây là lý do nhiều tổ chức dùng KMS làm recipient (thu hồi bằng IAM, có audit) hay chuyển sang secret manager
cho secret đổi thường xuyên.

## So sánh Sealed Secrets, SOPS và External Secrets Operator.

| | Sealed Secrets | SOPS | External Secrets Operator |
| --- | --- | --- | --- |
| Git chứa | SealedSecret mã hoá | Tệp mã hoá theo trường | Tham chiếu tới secret |
| Ai mở được | Chỉ controller của cluster đó | Mọi recipient (người, cluster, KMS) | Secret manager bên ngoài |
| Xoay giá trị | Seal lại, commit | Sửa, commit | Ở secret manager, tự đồng bộ |
| Rủi ro chính | Mất khoá controller là mất mọi secret; nhiều cluster phải seal nhiều lần | Quản khoá riêng cho người; lịch sử Git giữ bản cũ | Phụ thuộc secret manager; quyền IAM của operator rất rộng |

Chọn ESO khi đã có secret manager và cần xoay tự động; SOPS khi ít secret, muốn mọi thứ trong Git hay chạy offline; Sealed Secrets khi một
cluster và không ai cần đọc lại giá trị.

## Viết policy Vault cho api chỉ đọc secret của nó trên KV v2. Lỗi hay gặp là gì?

```hcl
path "secret/data/olist/api/*" {
  capabilities = ["read"]
}

path "secret/metadata/olist/api/*" {
  capabilities = ["list"]
}
```

Lỗi hay gặp: viết `path "secret/olist/api/*"` theo path của CLI. KV v2 đặt dữ liệu dưới `data/`, metadata dưới `metadata/`, xoá vĩnh viễn
qua `destroy/` và `metadata/`; policy không khớp path API thì bị từ chối (mặc định deny). Lỗi thứ hai: cấp `KV/*` với đủ capability "cho
chạy trước đã", tức api xoá được secret của service khác. `vault kv get -output-policy` in policy tối thiểu cho một lệnh.

## TTL, max TTL và period của token Vault khác nhau thế nào? App nên lấy token ra sao?

- `ttl`: sống bao lâu nếu không gia hạn.
- `explicit_max_ttl`: trần cứng tính từ lúc tạo; gia hạn không vượt được, hết thì phải đăng nhập lại.
- `period`: token gia hạn được mãi, mỗi lần tối đa một period, cho daemon chạy lâu.

App không nên cầm token tĩnh do người tạo. App đăng nhập bằng danh tính của nó qua auth method (Kubernetes auth với token ServiceAccount,
AWS IAM auth), nhận token TTL ngắn gắn policy theo role; Vault Agent (sidecar) lo đăng nhập, gia hạn và ghi secret ra tệp. Token root chỉ
dùng lúc dựng hệ thống rồi thu hồi.

## Dynamic secret là gì? Lợi và hại so với mật khẩu tĩnh trong secret manager?

Vault (hay OpenBao) sinh credential theo yêu cầu: database secrets engine tạo một user Postgres mới cho mỗi lần app xin, kèm lease 1 giờ,
hết lease thì xoá user. Tương tự cho IAM của AWS, chứng chỉ PKI, SSH.

Lợi: không còn mật khẩu dùng chung lâu năm; mỗi pod một user nên audit biết ai làm gì; lộ một credential chỉ lộ tới hết lease; thu hồi hàng
loạt bằng `lease revoke -prefix`. Hại: Vault nằm trên đường khởi động của app (Vault chết thì app mới không lên), app phải chịu được credential
đổi (pool kết nối làm mới), Postgres có nhiều user tạm, và cần người vận hành Vault HA.

## Một mật khẩu production vừa bị push lên repo GitHub công khai. 30 phút đầu bạn làm gì?

1. Coi như đã lộ: bot quét repo công khai trong vài phút, xoá commit không thu hồi được bản đã bị chép.
2. Tuyên bố sự cố, một người điều phối, kênh riêng.
3. Xoay mật khẩu (hay thu hồi token, khoá) và cập nhật nơi dùng nó (qua Git, ArgoCD sync), kiểm dịch vụ chạy lại.
4. Kiểm log truy cập của hệ thống từ thời điểm push; có dấu hiệu dùng trái phép thì mở rộng phạm vi điều tra.
5. Sau đó mới dọn: xoá commit (`git filter-repo`), fork, nhờ GitHub xoá cache.
6. Postmortem blameless: vì sao hệ thống cho phép (khoá trong thư mục repo, thiếu pre-commit hook, push protection không che fork, cảnh báo
   tới một người), action item có người và hạn.

## Thiết kế quản lý secret cho một công ty chạy 3 cluster EKS, 20 microservice, có yêu cầu audit và xoay mật khẩu DB 30 ngày.

- **Nguồn sự thật**: AWS Secrets Manager (đã ở AWS, có xoay tự động cho RDS bằng Lambda, audit qua CloudTrail). Secret đặt tên theo
  `<môi trường>/<service>/<tên>`, IAM policy theo tiền tố.
- **Vào cluster**: External Secrets Operator, `ClusterSecretStore` mỗi cluster dùng IRSA (hay EKS Pod Identity) với quyền đọc đúng tiền tố
  môi trường của cluster đó; `ExternalSecret` trong repo GitOps chỉ chứa tham chiếu, `refreshInterval` 1 giờ; Deployment rollout khi Secret
  đổi (Reloader hay hash annotation).
- **Ngoại lệ trong Git**: cấu hình bootstrap trước khi ESO chạy (ví dụ credential của chính ESO nếu không dùng IRSA) mã hoá bằng SOPS với
  KMS làm recipient.
- **Xoay**: Secrets Manager xoay mật khẩu RDS 30 ngày; ứng dụng chịu được hai mật khẩu hợp lệ trong lúc chuyển (chiến lược alternating
  users). Về sau cân nhắc Vault dynamic secret cho DB nếu cần mỗi pod một user.
- **Audit và phát hiện**: CloudTrail cho mọi `GetSecretValue`, alert khi truy cập ngoài role mong đợi; secret scanning và push protection
  trên mọi repo; pre-commit hook.
- **Quyền trong cluster**: Role của team không có `get secrets` ngoài namespace của mình; etcd encryption at rest bằng KMS (EKS bật sẵn
  envelope encryption).
