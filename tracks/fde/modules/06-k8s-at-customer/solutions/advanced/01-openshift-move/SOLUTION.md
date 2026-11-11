# Lời giải: khách chuyển sang OpenShift

## Hướng làm

Đi từng dòng values của `lawfirm-prod` và hỏi "trên OpenShift, ai quyết định giá trị này?". PSA restricted chỉ **kiểm**
pod của bạn; SCC `restricted-v2` vừa kiểm vừa **gán**: nó chọn UID trong dải của namespace, gán `fsGroup` và
supplemental group, ép `seccompProfile` và drop capability. Thứ bạn cố định (`runAsUser: 999`) trở thành thứ bị từ chối.
Sau đó đi theo đường của request (Route → Service → pod) và đường của image (registry → pull secret → node).

## Bài mẫu

### 1. Bảng khác biệt

| Khác biệt | Ảnh hưởng tới quillo | Cách xử lý |
| --- | --- | --- |
| SCC `restricted-v2` gán UID từ dải `openshift.io/sa.scc.uid-range` (vd. 1000660000/10000), từ chối `runAsUser` ngoài dải | `runAsUser: 999/10001/65534` của mọi thành phần bị từ chối (`unable to validate against any security context constraint`) | Bỏ mọi `runAsUser`, `runAsGroup`, `fsGroup` khỏi values; giữ `runAsNonRoot`, `allowPrivilegeEscalation: false`, `drop: [ALL]` (SCC cũng ép, khai rõ vẫn tốt cho cluster khác) |
| UID ngẫu nhiên nhưng GID chính luôn là `0` (root group) | Tiến trình phải ghi được thư mục nhờ quyền **nhóm 0**: pgvector ghi `PGDATA` và `/var/run/postgresql` (emptyDir, PVC: ổn vì `fsGroup` do SCC gán), quillo-api ghi `/tmp` (emptyDir: ổn); thư mục trong image thuộc `postgres:postgres` 0700 thì không | Kiểm từng image: mọi đường ghi phải là volume hoặc thư mục `chgrp 0 && chmod g=u` trong image. pgvector chính thức hỗ trợ UID tuỳ ý khi `PGDATA` nằm trên volume; nếu không thì vendor dựng biến thể image |
| `fsGroup` do SCC chọn (`MustRunAs` theo dải) | PVC của db và inbox được chown theo GID đó; giá trị `fsGroup: 999` trong values bị từ chối | Bỏ `fsGroup` khỏi values |
| Không có Ingress controller cho người dùng; Route + TLS edge của tập đoàn | api chỉ có Service ClusterIP; NetworkPolicy của api phải cho router (namespace `openshift-ingress`) vào | Tạo `Route` (edge, `insecureEdgeTerminationPolicy: Redirect`) tới `quillo-api:8080` ngoài chart hoặc qua values mở rộng; `networkPolicy.apiFrom` = namespaceSelector `network.openshift.io/policy-group: ingress` |
| Image từ internal registry hoặc registry tập đoàn có TLS + pull secret | `image.registry` đổi; pod cần `imagePullSecrets`; registry dùng CA tập đoàn (node đã trust, máy đẩy image thì chưa) | `image.registry: <registry tập đoàn>/quillo`, `image.pullSecrets: [{name: quillo-pull}]`; đẩy bằng `oc image mirror`/`skopeo copy` từ máy có CA |
| Egress ra ngoài cluster do `EgressFirewall` (OVN-Kubernetes) | quillo không cần egress ra ngoài trừ IdP khi bật SSO | Xin rule `EgressFirewall` cho IdP (host:port) nếu bật OIDC; NetworkPolicy giữ như `lawfirm-prod` (api→db/llm/embed, worker→db/embed, DNS tới `openshift-dns`, cổng 5353) |
| DNS cluster ở `openshift-dns`, pod nghe cổng 5353 | NetworkPolicy egress DNS theo nhãn `k8s-app: kube-dns` của chart không khớp | Egress DNS tới namespace `openshift-dns`, cổng 5353 UDP/TCP (và 53 cho chắc) |
| Quota/LimitRange do platform đặt, có thể có `LimitRange` default | Không còn bị từ chối vì thiếu resources, nhưng default có thể quá nhỏ cho llm (OOM-kill) | Giữ resources tường minh như `lawfirm-prod` |

### 2. Values cho OpenShift (phần khác `lawfirm-prod`)

```yaml
image:
  registry: registry.tapdoan.example/quillo          # registry tập đoàn, TLS
  pullSecrets: [{name: quillo-pull}]                  # Secret dockerconfigjson tạo từ tệp, không để trong values
podSecurityContext:
  runAsNonRoot: true                                  # bỏ seccompProfile cũng được: restricted-v2 tự gán RuntimeDefault
api:    {podSecurityContext: {}}                      # bỏ runAsUser/runAsGroup/fsGroup: SCC gán UID/GID theo namespace
worker: {podSecurityContext: {}}
db:     {podSecurityContext: {}}
llm:    {podSecurityContext: {}}
embed:  {podSecurityContext: {}}
networkPolicy:
  enabled: true
  apiFrom:
    - namespaceSelector:
        matchLabels: {network.openshift.io/policy-group: ingress}   # chỉ router của OpenShift gọi api
```

Kèm (ngoài chart) một `Route` edge TLS tới service `quillo-api`, và một NetworkPolicy bổ sung cho egress DNS tới
`openshift-dns` cổng 5353.

### 3. Thứ tự cài và kiểm

1. `oc whoami`, `oc auth can-i --list -n quillo`; `oc get ns quillo -o yaml` đọc `sa.scc.uid-range`, quota, LimitRange.
2. Đẩy image, `oc run` một pod thử từ mỗi image với SCC mặc định (`oc debug` hoặc pod `sleep`), ghi thử vào đường dẫn
   ứng dụng cần ghi. **Dừng** nếu một image không chạy được với UID ngẫu nhiên: cần image vendor sửa, không xin SCC.
3. `helm template … | oc apply --dry-run=server -f -`; `oc get pod -o yaml | grep openshift.io/scc` sau khi cài để
   chắc pod chạy dưới `restricted-v2`.
4. `helm upgrade --install --wait`; `oc get pods`, `oc logs` db (initdb với UID ngẫu nhiên).
5. Tạo Route; `curl -sk https://<host>/healthz` từ mạng người dùng; kiểm NetworkPolicy bằng pod thử như ở k3s.
6. Backup thử bằng `ops/backup.sh --kubectl` (`oc` tương thích `kubectl`).

### 4. Câu hỏi và yêu cầu gửi platform team

- Registry nào, pull secret ai tạo, CA của registry cho máy đẩy image; có quét image (policy chặn image có CVE) không.
- StorageClass mặc định, RWO đủ cho db và inbox, có snapshot không (backup).
- Hostname và chứng chỉ cho Route; người dùng tới router từ mạng nào.
- Quota/LimitRange của project (để kiểm trước như bài basic 02).
- EgressFirewall cho IdP nếu bật SSO; cổng DNS trong NetworkPolicy theo bản OpenShift của họ.
- Xác nhận **không** cần SCC khác ngoài `restricted-v2`; nếu buổi thử bước 2 cho thấy cần, sẽ gửi yêu cầu riêng có lý do.

## Rubric (10 điểm, đạt từ 7)

| Tiêu chí | Điểm |
| --- | --- |
| Nêu đúng: `runAsUser`/`fsGroup` cố định bị `restricted-v2` từ chối; xử lý bằng bỏ giá trị cố định, không xin `anyuid` | 2 |
| Nêu UID ngẫu nhiên + GID 0 ⇒ đường ghi phải là volume hoặc thư mục ghi được bởi nhóm 0; chỉ ra thành phần nào ghi ở đâu | 2 |
| Đường vào: Route + TLS edge, NetworkPolicy cho router vào api | 1 |
| Image: registry/pull secret/CA, cách đẩy image | 1 |
| NetworkPolicy/DNS/EgressFirewall đúng với OpenShift | 1 |
| Values cụ thể, mỗi thay đổi có lý do | 1 |
| Thứ tự cài có bước thử image với SCC mặc định **trước** khi cài cả chart, có điểm dừng | 1 |
| Câu hỏi gửi platform team cụ thể, trả lời được bằng có/không hoặc một giá trị | 1 |

Trừ điểm: xin `anyuid`/`privileged` "cho chắc" (−2), hay cho rằng PSA restricted và `restricted-v2` giống nhau nên values
giữ nguyên (−2).
