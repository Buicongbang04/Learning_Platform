# Lời giải: mình được làm gì trong cluster của khách

Lời giải ở `can_i.sh` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/basic/01-can-i -q
```

Đo 2026-11-11 trên máy của repo: ~30 s (boot VM ~15 s, mỗi lần chạy script 2–4 s cho ~20 lời gọi `kubectl`).

## Cách làm

1. **Hỏi API server trước tiên**: `kubectl auth whoami -o jsonpath='{.status.userInfo.username}'` (SelfSubjectReview,
   mọi danh tính đã xác thực đều được gọi). Lỗi ở đây ⇒ không kết nối được hoặc token sai ⇒ thoát `2`, không in gì ra
   stdout. Đây cũng là câu trả lời cho câu hỏi đầu tiên ở khách: "kubeconfig này là ai?".
2. **Namespace** đọc offline từ context: `kubectl config view --minify -o jsonpath='{..namespace}'`, rỗng ⇒ `default`
   (đúng như kubectl tự làm).
3. **Mỗi dòng** chạy `kubectl auth can-i <đối số>` và đọc **stdout**: `yes`/`no` là câu trả lời; bất kỳ thứ gì khác
   (rỗng, lỗi) ⇒ dừng với mã `2`. Không dựa vào mã thoát: `no` và "connection refused" đều thoát `1`:

   ```text
   $ kubectl auth can-i get nodes; echo rc=$?
   Warning: resource 'nodes' is not namespace scoped
   no
   rc=1
   $ kubectl --server=https://127.0.0.1:6999 auth can-i get pods; echo rc=$?
   The connection to the server 127.0.0.1:6999 was refused - did you specify the right host or port?
   rc=1
   ```

4. Ghép JSON trong biến, in **một lần** ở cuối. Lỗi giữa chừng không để lại nửa object.

Đối số được truyền nguyên (không quote) để shell tách theo khoảng trắng; khoá trong `checks` là các từ nối bằng một dấu
cách (`tr -s`), nên dòng có nhiều dấu cách vẫn ra đúng khoá.

## Kết quả trên `lawfirm-prod` và cách đọc

Với kubeconfig của `fde`, mọi dòng `need` của `checks.txt` là `true`, `can_install: true`. Ba dòng `info` đáng đọc kỹ:

- `delete networkpolicies.networking.k8s.io/default-deny` = **true**: RBAC không phân quyền theo tên kiểu "mọi thứ trừ
  object này", nên Role cho `delete networkpolicies` là cho cả `default-deny`. IT chặn bằng ValidatingAdmissionPolicy;
  `can-i` chỉ hỏi RBAC (SelfSubjectAccessReview), không chạy admission. Báo cáo quyền phải ghi rõ "RBAC cho phép, chưa
  chắc admission cho phép"; muốn biết thật thì `kubectl delete --dry-run=server` (admission chạy cả với dry-run).
- `get nodes`, `list namespaces`, `list storageclasses` = false: không biết node có bao nhiêu CPU, StorageClass nào là
  mặc định. Đó là câu hỏi phải gửi IT, không đoán.
- `update resourcequotas` = false: quota là của IT; muốn thêm phải xin.

Lần 4 (IT bỏ `secrets` khỏi Role): `create secrets` và `list secrets` thành false ⇒ `can_install: false`. Đây là
trường hợp thật: Helm 3 lưu release trong Secret `sh.helm.release.v1.<tên>.v<n>` cùng namespace, nên "chỉ cho tạo
Deployment, không cho đụng Secret" làm `helm install` thất bại ngay ở bước ghi release, dù chart không có Secret nào.

## Sai lầm thường gặp

- Đọc `kubectl auth can-i --list` bằng mắt rồi kết luận: danh sách đó gộp theo resource, dễ bỏ sót subresource
  (`pods/exec`, `pods/portforward`) và không nói gì về admission.
- Kết luận "không có quyền" khi thực ra kubeconfig hết hạn hoặc VPN rơi: script coi mọi output khác `yes`/`no` là lỗi.
- Hỏi `can-i` với `-n` cứng `quillo`: khách đặt tên namespace khác là báo cáo sai.
