---
title: Backup etcd của cluster kubeadm, có kiểm và giữ bản
level: intermediate
services: []
files:
  - path: starter/etcd-backup.sh
    note: Script backup chạy trên control plane
  - path: tests/fixtures/bin/etcdctl
    note: etcdctl giả, ghi lại argv
  - path: tests/fixtures/bin/etcdutl
    note: etcdutl giả
  - path: tests/test_etcd_backup.py
    note: Không sửa
run:
  - uv run pytest tracks/devops/modules/10-kubernetes-core/exercises/intermediate/02-etcd-backup -q -rs
---

## Mục tiêu

Viết script backup etcd đủ dùng ở production cho một cluster kubeadm: đúng endpoint và chứng chỉ, tệp có thời điểm UTC và quyền
chặt, kiểm snapshot trước khi tin nó, giữ đúng số bản, lỗi thì dừng mà không để lại tệp trông như hợp lệ. Rồi tự tay restore
etcd của `devops-lab` theo lab ở mục 6 của module.

## Đề bài

Viết `starter/etcd-backup.sh`, chạy bằng root trên control plane (qua systemd timer hay cron):

| Yêu cầu | Chi tiết |
| --- | --- |
| Biến | `ETCD_BACKUP_DIR` (mặc định `/var/backups/etcd`), `ETCD_BACKUP_KEEP` (mặc định 7), `ETCD_PKI` (mặc định `/etc/kubernetes/pki/etcd`) |
| Snapshot | `etcdctl snapshot save` qua endpoint, CA, cặp chứng chỉ client đúng như `/etc/kubernetes/manifests/etcd.yaml` của kubeadm (cờ `--endpoints`, `--cacert`, `--cert`, `--key` hay biến `ETCDCTL_*` tương ứng) |
| Tên tệp | `$ETCD_BACKUP_DIR/etcd-snapshot-<YYYYmmddTHHMMSSZ theo UTC>.db`, quyền `0600` (snapshot chứa mọi Secret) |
| Kiểm | `etcdutl snapshot status <tệp> -w json`; lỗi hay `totalKey` bằng 0 thì xoá tệp, trả mã khác 0 |
| Giữ bản | Sau khi lần này thành công: giữ `ETCD_BACKUP_KEEP` tệp `etcd-snapshot-*.db` mới nhất, xoá bản cũ hơn, không đụng tệp khác trong thư mục |
| Lỗi | `etcdctl` lỗi thì trả mã khác 0, không xoá bản cũ, không để lại `etcd-snapshot-*.db` hay `.part` |
| Output | Dòng cuối stdout là đường dẫn snapshot |

**Cách test chấm.** Script của bạn **không bao giờ** chạy trong node của cluster: nó chạy trong sandbox trên máy, với `etcdctl` và
`etcdutl` giả ở `tests/fixtures/bin/` (đặt đầu `PATH`) ghi lại argv, biến `ETCDCTL_*` và hành vi theo biến điều khiển.

| Test | Kiểm |
| --- | --- |
| Cờ | argv của `snapshot save`: endpoint `https://127.0.0.1:2379`, CA `/etc/kubernetes/pki/etcd/ca.crt`, cặp `server.crt`/`server.key` hay `healthcheck-client.crt`/`.key` trong `pki/etcd` |
| Tệp | Đúng một tệp tên đúng mẫu, quyền `0600`, dòng cuối stdout là đường dẫn, `etcdutl snapshot status` gọi đúng tệp, không còn `.part` |
| Giữ bản | 8 bản cũ cộng `README.txt`, `ETCD_BACKUP_KEEP=3`: còn 3 bản mới nhất, `README.txt` còn |
| Lỗi etcdctl | etcdctl giả trả 1: script mã khác 0, 4 bản cũ còn nguyên (dù `KEEP=2`), không `.part` |
| Snapshot hỏng | etcdutl giả lỗi, hay `totalKey: 0`: script mã khác 0, không còn snapshot nào |
| Cluster thật | Cần `devops-lab`: test đọc `/etc/kubernetes/manifests/etcd.yaml` của control plane (`kind_node_cp`) và kiểm các đường dẫn ở trên khớp nó; rồi **chính test** (không phải script của bạn) chạy một lệnh cố định `crictl exec ... etcdctl ... snapshot save` trong node, chép snapshot về, kiểm tệp là bbolt và có ConfigMap vừa tạo trong namespace của lab |

Dưới 20 giây.

## Tiêu chí đạt

- Mọi test pass.
- Làm lab restore ở mục 6 của module: xoá một ConfigMap, restore từ snapshot, ConfigMap trở lại. Chấm theo rubric trong
  `SOLUTION.md` (tự chấm hay nhờ người review).
- Trả lời được: snapshot của một control plane trong cluster ba control plane dùng được để restore cả cluster không, và cần làm gì
  với hai member còn lại.

## Gợi ý

### Gợi ý 1

Đọc cờ của chính etcd trên node: `docker exec devops-lab-control-plane grep -E 'client-urls|cert-file|key-file|trusted-ca'
/etc/kubernetes/manifests/etcd.yaml`. Client cần CA mà etcd tin (`--trusted-ca-file`) và một chứng chỉ do CA đó ký.

### Gợi ý 2

`set -euo pipefail` cộng `trap ... ERR` để dọn tệp dở dang. etcdctl ghi `<tệp>.part` rồi mới đổi tên; lỗi giữa chừng có thể để lại
`.part`. Chạy dọn bản cũ **sau** khi bản mới đã qua kiểm, không phải trước.
