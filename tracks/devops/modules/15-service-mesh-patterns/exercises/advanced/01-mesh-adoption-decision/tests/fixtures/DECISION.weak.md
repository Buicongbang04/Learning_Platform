# Quyết định: service mesh cho Olist Logistics

## 1. Bối cảnh và yêu cầu

- 9 service, 60 pod production.
- Kiểm toán yêu cầu mTLS giữa các service trong phạm vi PCI.
- Hai người platform.
- Prometheus đã có.

## 2. Phương án

| Phương án | mTLS | Traffic | Observability | Vận hành | RAM ước tính (MiB) |
| --- | --- | --- | --- | --- | --- |
| Linkerd | Có | Retry, timeout | Golden metrics | Nhẹ | 400 |
| Istio sidecar | Có | Rất nhiều | Có | Nặng | 3500 |
| Istio ambient | Có | L7 qua waypoint | Có | Trung bình | 1800 |
| Consul | Có | Có | Có | Nặng | 2500 |

## 3. Quyết định

- Chọn Linkerd.
- Vì nó nhẹ.
- Vì mọi người đều dùng.

## 4. Chi phí tài nguyên

| Thành phần | Số lượng | MiB mỗi cái | Tổng (MiB) |
| --- | --- | --- | --- |
| Proxy Linkerd | 160 | 4 | 600 |
| Control plane | 1 | 15000 | 15000 |
| linkerd-cni | 6 | 3 | 18 |

Tổng: 13000 MiB

## 5. Kế hoạch rollout

1. Cài Linkerd.
2. Bật inject cho mọi namespace.
3. Bật AuthorizationPolicy.
4. Xem dashboard.
5. Xong.

## 6. Vận hành và trách nhiệm

- Team platform lo.

## 7. Rủi ro và đường lui

- Proxy có thể lỗi.
- Tốn RAM.
- Có đường lui là gỡ mesh.

## 8. Khi nào xem lại

- Khi có sự cố.
- Sau một năm.
