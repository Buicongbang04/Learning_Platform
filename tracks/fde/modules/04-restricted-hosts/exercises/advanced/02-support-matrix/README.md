---
title: Ma trận hỗ trợ OS và runtime gửi khách
level: advanced
services: []
files:
  - path: starter/support-matrix.md
    note: Khung ma trận hỗ trợ 6 phần
run: []
---

## Mục tiêu

"Quillo chạy trên Linux" không phải một cam kết. Khách hỏi "máy của chúng tôi có được hỗ trợ không" và hợp đồng hỗ trợ
cần một câu trả lời kiểm được: OS nào, bản nào, tới ngày nào, runtime nào, điều kiện gì, cái gì "chạy được nhưng không hỗ
trợ". Bài này viết ma trận đó cho khách, dựa trên số đo thật chứ không phải ước đoán, và giữ được khi product ra bản mới.

## Đề bài

Bốn khách hiện có của công ty, mỗi khách một kiểu máy (đúng các hồ sơ của track): ngân hàng (`bank`, `lawfirm-hardened`:
Rocky 8.10, Podman 4.9 rootless, SELinux, không root), bệnh viện (`hospital`: Ubuntu 20.04, Docker 26 không compose
plugin), nhà máy (`factory`: Debian 12, Docker CE 29 + compose 5.6), công ty luật (`lawfirm-staging`/`lawfirm-prod`:
Ubuntu 22.04, Docker hoặc k3s). Khách mới hỏi thêm về RHEL 9, Ubuntu 24.04 và "máy dev Windows có WSL2".

Product: `quillo` 1.1.0 phát hành dạng bundle compose (image `quillo-api` dựng trên Python 3.12 Debian bookworm,
`llama.cpp` server, Postgres 16 + pgvector) và Helm chart; `REQUIREMENTS.yaml` ghi `os` tối thiểu Ubuntu 20.04 / Rocky 8 /
Debian 11, runtime `docker>=20.10`, `podman>=4.0`. Bạn đã có công cụ `compat_check.py` (bài basic 03) và output thật của
các máy (`exercises/basic/03-compat-check/tests/fixtures/`), cùng kết quả các bài trong module này.

Viết `starter/support-matrix.md` gửi khách (kèm bản cho product). Bài không có test; tự chấm theo rubric, đạt đủ 8 mục,
rồi so với bài mẫu trong `solutions/`.

| # | Tiêu chí (mỗi mục đạt / không đạt) |
| --- | --- |
| M1 | Định nghĩa ba (hoặc nhiều hơn) mức hỗ trợ có nghĩa vận hành rõ (ví dụ: được hỗ trợ / chạy được không cam kết / không hỗ trợ), mỗi mức nói khách được gì khi có sự cố |
| M2 | Bảng OS × phiên bản: mức hỗ trợ, ngày hết hỗ trợ của OS (nguồn chính thức), glibc, ghi chú; đủ các OS trong đề kể cả bản khách mới hỏi |
| M3 | Bảng runtime: Docker (phiên bản tối thiểu, compose plugin hay binary), Podman rootless (phiên bản, socket, cgroup v1/v2), k3s/Kubernetes, "không container" (nếu bạn chọn hỗ trợ), mỗi dòng có điều kiện và giới hạn đã biết |
| M4 | Mỗi điều kiện hay giới hạn quan trọng dẫn về **bằng chứng** (số đo, output, bài trong module) chứ không phải "nghe nói" |
| M5 | Yêu cầu môi trường ngoài OS: SELinux (enforcing được hỗ trợ, cách), không root, `/tmp` noexec, `nofile`, proxy/air-gapped, CPU (AVX2), RAM/đĩa; mỗi thứ nói "được hỗ trợ thế nào" chứ không chỉ "cần" |
| M6 | WSL2 và Windows: mức hỗ trợ, lý do, phạm vi được dùng (demo/dev) |
| M7 | Chính sách thay đổi: khi nào một OS/runtime bị bỏ, báo trước bao lâu, cách khách kiểm máy của họ (lệnh hoặc công cụ) |
| M8 | Bản cho product: những khoảng trống phải làm để giữ ma trận (CI trên OS nào, build cho glibc nào, thứ product đang hứa mà chưa kiểm) |

## Tiêu chí đạt

- `support-matrix.md` đạt đủ M1–M8 khi tự chấm từng mục.
- Mọi ngày vòng đời có nguồn chính thức (trang lifecycle của distro), mọi phiên bản có trong đề hoặc đo được trên VM.

## Gợi ý

### Gợi ý 1

Bắt đầu từ thứ bạn **đã đo** trong module (bài nào chạy được, gãy ở đâu, sửa bằng gì) rồi mới tới thứ bạn suy ra. Thứ
chưa đo thì ghi là chưa đo.

### Gợi ý 2

Một mức "được hỗ trợ" mà product không chạy CI trên đó là một lời hứa không ai giữ. Hỏi product họ thật sự kiểm trên gì.

### Gợi ý 3

Ngày hết hỗ trợ của OS không phải ngày bạn ngừng hỗ trợ. Quyết định cái sau, nói rõ khoảng giữa hai ngày đó.
