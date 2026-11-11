# Olist Shop platform: code của bạn

Thư mục này là chỗ bạn làm capstone. Lúc đầu chỉ có khung thư mục và test; mỗi milestone thêm tệp vào đúng vị trí
dưới đây. Đề từng milestone ở [`../milestones/`](../milestones/), tổng quan ở [README capstone](../README.md).

| Thư mục | Milestone | Bạn tạo |
| --- | --- | --- |
| `ops/` | [M01](../milestones/m01-ops-scripts.md) | `bootstrap.sh`, `healthcheck.sh`, `backup.sh` |
| `nginx/` | [M02](../milestones/m02-nginx-front.md) | `gen-cert.sh`, `olist-shop.conf` |
| `container/` | [M03](../milestones/m03-containers.md) | `Dockerfile` (target `api`, `worker`), `compose.yaml` production, `trivy.yaml`, `.trivyignore.yaml` |
| `.github/workflows/`, `ci/` | [M04](../milestones/m04-cicd-pipeline.md) | `ci.yml` (test, build, quét, push, deploy staging), `smoke-test.sh` |
| `infra/` | [M05](../milestones/m05-iac-config.md) | Cấu hình OpenTofu: state S3 mã hoá, KMS, bucket backup, cây tham số SSM, instance role |
| `ansible/` | [M05](../milestones/m05-iac-config.md) | `site.yml`, `inventory/hosts.yml`, role `olist_worker` |
| `chart/olist-shop/` | [M06](../milestones/m06-kubernetes-helm.md) | Helm chart cho `api` và `worker`: HPA, PDB, NetworkPolicy, RBAC, HTTPRoute |
| `gitops/` | [M07](../milestones/m07-gitops-secrets.md) | `application.yaml` (ArgoCD, nhiều nguồn), `values-lab.yaml`, `.sops.yaml`, `seal-db.sh`, `secrets/kustomization.yaml` |
| `observability/` | [M08](../milestones/m08-observability.md) | Recording và alert rule kèm test `promtool`, route Alertmanager, dashboard Grafana; thêm `OTEL_EXPORTER_OTLP_ENDPOINT` vào `container/compose.yaml` |
| `sre/` | [M09](../milestones/m09-game-day.md) | `slo.yaml`, `runbook.yaml`, `RUNBOOK.md`, `POSTMORTEM.md`; thêm `observability/prometheus/rules/slo.yml` và `slo.test.yml` |
| `tests/` | mọi milestone | Không sửa: test chấm bài |

`.gitignore` ở đây đã chặn `backups/` (bản sao lưu thật), `nginx/tls/` (cert và private key thật), state và thư mục `.terraform/` của
OpenTofu, `ansible/runtime.json` (cấu hình runtime có mật khẩu) và `ansible/artifacts/`. Đừng bỏ các dòng đó.

## Chạy test

Từ gốc repo:

```bash
uv run pytest tracks/devops/capstone/project/tests -q -rs
uv run pytest tracks/devops/capstone/project/tests -q -rs -k m01
```

Chưa làm milestone nào thì test **fail** với thông báo "Chưa có tệp ...", không phải lỗi của test. Test skip khi máy
thiếu công cụ (bwrap, curl, jq, openssl, shellcheck, Docker hoặc image, trivy, act, registry local, tofu,
LocalStack riêng của track, ansible, helm, cluster kind `devops-lab`, ArgoCD, sops, age, image của stack observability, image netem của game day) và lý do skip cho
biết cần cài gì; skip không tính là đạt. Trên máy dùng chung, thêm `nice -n 15 ${DEVOPS_CPUSET:+taskset -c "$DEVOPS_CPUSET"}` trước `uv run`.

Bản tham chiếu nằm ở [`../solutions/`](../solutions/SOLUTION.md) và chạy được bằng
`SOLUTION=1 uv run pytest tracks/devops/capstone/project/tests -q -rs`. Chỉ mở sau khi đã tự làm.

## Vận hành

Mục này là của bạn: sau M01, ghi ba lệnh vận hành, exit code của từng lệnh và cách khôi phục từ backup; sau M02, thêm
mục "Edge" với các quyết định cấu hình Nginx; sau M03, mục "Container"; sau M04, mục "Pipeline"; sau M05, mục "Hạ tầng
và cấu hình"; sau M06, mục "Kubernetes"; sau M07, mục "GitOps"; sau M08, mục "Observability"; sau M09, mục "SRE". Xem phần "Kết quả nộp" của từng milestone.
