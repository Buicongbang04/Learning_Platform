# Lời giải: ma trận hỗ trợ OS và runtime gửi khách

## Hướng làm

1. Định nghĩa mức trước, bảng sau: mỗi mức là một cam kết vận hành (ai sửa, trong bao lâu), không phải nhãn.
2. Lập bảng OS từ **bằng chứng**: output thật trên golden (glibc, Python, `SUPPORT_END`), kết quả các bài module 03–04,
   trang lifecycle chính thức. Thứ chưa đo ghi "chưa kiểm".
3. Runtime riêng một bảng, vì cùng OS có thể chạy Docker, Podman hay k3s, mỗi thứ một bộ giới hạn.
4. Môi trường bị khoá là một phần của ma trận, không phải chú thích: SELinux enforcing, không root, noexec, `nofile`.
5. Viết riêng phần "phải làm gì để lời hứa này đúng" cho product.

Chỗ hay sai: chép `REQUIREMENTS.yaml` thành ma trận (nó ghi Debian 11, mà Debian 11 đã hết LTS 31/08/2026); ghi "RHEL 8+"
không phân biệt Podman rootless trên cgroup v1; hứa SELinux "cần tắt"; đưa WSL2 vào "được hỗ trợ"; không có ngày hay nguồn.

## Rubric (tự chấm, đạt đủ 8 mục)

| # | Bài mẫu đạt ở đâu |
| --- | --- |
| M1 | Mục 1: ba mức S/C/U kèm thời gian phản hồi và ai chịu trách nhiệm |
| M2 | Mục 2: 9 dòng OS gồm RHEL 9, Ubuntu 24.04, Debian 11; ngày từ trang lifecycle, glibc đo hoặc theo bản phát hành |
| M3 | Mục 3: 5 dòng runtime, mỗi dòng phiên bản tối thiểu, điều kiện, giới hạn |
| M4 | Cột "Bằng chứng" của mục 2–3 dẫn về bài/milestone/số đo |
| M5 | Mục 4: 7 dòng, mỗi dòng "hỗ trợ thế nào" |
| M6 | Mục 5 |
| M7 | Mục 6: báo trước 6 tháng, `compat_check.py` + preflight để khách tự kiểm |
| M8 | Mục 6: 5 khoảng trống cho product |

---

## Bài mẫu

# Ma trận hỗ trợ quillo 1.1.x: hệ điều hành và runtime

Áp dụng từ: 11/11/2026 · Bản: quillo 1.1.x · Người duyệt (product): …

## 1. Mức hỗ trợ

| Mức | Nghĩa | Khi có sự cố |
| --- | --- | --- |
| **S — Được hỗ trợ** | Product chạy CI và kiểm cài đặt trên tổ hợp này mỗi bản phát hành | Theo SLA hợp đồng; lỗi do sản phẩm được sửa trong bản vá |
| **C — Chạy được, có điều kiện** | Đã cài thành công tại hiện trường/lab, có giới hạn đã ghi; không có CI | FDE hỗ trợ theo khả năng (best effort); lỗi chỉ tái hiện được trên tổ hợp này không đảm bảo có bản vá |
| **U — Không hỗ trợ** | Đã biết không chạy, hoặc OS đã hết hỗ trợ của nhà phát hành | Không nhận ticket; FDE giúp lên kế hoạch chuyển |

## 2. Hệ điều hành (x86-64)

| OS | Mức | Hết hỗ trợ của nhà phát hành (nguồn) | glibc | Ghi chú | Bằng chứng |
| --- | --- | --- | --- | --- | --- |
| Ubuntu 22.04 | S | Standard 06/2027, ESM 04/2032 (ubuntu.com/about/release-cycle) | 2.35 | Máy đối chứng | `lab-open`, module 02–03 |
| Ubuntu 24.04 | S (từ bản 1.2 khi có CI), hiện C | Standard 05/2029 | 2.39 | Chưa kiểm cài đặt | Chưa đo |
| Ubuntu 20.04 | C | Standard hết 31/05/2025; chỉ còn ESM (Ubuntu Pro) | 2.31 | Python hệ thống 3.8, thiếu `venv`; Docker distro không có compose plugin | `hospital`: module 03 intermediate, module 04 intermediate 02 |
| Rocky Linux 8 / RHEL 8 | S cho Podman rootless (mục 3) | 31/05/2029 (`SUPPORT_END` trong `/etc/os-release`, đo trên golden) | 2.28 | Không có `python3` mặc định; cgroup v1 | `bank`, `lawfirm-hardened`: module 04 basic 01, intermediate 01 |
| Rocky Linux 9 / RHEL 9 | C | 31/05/2032 (access.redhat.com/support/policy/updates/errata) | 2.34 | cgroup v2: giới hạn tài nguyên rootless có tác dụng; chưa kiểm | Chưa đo |
| Debian 12 | C | Security thường hết 11/07/2026, LTS tới 30/06/2028 (wiki.debian.org/LTS) | 2.36 | Đang ở pha LTS: khuyên khách lên Debian 13 | `factory`: module 04 basic 02 |
| Debian 13 | C | ~08/2028 thường, LTS 06/2030 | 2.41 | Chưa kiểm | Chưa đo |
| Debian 11 | **U** | LTS hết 31/08/2026 | 2.31 | `REQUIREMENTS.yaml` còn ghi `min: "11"`: product cần sửa | — |
| CentOS 7 / RHEL 7 | **U** | 30/06/2024 | 2.17 | Podman 1.x, kernel 3.10 | — |

## 3. Runtime

| Runtime | Mức | Phiên bản tối thiểu | Điều kiện | Giới hạn đã biết | Bằng chứng |
| --- | --- | --- | --- | --- | --- |
| Docker Engine + compose | S | Docker 20.10.10 (seccomp cho `clone3`), compose v2 | Không có plugin compose thì bundle mang binary `docker-compose` v5.6.1 | Restart daemon để đổi proxy/registry gây downtime nếu không `live-restore` | Module 03 |
| Podman rootless + `docker-compose` qua API | S trên Rocky/RHEL 8 | Podman 4.4 | `podman.socket` của user bật, linger bật, bind mount `:Z`/`:z` | cgroup v1: giới hạn RAM/CPU của container bị bỏ qua; container không tự lên sau reboot nếu không có `podman-restart.service`/Quadlet; cổng ≥ 1024 | Module 04 intermediate 01 (`lawfirm-hardened`) |
| k3s / Kubernetes | S cho k3s ≥ 1.30, C cho OpenShift | Helm 3 | Namespace riêng, PSA `restricted` cần values mẫu | Chart mặc định không có securityContext/resources | `lawfirm-prod`, module 06 |
| Không container (systemd --user) | C | Rocky/RHEL 8–9 | Postgres do khách cấp; product phát hành runtime + llama.cpp cho glibc 2.28 | Mất cô lập của container; tự vá runtime | Module 04 advanced 01 (thiết kế, chưa kiểm) |
| Docker Desktop / WSL2 | U cho production | — | — | Xem mục 5 | — |

## 4. Môi trường bị khoá

| Yêu cầu của khách | Hỗ trợ thế nào |
| --- | --- |
| SELinux enforcing | Hỗ trợ đầy đủ; **không bao giờ** yêu cầu permissive. Bind mount dùng `:Z`; không cần boolean nào cho cấu hình mặc định |
| Không root/sudo | Podman rootless hoặc systemd --user; cần IT một lần: linger cho user dịch vụ, subuid/subgid nếu chưa có |
| `/tmp` noexec | Hỗ trợ; installer dùng thư mục stage cạnh chỗ cài |
| `nofile` thấp | Tối thiểu 1024; installer tự điều chỉnh theo `ulimit -n` |
| Proxy, TLS inspection | Hỗ trợ; CA nội bộ được tin ở hệ thống và trong container theo hướng dẫn module 03 |
| Air-gapped | Hỗ trợ; bundle offline có `SHA256SUMS` và manifest |
| CPU/RAM/đĩa | x86-64 có AVX2 (CPU không AVX2 chạy được nhưng chậm, mức C); 2 vCPU, 4 GB RAM, 10 GB trống cho `llm-small` (`REQUIREMENTS.yaml`) |

## 5. Windows và WSL2

Mức **U** cho chạy thật, **C** cho demo/dev. Lý do: máy tắt theo phiên Windows, systemd tuỳ cấu hình `wsl.conf`, RAM do
`.wslconfig` giới hạn, mạng NAT không lộ cổng ra mạng công ty, Docker Desktop cần license thương mại ở doanh nghiệp lớn.
Nhận biết: `uname -r` chứa `microsoft-standard-WSL2`. Windows Server không phải nền tảng của quillo.

## 6. Thay đổi ma trận, tự kiểm và ghi chú cho product

- Bỏ một OS/runtime khỏi mức S: báo trước **6 tháng** trong release notes và email kỹ thuật; không bỏ giữa một bản vá.
  OS hết hỗ trợ của nhà phát hành chuyển sang U ở bản phát hành kế tiếp (Ubuntu 20.04 hiện là C vì khách có ESM).
- Khách tự kiểm: gửi kết quả `ldd --version`, `python3 -V`, `/etc/os-release` (công cụ `compat_check.py` ra danh sách
  vấn đề), rồi chạy `preflight` của installer trước ngày cài.

**Cho product (khoảng trống phải làm để ma trận đúng):**

1. CI hiện chỉ trên Ubuntu 22.04: thêm job cài đặt trên Rocky 8 (Podman rootless) và Ubuntu 24.04 trước khi gọi chúng là S.
2. Sửa `REQUIREMENTS.yaml`: bỏ Debian 11, ghi Podman tối thiểu 4.4 thay vì 4.0 (Quadlet, API compose đã kiểm).
3. Nếu bán cho khách "không container": dựng `llama-server` và wheelhouse cho glibc 2.28 trong pipeline release.
4. Chart Helm: thêm values mặc định qua được PSA `restricted`.
5. Ghi phiên bản Python runtime và llama.cpp vào release notes để khách theo dõi CVE.
