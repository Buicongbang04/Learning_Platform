# Olist Shop platform: code của bạn

Thư mục này là chỗ bạn làm capstone. Lúc đầu chỉ có khung thư mục và test; mỗi milestone thêm tệp vào đúng vị trí
dưới đây. Đề từng milestone ở [`../milestones/`](../milestones/), tổng quan ở [README capstone](../README.md).

| Thư mục | Milestone | Bạn tạo |
| --- | --- | --- |
| `ops/` | [M01](../milestones/m01-ops-scripts.md) | `bootstrap.sh`, `healthcheck.sh`, `backup.sh` |
| `nginx/` | [M02](../milestones/m02-nginx-front.md) | `gen-cert.sh`, `olist-shop.conf` |
| `container/` | [M03](../milestones/m03-containers.md) | `Dockerfile` (target `api`, `worker`), `compose.yaml` production, `trivy.yaml`, `.trivyignore.yaml` |
| `.github/workflows/`, `ci/` | [M04](../milestones/m04-cicd-pipeline.md) | `ci.yml` (test, build, quét, push, deploy staging), `smoke-test.sh` |
| `tests/` | mọi milestone | Không sửa: test chấm bài |

`.gitignore` ở đây đã chặn `backups/` (bản sao lưu thật) và `nginx/tls/` (cert và private key thật). Đừng bỏ hai dòng đó.

## Chạy test

Từ gốc repo:

```bash
uv run pytest tracks/devops/capstone/project/tests -q -rs
uv run pytest tracks/devops/capstone/project/tests -q -rs -k m01
```

Chưa làm milestone nào thì test **fail** với thông báo "Chưa có tệp ...", không phải lỗi của test. Test skip khi máy
thiếu công cụ (bwrap, curl, jq, openssl, shellcheck, Docker hoặc image, trivy, act, registry local) và lý do skip cho
biết cần cài gì; skip không tính là đạt. Trên máy dùng chung, thêm `nice -n 15 ${DEVOPS_CPUSET:+taskset -c "$DEVOPS_CPUSET"}` trước `uv run`.

Bản tham chiếu nằm ở [`../solutions/`](../solutions/SOLUTION.md) và chạy được bằng
`SOLUTION=1 uv run pytest tracks/devops/capstone/project/tests -q -rs`. Chỉ mở sau khi đã tự làm.

## Vận hành

Mục này là của bạn: sau M01, ghi ba lệnh vận hành, exit code của từng lệnh và cách khôi phục từ backup; sau M02, thêm
mục "Edge" với các quyết định cấu hình Nginx; sau M03, mục "Container"; sau M04, mục "Pipeline". Xem phần "Kết quả
nộp" của từng milestone.
