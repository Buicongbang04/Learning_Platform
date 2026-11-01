# Lời giải: Ingress và HTTPRoute trên Gateway dùng chung

Lời giải: `k8s/20-ingress.yaml`, `k8s/30-httproute.yaml` (`10-api.yaml` giữ như starter).

## Ingress

`ingressClassName: devops-traefik` chọn controller (Traefik chỉ xử lý Ingress của class nó được cấu hình); `pathType: Prefix` với `/`
bắt mọi path; backend trỏ cổng theo **tên** (`http`) của Service. Không có `defaultBackend`: trên controller dùng chung, defaultBackend
bắt mọi host không khớp rule nào, kể cả host của team khác, nên policy của lab từ chối nó.

## HTTPRoute

- `parentRefs` trỏ Gateway `public` ở namespace `devops-gateway`. Gateway cho phép gắn route vì namespace của lab có nhãn `devops-ex`
  (`allowedRoutes.namespaces.from: Selector`). Đó là hợp đồng giữa platform và team app: platform quyết định listener, TLS, ai được gắn;
  team app quyết định route của mình.
- Rule đầu chỉ có match header `X-Canary: always`, tới `api-canary`. Rule sau match path `/` với hai `backendRefs` trọng số 90 và 10.
  Theo spec, khi nhiều rule khớp, rule có nhiều điều kiện cụ thể hơn được ưu tiên, nên request có header luôn vào rule đầu.
- Trọng số là tỉ lệ request, không phụ thuộc số replica (Ingress thuần hay hai Deployment chung Service thì tỉ lệ theo số pod).

## Vì sao không tạo được Gateway

Token của lab chỉ có quyền ghi `httproutes` và `ingresses`; Gateway, GatewayClass, ReferenceGrant là việc của platform. Một team tự tạo
Gateway là tự mở listener trên controller dùng chung; một ReferenceGrant cho phép route của namespace khác trỏ Service của mình.
Tách quyền như vậy là lý do chính Gateway API ra đời.

## Bản ingress-nginx (đối chiếu)

Canary 10% bằng ingress-nginx cần một Ingress thứ hai cùng host với annotation `nginx.ingress.kubernetes.io/canary: "true"` và
`nginx.ingress.kubernetes.io/canary-weight: "10"` (cộng `canary-by-header`). Annotation đó chỉ ingress-nginx hiểu; đổi sang Traefik
phải viết lại bằng `TraefikService` riêng. HTTPRoute mang được giữa các implementation đạt conformance.

## Sai lầm hay gặp

- Thiếu `hostnames`: route khớp mọi host của listener, bị policy của lab từ chối.
- `parentRefs` thiếu `namespace`: mặc định là namespace của route, không có Gateway nào ở đó, `Accepted=False`.
- Cổng trong `backendRefs` là cổng của **Service** (8000), không phải `targetPort`.
