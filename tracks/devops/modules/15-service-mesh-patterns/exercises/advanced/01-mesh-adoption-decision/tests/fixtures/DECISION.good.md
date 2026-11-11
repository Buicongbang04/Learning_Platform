# Quyết định: service mesh cho Olist Logistics

## 1. Bối cảnh và yêu cầu

- 9 service, 60 pod production trên một cluster Kubernetes, 6 node; còn trống khoảng 12 GiB RAM.
- Kiểm toán PCI: luồng giữa `label-printer`, `carrier-gateway` và `billing` phải mã hoá và xác thực hai chiều (mTLS) trước quý 2.
- Hai người platform, không có ai chuyên về proxy; trực on-call theo tuần.
- Prometheus và Grafana đã có, nhưng chưa có số liệu theo từng cặp service.
- Không có VM ngoài cluster cần vào mesh.

## 2. Phương án

| Phương án | mTLS | Traffic | Observability | Vận hành | RAM ước tính (MiB) |
| --- | --- | --- | --- | --- | --- |
| Không dùng mesh: cert-manager cấp chứng chỉ, sửa code TLS hai chiều | Có nhưng phải sửa 3 service, tự xoay chứng chỉ | Retry trong thư viện client | Metrics của app | Nhẹ hạ tầng, nặng code | 0 |
| Linkerd sidecar | Mặc định cho mọi pod trong mesh, xoay tự động | Retry, timeout, traffic split | Golden metrics theo route và cặp service | Nhẹ, ít CRD | 520 |
| Istio ambient | Có qua ztunnel | L7 khi thêm waypoint | Có, cần Kiali, Prometheus | Trung bình | 900 |
| Cilium service mesh | Có (WireGuard hoặc mTLS) | Hạn chế hơn ở L7 | Hubble | Phải đổi CNI | 1100 |

## 3. Quyết định

- Chọn Linkerd sidecar, chỉ cho ba service trong phạm vi PCI trước, rồi mở rộng nếu đạt.
- Đáp ứng mTLS mà không sửa code; hai người platform vận hành được (ít CRD, ít cấu hình).
- Tốn khoảng 0,5 GiB, nằm trong phần RAM còn trống.
- Không chọn Istio vì chưa cần L7 phong phú; không chọn Cilium vì đổi CNI là rủi ro lớn hơn yêu cầu.

## 4. Chi phí tài nguyên

| Thành phần | Số lượng | MiB mỗi cái | Tổng (MiB) |
| --- | --- | --- | --- |
| Proxy Linkerd (pod production) | 60 | 4 | 240 |
| Control plane (destination, identity, injector, policy) | 1 | 90 | 90 |
| linkerd-cni | 6 | 3 | 18 |
| Dự phòng proxy khi tải cao | 60 | 3 | 180 |

Tổng: 528 MiB

## 5. Kế hoạch rollout

1. Cài Linkerd ở staging, chạy một tuần, đo RAM, độ trễ thêm.
2. Bật inject cho namespace `billing` ở production, theo dõi tỉ lệ thành công 2 ngày.
3. Mở rộng sang `label-printer` và `carrier-gateway`; xác nhận mTLS bằng metrics của proxy.
4. Thêm `Server` và `AuthorizationPolicy` ở chế độ audit trước, rồi mới deny.
5. Viết runbook; rollback là bỏ annotation inject và `rollout restart`, đã tập một lần ở staging.

## 6. Vận hành và trách nhiệm

- Team platform giữ trust anchor ngoài cluster, xoay chứng chỉ issuer mỗi năm; cảnh báo khi chứng chỉ còn dưới 30 ngày.
- Team platform nâng cấp Linkerd mỗi quý, staging trước production một tuần.
- Team ứng dụng sở hữu `AuthorizationPolicy` của service mình, review qua pull request.

## 7. Rủi ro và đường lui

- Injector chết thì pod mới không có proxy và bị policy chặn: cảnh báo trên webhook, runbook bật lại.
- Proxy thêm 1-2 ms mỗi chặng: đo ở staging, ngưỡng chấp nhận 5 ms p99.
- Đường lui: gỡ annotation inject theo namespace, xoá policy, quay về NetworkPolicy; giữ manifest NetworkPolicy cũ trong repo.

## 8. Khi nào xem lại

- Khi cần định tuyến L7 phức tạp (theo header, fault injection) mà Linkerd không có.
- Khi số pod vượt 500 hoặc thêm cluster thứ hai cần multi-cluster.
