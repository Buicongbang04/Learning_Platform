# Lời giải: Postgres bền trên volume local, backup và restore

Lời giải: `k8s/postgres.yaml`, `k8s/backup.yaml`, `restore/pg-restore.yaml`.

## Binding

`volumeClaimTemplates` tên `data`, `storageClassName: olist-local`, 1Gi, ReadWriteOnce, nên StatefulSet tạo PVC `data-postgres-0`.
PV của admin có cùng class, đủ dung lượng, đúng access mode và `claimRef` trỏ đúng PVC đó, nên PV controller bind hai bên. PV `local`
có `nodeAffinity` tới `devops-lab-worker`; scheduler biết volume đã bind nằm ở đâu và đặt pod lên đúng node. Xin `standard` thay vì
`olist-local` thì local-path provisioner tạo một PV động mới, PV của admin bỏ không, và test thấy `volumeName` khác.

`persistentVolumeClaimRetentionPolicy: Retain` (mặc định) giữ PVC khi xoá hay scale StatefulSet xuống; `Delete` tiện cho môi
trường tạm nhưng nguy hiểm với dữ liệu thật.

## Backup và restore

- `pg_dump -Fc` ra `<tên>.part` rồi `mv`: bản dở dang không bao giờ mang tên của bản tốt; restore chọn bản mới nhất theo tên (UTC,
  sort được). Giữ 7 bản bằng `ls | sort -r | tail -n +8 | xargs rm`.
- `concurrencyPolicy: Forbid`: lần trước chưa xong thì bỏ lần này, không có hai `pg_dump` ghi cùng thư mục. `startingDeadlineSeconds:
  600`: controller lỡ lịch (control plane gián đoạn) thì chỉ chạy bù trong 10 phút; không đặt thì sau hơn 100 lần lỡ CronJob ngừng
  lên lịch. `timeZone: Asia/Ho_Chi_Minh` để 02:15 là giờ Việt Nam, không phải giờ của controller-manager.
- Restore là một Job riêng, không apply cùng `k8s/`: restore là quyết định của người trực, không phải trạng thái mong muốn.
  `pg_restore --clean --if-exists --no-owner --exit-on-error`, `backoffLimit: 0` (restore lỗi giữa chừng thì người xem log, không
  để controller chạy lại tự động).

## Rubric câu hỏi ở Tiêu chí đạt (10 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| Worker chết hẳn: pod `postgres-0` kẹt `Pending` vì PV local gắn với node đó; RTO bằng thời gian sửa node, hay restore từ dump sang PV mới (dump cũ nhất 24 giờ, RPO 24 giờ) | 3 |
| `Retain`: xoá namespace thì PVC mất, PV chuyển `Released`, dữ liệu còn trên đĩa, admin phải xoá `claimRef` hay tạo PV mới trỏ cùng thư mục để dùng lại; `Delete`: provisioner xoá luôn dữ liệu | 3 |
| Dump cùng cluster bảo vệ trước lỗi logic (xoá nhầm bảng, migration hỏng), không bảo vệ trước mất node có PVC `pg-backups`, mất cluster hay xoá namespace; cần đẩy bản dump ra ngoài (object storage khác tài khoản) | 2 |
| Nêu hướng production: replica streaming (CloudNativePG, Patroni) hay dịch vụ managed, WAL archiving cho PITR, diễn tập restore định kỳ | 2 |
