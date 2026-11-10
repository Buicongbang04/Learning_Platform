# Lời giải: backup etcd và lab restore

Lời giải: `etcd-backup.sh`.

## Script

- `etcdctl --endpoints=https://127.0.0.1:2379 --cacert=$ETCD_PKI/ca.crt --cert=$ETCD_PKI/server.crt --key=$ETCD_PKI/server.key
  snapshot save <tệp>`. Ba đường dẫn khớp `--trusted-ca-file`, `--cert-file`, `--key-file` trong
  `/etc/kubernetes/manifests/etcd.yaml`. `healthcheck-client.crt` cũng dùng được (cũng do CA của etcd ký). `apiserver-etcd-client.crt`
  nằm ở `/etc/kubernetes/pki/`, không phải `pki/etcd/`; dùng được nhưng không phải lựa chọn của kubeadm docs. CA của cluster
  (`/etc/kubernetes/pki/ca.crt`) thì **không**: etcd có CA riêng.
- `umask 077` và `chmod 600`: snapshot chứa mọi Secret của cluster. Đã kiểm trên `devops-lab`: `grep -a` thấy nguyên giá trị một
  Secret vừa tạo trong tệp snapshot. Ở production mã hoá tệp trước khi đẩy đi (age, KMS) và bật encryption at rest cho Secret.
- `trap cleanup ERR` xoá tệp và `.part` khi bất kỳ lệnh nào lỗi dưới `set -e`.
- Kiểm bằng `etcdutl snapshot status -w json`: etcd 3.6 bỏ `etcdctl snapshot status`. Snapshot 0 key là dấu hiệu snapshot từ một
  member chưa có dữ liệu (endpoint trỏ nhầm).
- Dọn bản cũ chỉ sau khi bản mới qua kiểm: lần backup lỗi không bao giờ làm giảm số bản tốt.

## Vì sao test không chạy script trong node

Node kind là container privileged; lệnh chạy trong node bằng root chạm được máy host. Vì vậy testkit chỉ chạy **một argv cố định**
viết sẵn trong test (`crictl exec -q --name ^etcd$ --state running etcdctl ... snapshot save /var/lib/etcd/devops-ex-snapshot.db`),
không bao giờ chạy nội dung bạn viết trong node. Script của bạn chạy trong sandbox với `etcdctl` giả; test cluster thật chứng minh
các đường dẫn bạn dùng chính là đường dẫn của etcd thật. Trên kind, etcdctl chỉ có trong container etcd (image không có `etcdutl`
hay shell) và `/var/lib/etcd` là mount ghi được duy nhất chung giữa container đó và node, nên snapshot của test ghi tạm vào đó rồi
xoá.

## Rubric lab restore (10 điểm)

Theo đúng lab ở mục 6 của module: restore ra thư mục mới trên máy, dừng static pod, đổi data dir **tại chỗ**, bật lại, kiểm.

| Tiêu chí | Điểm |
| --- | --- |
| Tạo snapshot đúng cờ, chép ra máy, quyền `0600`, kiểm bằng `etcdutl snapshot status` (có revision, số key) | 2 |
| Chứng minh snapshot chứa Secret ở dạng đọc được và nêu hai biện pháp bảo vệ | 1 |
| `etcdutl snapshot restore` ra **thư mục mới** với `--name`, `--initial-cluster`, `--initial-advertise-peer-urls` đọc từ `etcd.yaml`; giải thích vì sao cluster nhiều member bắt buộc ba cờ đó | 2 |
| Dừng etcd và kube-apiserver bằng cách chuyển manifest ra khỏi `/etc/kubernetes/manifests`, **chờ** container dừng hẳn, giữ data dir cũ ở `/var/lib/etcd-truoc-restore`, đặt bản restore vào `/var/lib/etcd`, trả manifest về, chờ `/readyz` | 2 |
| ConfigMap đã xoá trở lại; nêu được thứ gì tạo sau snapshot đã mất trên cả cluster dùng chung, và vì sao không được chạy test song song | 1 |
| Nói được đường lui khi chuỗi lệnh dừng giữa chừng (khối quay về `/var/lib/etcd-truoc-restore`, phương án cuối là tạo lại cluster) và các bước khác trên kubeadm nhiều member: restore **cùng** snapshot trên mọi member, mỗi member `--name` của nó | 2 |

Tài liệu kubeadm còn mô tả cách restore ra thư mục mới rồi sửa `hostPath` của volume `etcd-data` trong manifest. Cách đó đúng trên
kubeadm thật nhưng không dùng trên `devops-lab`: test thật của bài này kiểm data dir là `/var/lib/etcd` (snapshot của test ghi vào đó)
và fail kèm lời nhắc nếu manifest trỏ chỗ khác. Không cộng điểm cho cách đó trong rubric này.

## Câu hỏi ở Tiêu chí đạt

Snapshot từ một member của cluster ba member restore được cả cluster: restore **cùng** tệp đó trên cả ba node, mỗi node với `--name`
của nó và cùng `--initial-cluster`, tạo một cluster etcd mới (cluster ID mới) với cùng dữ liệu. Không restore một member rồi cho
join vào hai member cũ: dữ liệu và cluster ID không khớp.
