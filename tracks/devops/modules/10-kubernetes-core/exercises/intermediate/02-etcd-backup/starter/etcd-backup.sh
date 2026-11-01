#!/usr/bin/env bash
set -euo pipefail

# Chạy trên control plane của cluster kubeadm, bằng root, qua systemd timer hay cron.
# Biến: ETCD_BACKUP_DIR (mặc định /var/backups/etcd), ETCD_BACKUP_KEEP (mặc định 7), ETCD_PKI (mặc định /etc/kubernetes/pki/etcd).
# TODO 1: snapshot bằng etcdctl qua endpoint, CA, chứng chỉ client đúng như trong /etc/kubernetes/manifests/etcd.yaml
# TODO 2: tên tệp etcd-snapshot-<UTC YYYYmmddTHHMMSSZ>.db trong ETCD_BACKUP_DIR, quyền 0600
# TODO 3: kiểm bằng etcdutl snapshot status; lỗi hay 0 key thì xoá tệp và trả mã khác 0
# TODO 4: giữ ETCD_BACKUP_KEEP bản mới nhất, không đụng tệp khác trong thư mục
# TODO 5: in đường dẫn snapshot ở dòng cuối stdout
echo "etcd-backup.sh chưa viết" >&2
exit 1
