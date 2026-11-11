# Quyết định: service mesh cho Olist Marketplace

## 1. Bối cảnh và yêu cầu

- 18 service, khoảng 140 pod production trên một cluster Kubernetes 8 node; staging là cluster riêng nhỏ hơn. Phần RAM còn trống ở production khoảng 12 GiB.
- PCI DSS: năm service trong luồng thanh toán (`checkout`, `payments`, `fraud`, `ledger`, `refunds`) phải mã hoá và xác thực hai chiều (mTLS) trong 6 tháng; kiểm toán cần bằng chứng danh tính của từng bên gọi.
- Team `checkout` muốn canary theo tỉ lệ traffic (5%, 25%, 100%) thay vì đổi cả Deployment một lần.
- Connector ERP cũ chạy trên một VM ngoài cluster, gọi `ledger` qua HTTP.
- 3 team sản phẩm (khoảng 15 dev), 2 người platform; chưa ai vận hành Envoy hay Istio.
- Prometheus, Grafana, Loki, Jaeger đã có (module 13); thiếu số liệu theo từng cặp service.
- Black Friday tải gấp 10 lần ngày thường trong vài giờ.

## 2. Phương án

| Phương án | mTLS | Traffic | Observability | Vận hành | RAM ước tính (MiB) |
| --- | --- | --- | --- | --- | --- |
| Không dùng mesh: cert-manager, TLS hai chiều trong code, Argo Rollouts cho canary qua Ingress | Phải sửa 5 service ở 3 ngôn ngữ, tự xoay chứng chỉ | Canary ở Ingress, retry trong thư viện client | Metrics của app, không có theo cặp service | Hạ tầng nhẹ, nặng phần code và review | 300 |
| Linkerd sidecar | Mặc định cho mọi pod trong mesh, danh tính theo ServiceAccount, xoay 24 giờ | Retry, timeout, traffic split theo HTTPRoute | Golden metrics theo route, theo cặp service | Ít CRD, proxy Rust nhỏ, 2 người vận hành được | 900 |
| Istio sidecar | Có, PeerAuthentication STRICT | Phong phú nhất: header, mirror, fault injection | Có, cần Kiali, Prometheus | Nhiều CRD, Envoy nặng hơn, cần người chuyên | 7600 |
| Istio ambient | Có qua ztunnel mỗi node | L7 khi thêm waypoint cho từng namespace | Có | Mới hơn, ít kinh nghiệm vận hành trong team | 1500 |
| Consul service mesh | Có, CA từ Vault | Có, qua Envoy | Có | Mạnh khi có VM; thêm server Consul phải vận hành | 3200 |

## 3. Quyết định

- Chọn Linkerd sidecar, bắt đầu với năm service PCI, mở rộng ra cả cluster nếu đạt các ngưỡng ở mục 5.
- mTLS mặc định không sửa code, có bằng chứng danh tính (`client_id` trong metrics) cho kiểm toán; traffic split đủ cho canary của `checkout`.
- Hai người platform vận hành được; tốn khoảng 0,9 GiB, nằm trong 12 GiB còn trống. Istio sidecar tốn gần 8 GiB và cần người chuyên.
- Connector ERP trên VM không vào mesh: đi qua Ingress có mTLS ở cổng vào (chứng chỉ client do cert-manager cấp), `ledger` chỉ nhận từ Ingress qua AuthorizationPolicy.
- Không chọn Consul dù có VM: chỉ một VM, không đáng thêm một cụm Consul.

## 4. Chi phí tài nguyên

| Thành phần | Số lượng | MiB mỗi cái | Tổng (MiB) |
| --- | --- | --- | --- |
| Proxy Linkerd (pod production) | 140 | 4 | 560 |
| Dự phòng proxy khi tải Black Friday | 140 | 2 | 280 |
| Control plane (destination, identity, injector, policy, sp-validator) | 1 | 70 | 70 |
| linkerd-cni | 8 | 3 | 24 |

Tổng: 934 MiB

## 5. Kế hoạch rollout

1. Staging: cài Linkerd theo `setup/kind/linkerd` (helm template, CA ngoài, linkerd-cni), chạy hai tuần, đo RAM, độ trễ p99 thêm (ngưỡng 5 ms) và tỉ lệ thành công.
2. Production, namespace `payments` trước: bật inject, `rollout restart`, theo dõi 3 ngày; kiểm `client_id` của mọi luồng vào.
3. Bốn service PCI còn lại, mỗi ngày một service; xác nhận mọi kết nối giữa chúng là `tls="true"`.
4. `Server` và `AuthorizationPolicy` cho luồng PCI: chạy với `MeshTLSAuthentication` liệt kê đủ bên gọi đã thấy trong metrics, rồi mới bật cho từng Server; xem `inbound_http_authz_deny_total` sau mỗi bước.
5. Canary của `checkout` bằng HTTPRoute có `backendRefs` hai phiên bản theo trọng số.
6. Rollback ở mọi bước: bỏ annotation inject, `rollout restart`, xoá policy; đã tập ở staging và ghi trong runbook. Bước 4 có rollback riêng là xoá AuthorizationPolicy (mặc định quay về `all-unauthenticated`).

## 6. Vận hành và trách nhiệm

- Platform giữ trust anchor ngoài cluster (két offline), issuer xoay mỗi năm; cảnh báo khi chứng chỉ issuer còn dưới 60 ngày.
- Platform nâng cấp Linkerd mỗi quý theo edge đã ra đủ hai tuần, staging trước một tuần; nâng cấp proxy đi kèm `rollout restart` theo lịch.
- Team sản phẩm sở hữu `AuthorizationPolicy` và HTTPRoute của service mình, review qua pull request có người platform.
- On-call có runbook: injector chết, chứng chỉ hết hạn, policy chặn nhầm.

## 7. Rủi ro và đường lui

- Injector có `failurePolicy: Ignore`: chết thì pod mới chạy không proxy và bị policy chặn. Cảnh báo theo số pod thiếu proxy.
- Trust anchor hết hạn hay bị xoay sai làm toàn bộ mTLS hỏng: tập xoay ở staging, có checklist.
- Proxy thêm độ trễ, đặc biệt khi tải gấp 10: load test trước Black Friday.
- Đường lui: gỡ mesh theo namespace (bỏ inject, restart), giữ NetworkPolicy hiện có làm lớp bảo vệ nền; chứng minh mTLS cho kiểm toán tạm bằng TLS hai chiều ở Ingress trong lúc gỡ.

## 8. Khi nào xem lại

- Khi cần định tuyến L7 phức tạp (theo header, mirror, fault injection) cho nhiều team.
- Khi thêm VM hay cluster thứ hai cần chung mesh (khi đó cân nhắc Consul hay multi-cluster của Linkerd).
- Khi Istio ambient có ít nhất một năm vận hành ổn định trong cộng đồng và team có người chuyên.
