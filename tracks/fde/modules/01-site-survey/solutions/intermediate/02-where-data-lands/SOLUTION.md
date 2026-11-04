# Lời giải: Image sẽ nằm ở đâu

Lời giải ở `storage_report.sh` cạnh tệp này. Chạy:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/01-site-survey/exercises/intermediate/02-where-data-lands -q
```

## Cách làm

1. Hỏi runtime chứ không đoán: `docker info --format '{{.DockerRootDir}}'` (chỉ chạy được khi daemon trả lời user này),
   rồi `podman info --format '{{.Store.GraphRoot}}'`.
2. Thư mục có thể chưa tồn tại (Podman chưa chạy lần nào): đi ngược lên thư mục cha gần nhất có thật.
3. `df -P -k <dir>` ⇒ cột 4 (Available) và cột 6 (mount); `df -P -i <dir>` ⇒ `IFree / Inodes`. Filesystem báo
   `Inodes` = 0 (btrfs, một số FS mạng) thì in `null` thay vì chia cho 0.

## Bẫy trong bài

| Bẫy | Ai hay mắc | Thực tế |
| --- | --- | --- |
| Đo `df /` | Gần như ai cũng làm lần đầu | Sau khi IT chuyển `data-root` sang `/srv/appdata`, `/` vẫn còn 17 GB nhưng Docker chỉ còn ~1,8 GB |
| Đặt cứng `/var/lib/docker` | Người quen Ubuntu | `data-root` trong `/etc/docker/daemon.json` là cấu hình phổ biến nhất ở khách có volume dữ liệu riêng |
| Đọc `graphroot` trong `/etc/containers/storage.conf` | Người quen Podman chạy root | Đó là cấu hình của root (`/var/lib/containers/storage`); rootless dùng `~/.local/share/containers/storage` hoặc `~/.config/containers/storage.conf` |
| `du`/`ls` trong `data_root` | Muốn "xem cho chắc" | `/srv/appdata/docker` thuộc root, mode 710: `ls` bị từ chối, nhưng `df` trên chính thư mục vẫn chạy |
| Quên inode | Hầu hết | Image nhiều layer với hàng trăm nghìn tệp nhỏ (Python site-packages) có thể hết inode trước khi hết dung lượng, nhất là ext4 tạo với `-i` lớn |

## Output đo được

| Máy | `data_root` | `data_mount` | `data_free_gb` |
| --- | --- | --- | --- |
| `lab-open` mặc định | `/var/lib/docker` | `/` | 17.47 |
| `lab-open` sau khi chuyển | `/srv/appdata/docker` | `/srv/appdata` | ~1.78 (ext4 giữ 5% cho root) |
| `bank` mặc định | `/home/fde/.local/share/containers/storage` | `/` | 17.45 |
| `hospital` | `/var/lib/docker` | `/` | 6.02 |

## Dùng vào preflight thế nào

Trong preflight thật, check `disk` nên so `min_disk_free_gb` với `data_free_gb` này chứ không phải với `/`. Survey 13
trường giữ `disk_free_gb_max` đo ở `/` vì đó là thứ so được với hồ sơ; khi gửi khách, báo cáo khoảng cách ghi cả hai con
số nếu chúng khác nhau.
