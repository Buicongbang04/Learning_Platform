# Lời giải: chọn công cụ theo tình huống

## Cách làm

Mỗi câu có một ràng buộc cứng loại ngay hai phương án, rồi câu hỏi "ai vận hành nó" chọn giữa hai phương án còn lại.
Công cụ đúng là công cụ nhỏ nhất thoả ràng buộc mà team vận hành được, không phải công cụ mạnh nhất.

| Câu | Đáp án | Ràng buộc quyết định | Track dạy ở |
| --- | --- | --- | --- |
| `ci-small-team` | b. GitHub Actions | Code đã trên GitHub, không ai trực server CI | 07 |
| `config-agentless` | c. Ansible | Không được cài agent | 09 |
| `iac-multi-provider` | a. OpenTofu | Nhiều provider, plan trước apply, mã nguồn mở | 08 |
| `secrets-in-git` | d. SOPS | Secret nằm trong Git, diff theo key | 12 |
| `logs-low-budget` | b. Loki | Đã có Grafana, ngân sách gần 0, tìm theo label | 13 |
| `orchestration-small` | c. Compose trên VM | 4 người, 3 service, chưa ai vận hành K8s | 06 |
| `serverless-bursty` | a. AWS Lambda | Tải dồn đợt, idle phần lớn thời gian | 14 |
| `web-server-auto-tls` | d. Caddy | HTTPS tự động, cấu hình tối thiểu | 05 |
| `artifact-repository` | b. Nexus hoặc Artifactory | Nhiều định dạng, on-prem, bất biến | 07 |
| `gitops-ui` | a. ArgoCD | Cần UI xem drift và sync | 12 |
| `mesh-light` | c. Linkerd | mTLS + golden metrics, sợ phức tạp | 15 |
| `tracing-slow-request` | d. OpenTelemetry + Jaeger | Trace qua nhiều service, instrument trung lập | 13 |

## Giải thích từng câu

### `ci-small-team`: GitHub Actions

Code đã ở GitHub, runner do GitHub quản lý nên không có server để vá. Jenkins mạnh và linh hoạt nhất nhưng ai đó
phải vá plugin và trực nó; đúng khi công ty cần CI on-prem hoặc pipeline rất đặc thù. TeamCity hợp shop .NET/JVM
lớn đã có license. Octopus Deploy là công cụ **deploy/release**, không chạy test cho PR.

### `config-agentless`: Ansible

Ansible chạy qua SSH, không cần agent, playbook đọc được như tài liệu. Puppet và Chef dùng agent kéo cấu hình định
kỳ: tự sửa drift tốt hơn, đúng ở công ty hàng nghìn máy đã có hạ tầng đó, nhưng vi phạm ràng buộc. CloudFormation tạo
tài nguyên AWS, không cấu hình bên trong máy.

### `iac-multi-provider`: OpenTofu

OpenTofu (fork mã nguồn mở của Terraform, giấy phép MPL) có provider cho cả AWS và Cloudflare, có `plan`. CloudFormation
và CDK chỉ quản AWS (CDK sinh CloudFormation), phần Cloudflare làm tay sẽ drift. Ansible gọi API được nhưng không có
state và plan, khó biết thay đổi gì trước khi chạy. Terraform cũng đúng về kỹ thuật; ràng buộc "mã nguồn mở" loại nó
vì Terraform đổi sang giấy phép BSL từ 2023.

### `secrets-in-git`: SOPS

SOPS mã hoá **giá trị**, giữ nguyên key, nên diff trong PR vẫn thấy "đổi `DB_PASSWORD`" mà không lộ giá trị. Secret
Kubernetes chỉ base64, không phải mã hoá. `.env` trong repo private vẫn là plaintext ai clone cũng đọc được. Vault
đúng khi cần secret động, xoay vòng, audit tập trung; nhưng khi đó secret không nằm trong Git như đề yêu cầu.

### `logs-low-budget`: Loki

Loki chỉ index label (service, level), lưu log nén trên object storage, nên rẻ; truy vấn trong Grafana sẵn có. Đổi
lại, tìm full-text trên khối lượng lớn chậm hơn Elasticsearch. Elastic Stack ba node cần người vận hành và RAM; đúng
khi cần tìm kiếm full-text phức tạp. Splunk và Datadog mạnh nhưng tính tiền theo GB, vượt ngân sách.

### `orchestration-small`: Docker Compose trên VM

Kubernetes giải quyết bài toán nhiều team, nhiều service, scale tự động. Bốn người vận hành ba service trên hai VM
sẽ tiêu phần lớn thời gian cho chính cluster. Compose với healthcheck, `restart: unless-stopped`, deploy bằng script
idempotent là đủ, và chuyển lên K8s sau không khó nếu image đã chuẩn. Swarm 5 manager cho 2 VM là vô lý; Istio
trước khi có K8s là đặt mái trước móng. Điều kiện để chuyển: nhiều team hơn, cần autoscale, cần nhiều môi trường.

### `serverless-bursty`: AWS Lambda

Trả tiền theo lần chạy, tự scale theo đợt, không tốn khi idle; tác vụ ngắn hơn nhiều giới hạn 15 phút. EC2 reserved
và dyno 24/7 trả tiền cho thời gian idle. Cluster riêng là chi phí vận hành lớn nhất. Lambda sai khi tác vụ chạy dài,
cần GPU, hoặc tải đều và cao (khi đó container chạy liên tục rẻ hơn).

### `web-server-auto-tls`: Caddy

Caddy tự xin và gia hạn chứng chỉ ACME, cấu hình vài dòng. Nginx + certbot làm được, là lựa chọn của track vì phổ biến
và linh hoạt nhất, nhưng thêm cron và hook reload cần theo dõi. Tomcat là servlet container cho Java; IIS cho hệ Windows.

### `artifact-repository`: Nexus hoặc Artifactory

Hai công cụ này là artifact repository đa định dạng (Maven, npm, PyPI, Docker), có proxy cache, phân quyền, chính sách
không ghi đè bản phát hành. GitHub Releases chỉ chứa tệp đính kèm theo repo. Bucket S3 thô không có metadata hay quyền
theo package. Docker Hub public sai cả on-prem lẫn quyền riêng tư.

### `gitops-ui`: ArgoCD

ArgoCD có UI hiển thị trạng thái đồng bộ, drift, cây tài nguyên, và nút sync; quản nhiều cluster từ một chỗ. FluxCD
cũng là GitOps tốt, nhẹ hơn, hợp team thích CLI và cấu hình thuần Git, nhưng không có UI chính thức. Jenkins chạy
`kubectl apply` theo giờ là push-based, không phát hiện drift. Helm cài tay là trạng thái chỉ nằm trên laptop.

### `mesh-light`: Linkerd

Linkerd bật mTLS mặc định, có golden metrics theo route, proxy viết bằng Rust nhẹ, cài nhanh. Istio mạnh hơn về định
tuyến và chính sách nhưng phức tạp hơn nhiều; Consul hợp khi đã dùng hệ HashiCorp và cần mesh trải qua VM. Tự viết
sidecar Envoy là tự làm lại một service mesh.

### `tracing-slow-request`: OpenTelemetry + Jaeger

Cần trace phân tán: một request sinh nhiều span qua nhiều service. OpenTelemetry là chuẩn instrument trung lập (gửi
tới Jaeger, Tempo, Datadog… mà không sửa code), Jaeger lưu và hiển thị trace. Zabbix đo máy, không thấy request.
Papertrail gom log text, phải tự ghép. Prometheus counter cho biết tỉ lệ chậm, không cho biết đoạn nào chậm.
