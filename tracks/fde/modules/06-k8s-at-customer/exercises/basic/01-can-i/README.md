---
title: "Mình được làm gì trong cluster của khách"
level: basic
services: []
files:
  - path: starter/can_i.sh
    note: Script hỏi quyền, bạn viết (POSIX sh)
  - path: checks.txt
    note: Danh sách quyền cần kiểm cho bản cài quillo (không sửa)
  - path: tests/test_can_i.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lawfirm-prod
  - uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/basic/01-can-i -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Ngày đầu ở khách có Kubernetes, việc đầu tiên không phải `helm install` mà là trả lời: **bằng kubeconfig IT vừa đưa,
mình được làm gì, ở namespace nào, còn thiếu quyền gì để cài**. Câu trả lời đó đi vào email gửi platform team trước buổi
triển khai, nên nó phải đúng với cluster thật chứ không phải với tài liệu RBAC IT gửi. Bạn viết một script nhỏ chạy
được trên máy khách chỉ với `kubectl`, phân biệt rõ "không có quyền" với "không hỏi được".

## Đề bài

Máy `lawfirm-prod` của công ty luật: Ubuntu 22.04, k3s do IT quản, user `fde` không có sudo, chỉ có
`~/.kube/config` (token của một ServiceAccount, context trỏ sẵn một namespace). `kubectl` có trong `PATH`.

Viết `starter/can_i.sh` (POSIX sh, chỉ dùng `kubectl` và công cụ chuẩn của Ubuntu; không Python). Cách chạy:

```sh
sh can_i.sh <tệp kiểm tra>
```

Tệp kiểm tra có dạng như `checks.txt`: dòng trống và dòng bắt đầu bằng `#` bỏ qua; mỗi dòng còn lại là `need` hoặc
`info`, rồi đến **đúng các đối số** cho `kubectl auth can-i` (vd. `need create pods --subresource=portforward`). Giữa
các từ có thể có nhiều dấu cách. Script dùng kubeconfig hiện hành (biến `KUBECONFIG` nếu có, không thì
`~/.kube/config`).

Thành công thì in ra stdout **đúng một object JSON** rồi thoát `0`:

| Khoá | Giá trị |
| --- | --- |
| `user` | Username của danh tính đang dùng, như API server thấy (vd. `system:serviceaccount:<ns>:<tên>`) |
| `namespace` | Namespace của context hiện hành; context không đặt namespace thì `"default"` |
| `checks` | Object: khoá là phần đối số của mỗi dòng (sau `need`/`info`, các từ nối bằng **một** dấu cách), giá trị `true`/`false` theo `kubectl auth can-i` |
| `missing` | Mảng các khoá `need` có giá trị `false`, đúng thứ tự trong tệp |
| `can_install` | `true` khi `missing` rỗng |

Không hỏi được API server (sai địa chỉ, token hết hạn, mạng đứt…) thì **không** được in báo cáo: stdout rỗng, thoát mã
khác `0`, lý do ghi ra stderr. Một báo cáo toàn `false` vì không kết nối được là báo cáo sai.

Test boot `lawfirm-prod` (cho test có sudo để đóng vai IT), chép script vào `/home/fde/can-i/` và chạy bốn lần, mỗi lần
một tệp kiểm tra khác (chọn ngẫu nhiên, đảo thứ tự các dòng của `checks.txt`):

1. Kubeconfig của `fde` như IT giao.
2. Bản sao kubeconfig có context trỏ namespace `default` (qua `KUBECONFIG`).
3. Bản sao kubeconfig trỏ một cổng API server không tồn tại.
4. Sau khi IT (test, bằng sudo) sửa Role của `fde` và thêm một ClusterRoleBinding.

Đo trên máy của repo: cả bài ~30 s.

## Tiêu chí đạt

`test_can_i_on_lawfirm_prod`:

- Lần 1, 2, 4: thoát `0` trong 90 s; stdout là một object JSON; `user`, `namespace` đúng; `checks` có đúng một khoá cho
  mỗi dòng của tệp kiểm tra và mọi giá trị trùng với `kubectl auth can-i` chạy cùng lúc trong VM; `missing` và
  `can_install` đúng theo định nghĩa trên.
- Lần 3: thoát mã khác `0`, stdout rỗng.

## Gợi ý

### Gợi ý 1

`kubectl auth can-i` trả `yes`/`no` trên stdout, nhưng mã thoát của "no" và của "không kết nối được" là một. Bạn dựa
vào gì để phân biệt?

### Gợi ý 2

Username và namespace hiện hành đều hỏi được bằng `kubectl` mà không cần đọc tay tệp kubeconfig. Một trong hai câu hỏi
đó cần API server, câu kia thì không: thứ tự bạn hỏi quyết định script phát hiện lỗi kết nối sớm hay muộn.

### Gợi ý 3

Gom kết quả vào biến rồi mới in ở cuối; in dần từng dòng thì lỗi giữa chừng để lại nửa object JSON trên stdout.
