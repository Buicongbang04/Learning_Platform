# Lời giải: Báo cáo survey máy khách

Lời giải đầy đủ ở `site_survey.sh` cạnh tệp này. Chạy:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/01-site-survey/exercises/basic/01-survey-report -q
```

## Từng trường và vì sao chọn nguồn đó

| Khoá | Nguồn | Vì sao không dùng nguồn khác |
| --- | --- | --- |
| `os_id`, `os_version` | `. /etc/os-release` trong `$( )` | `lsb_release` không có trên Rocky cloud image; `/etc/issue` hay bị IT sửa thành banner |
| `kernel_major` | `uname -r \| cut -d. -f1-2` | `uname -r` của Rocky là `4.18.0-553.el8_10.x86_64`: hai thành phần đầu mới ổn định |
| `glibc` | `getconf GNU_LIBC_VERSION`, dự phòng `ldd --version` | Dòng đầu của `ldd --version` khác nhau giữa Ubuntu (`ldd (Ubuntu GLIBC 2.31-0ubuntu9.18) 2.31`) và Rocky (`ldd (GNU libc) 2.28`); `getconf` in gọn `glibc 2.31` |
| `cpus` | `nproc` | `nproc` tôn trọng cgroup/affinity; đếm `processor` trong `/proc/cpuinfo` ra số CPU của host khi chạy trong container |
| `mem_mb` | `MemTotal` trong `/proc/meminfo` | `free -m` đổi định dạng giữa các bản procps |
| `disk_free_gb_max` | Cột 4 của `df -P -k /` | `-P` khoá định dạng một dòng (tên device dài không bị xuống dòng); cột Available đã trừ phần dự trữ cho root, đúng với cái user cài sản phẩm thấy |
| `gpu` | `nvidia-smi --query-gpu=name`, dự phòng `/dev/nvidia0` | `lspci` không có trên Rocky cloud image |
| `proxy_url` | `https_proxy`/`HTTPS_PROXY` rồi `/etc/environment` | Phiên SSH có `pam_env` nạp `/etc/environment`, nhưng script chạy từ cron hay `env -i` thì không; đọc cả tệp cho chắc |
| `sudo` | `sudo -n true` | `id -nG` có nhóm `sudo`/`wheel` không đủ: `lab-open` cho `fde` sudo qua `/etc/sudoers.d`, không qua nhóm |
| `selinux` | `getenforce`, dự phòng `/sys/fs/selinux/enforce` | Ubuntu không có `getenforce` ⇒ `n/a` |
| `runtime` | `command -v docker`, rồi `podman` | Có `docker` mà `docker --version` nhắc tới podman (gói `podman-docker`) thì vẫn là `podman` |
| `egress` | `curl --noproxy '*' --max-time 5`, rồi qua proxy bằng URL `http://` | Proxy TLS inspection làm HTTPS lỗi cert dù có đường; phép thử qua proxy dùng `http://` |

## Output đo trên các hồ sơ (2026-11-04, RAM mặc định 2048 MB)

| Hồ sơ | Điểm đáng chú ý |
| --- | --- |
| `lab-open` | `mem_mb` 1963, `disk_free_gb_max` 17.5, `egress` `open` |
| `hospital` | `disk_free_gb_max` 6.0, `proxy_url` `http://10.0.2.100:3128`, `egress` `proxy` |
| `bank` | `mem_mb` 1778 (crashkernel giữ một phần RAM), `sudo` false, `selinux` `enforcing`, `runtime` `podman`, `egress` `none` |
| `lawfirm-staging` | `disk_free_gb_max` 27.2, `egress` `none` |

`mem_mb` luôn thấp hơn RAM cấp cho VM: kernel và firmware giữ một phần, và Rocky 8 với `crashkernel=auto` giữ nhiều hơn.
Đây là lý do preflight (bài 02) không thể so `MemTotal` với "4 GB" một cách máy móc.

## Lỗi hay gặp

- In con số `df -h` (`6.1G`): định dạng cho người đọc, đơn vị lẫn lộn, không parse được ổn định.
- Quên `LC_ALL=C`: `printf "%.1f"` trong `awk` theo locale có thể in dấu phẩy.
- Chỉ đọc biến `https_proxy` của phiên: đúng khi chạy qua SSH, sai khi khách chạy qua cron hay công cụ quản trị.
- Dùng `ip route get 1.1.1.1` để kết luận "có mạng": route mặc định vẫn có trên máy air-gapped; chỉ phép thử kết nối
  thật (có timeout) mới trả lời được.
- Hỏi `sudo -n true` là có giá: trên máy ngân hàng, lần thử thất bại có thể sinh một dòng log bảo mật. Ghi rõ trong thư
  gửi IT rằng script thử `sudo -n` đúng một lần (xem Advanced 02).
