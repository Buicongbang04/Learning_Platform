---
title: Đẩy image vào registry nội bộ của khách và chạy từ đó
level: basic
services: []
files:
  - path: starter/publish.sh
    note: 4 TODO, POSIX sh, chạy bằng sudo trên máy lawfirm-staging
  - path: tests/fixtures/hello-amd64.tar
    note: "docker save của hello-world (linux/amd64), không sửa"
  - path: tests/test_registry.py
    note: Không sửa
run:
  - nice -n 15 uv run python -m fdekit prepare lawfirm-staging
  - uv run pytest tracks/fde/modules/03-airgapped-proxy/exercises/basic/02-internal-registry -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Ở khách air-gapped có registry nội bộ, quy trình chuẩn là: nạp image từ bundle **một lần**, đẩy lên registry của
khách, mọi máy chạy kéo từ đó. Bài này làm đúng việc đó trên máy staging của công ty luật, với registry và Docker
**của khách**, cấu hình sẵn theo cách của khách, và bạn phải sống chung với cấu hình đó.

## Đề bài

Máy `lawfirm-staging` (Ubuntu 22.04, Docker từ gói của distro, không ra internet). IT công ty luật cho biết registry
nội bộ ở `10.0.2.101:5000` và họ đã có `/etc/docker/daemon.json` riêng (log, live-restore); thay đổi cấu hình Docker phải
giữ nguyên những gì họ đã đặt.

Viết `starter/publish.sh <image.tar> <registry host:port> <repo:tag>`. Test dựng khách (`fdekit.customer_site
("lawfirm-staging")`, registry thật chạy phía host), chép `tests/fixtures/hello-amd64.tar` vào `/home/fde/hello.tar`, ghi
`daemon.json` của IT, rồi chạy **hai lần**:

```bash
sudo sh /home/fde/publish.sh /home/fde/hello.tar 10.0.2.101:5000 tools/hello-<ngẫu nhiên>:r<ngẫu nhiên>
```

Sau đó test xoá mọi image cục bộ trong VM và chạy `docker run --rm 10.0.2.101:5000/<repo:tag>` bằng user `fde`.

Registry này là của khách, bạn không cấu hình được phía nó. Phần 2 của README module so sánh các cách để Docker làm
việc với một registry nội bộ và cái giá của từng cách; đọc trước khi chọn.

Tự boot máy để điều tra: `with fdekit.customer_site("lawfirm-staging") as s:` rồi `s.vm.ssh(...)`; registry nhìn từ
host ở `s.registry_host`.

## Tiêu chí đạt

`test_push_and_run_from_internal_registry`:

- Hai lần chạy `publish.sh` đều thoát `0`, mỗi lần ≤120 s.
- `/etc/docker/daemon.json` sau đó vẫn giữ nguyên mọi khoá IT đã đặt (`log-driver`, `log-opts`, `live-restore`), và nếu có
  `insecure-registries` thì danh sách đó chỉ chứa đúng `10.0.2.101:5000` (không dải CIDR, không registry khác).
- Docker daemon đang chạy.
- Registry (hỏi từ host qua API `/v2/`) có đúng `repo:tag` test yêu cầu.
- Sau khi xoá image cục bộ, `docker run` image từ registry nội bộ in `Hello from Docker!`, và `RepoDigests` của image vừa
  kéo về khớp digest registry trả cho tag đó.

## Gợi ý

### Gợi ý 1

Chạy tay từng bước trên VM trước (`docker load`, `docker tag`, `docker push`) và đọc nguyên văn lỗi đầu tiên. Lỗi đó nói
rõ Docker đang mong đợi gì ở registry.

### Gợi ý 2

`daemon.json` là JSON: sửa bằng công cụ hiểu JSON có sẵn trên máy (máy không có mạng để cài thêm), không bằng `sed` hay
ghi đè cả tệp. Daemon không đọc lại tệp này nếu bạn không bảo nó.

### Gợi ý 3

`docker load` in ra tên image nó vừa nạp; bạn không nên đoán tên đó từ tên tệp.
