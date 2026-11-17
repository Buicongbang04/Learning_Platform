---
title: "k3s air-gapped trên máy staging của công ty luật"
level: intermediate
services: []
files:
  - path: starter/install_k3s.sh
    note: Script cài k3s IT đã thử; bạn sửa
  - path: hello.yaml
    note: Manifest ứng dụng thử của team app khách (không sửa)
  - path: tests/test_k3s_airgap.py
    note: Không sửa (cũng là nơi dựng image hello từ BusyBox đã ghim)
run:
  - nice -n 15 uv run python -m fdekit prepare lawfirm-staging
  - uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/intermediate/02-k3s-airgap -q -s
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Khách chưa có Kubernetes nhưng muốn sản phẩm chạy "kiểu cluster" để sau này lên production cùng cách. Bạn dựng một k3s
một node trên máy **không ra internet**, từ đúng các tệp đã mang vào, sao cho ứng dụng của khách chạy từ registry nội bộ
và dùng được như một cluster bình thường. Script phải chạy lại được trên máy đã cài.

## Đề bài

Máy `lawfirm-staging`: Ubuntu 22.04, `fde` có sudo (`sudo -n`), không ra internet, không DNS ra ngoài, Docker của team
khác đang cài sẵn (không gỡ). Theo phiếu khảo sát mạng: subnet `10.0.2.0/24`, gateway `10.0.2.2`, firewall chặn mọi kết
nối ra ngoài. Registry nội bộ `10.0.2.101:5000` (HTTP, không đăng nhập) đã có image `lawfirm/hello:1.0` của team app.

Bạn đã chép vào `/home/fde/k3s-airgap/` ba tệp của bản `v1.37.1+k3s1` (sha256 ở phần `0. Cài đặt` của README module):
`k3s`, `k3s-airgap-images-amd64.tar.zst`, `install.sh`.

IT đã thử theo quickstart (chính là `starter/install_k3s.sh`) và báo:

> Service k3s chạy, `kubectl get nodes` ra `Ready`, nhưng các pod trong `kube-system` đứng mãi ở `ContainerCreating`.

Sửa `starter/install_k3s.sh` (POSIX sh, chạy dưới `fde`, dùng `sudo -n` khi cần). Test boot `lawfirm-staging`, đẩy
lên registry nội bộ image `lawfirm/hello:1.0` mới dựng (BusyBox, httpd cổng 8080 trả một dòng ngẫu nhiên của lần chạy),
chép ba tệp k3s vào `/home/fde/k3s-airgap/`, chép script của bạn vào `/home/fde/install_k3s.sh` và `hello.yaml` vào
`/home/fde/hello.yaml`, rồi:

1. Chạy `cd /home/fde && sh /home/fde/install_k3s.sh` (≤150 s), chờ cluster, `sudo k3s kubectl apply -f hello.yaml`.
2. Chạy lại đúng lệnh cài lần nữa, kiểm lại.

Đo trên máy của repo với lời giải tham chiếu: ~60 s. Tự boot máy để điều tra:
`with fdekit.customer_site("lawfirm-staging") as s:`; đẩy image thử bằng hàm `push_hello` trong tệp test.

## Tiêu chí đạt

`test_k3s_airgap_on_lawfirm_staging`, sau **mỗi** lần cài:

- `install_k3s.sh` thoát `0` trong 150 s.
- Trong 120 s: mọi node `Ready`; Deployment `coredns`, `local-path-provisioner`, `metrics-server` ở `kube-system` có pod
  available. `k3s --version` là `v1.37.1+k3s1`.
- Trong 90 s: Deployment `hello` (namespace `default`) rollout xong, pod chạy đúng image
  `10.0.2.101:5000/lawfirm/hello:1.0`.
- Từ chính máy (shell của `fde`, không qua pod), `curl http://<ClusterIP của service hello>/` trả đúng dòng của lần chạy
  (thử lại trong 30 s).
- Một pod BusyBox trong cluster gọi `http://hello.default.svc.cluster.local/` nhận đúng dòng đó.

## Gợi ý

### Gợi ý 1

`kubectl describe pod` và `journalctl -u k3s` cho biết container đang chờ gì. Đọc nguyên văn dòng lỗi, đừng dừng ở trạng
thái.

### Gợi ý 2

Sửa xong một lớp thì đi tiếp tới tiêu chí kế; không phải lỗi nào cũng in ra ở cùng một chỗ, có lỗi chỉ lộ khi bạn thử
truy cập theo một đường cụ thể.

### Gợi ý 3

Quickstart được viết cho một máy có internet. Liệt kê những thứ nó ngầm giả định có sẵn trên máy đó, rồi kiểm từng thứ
trên máy này.
