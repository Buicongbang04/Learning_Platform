---
title: "NetworkPolicy tối thiểu cho quillo"
level: basic
services: []
files:
  - path: starter/networkpolicy.yaml
    note: NetworkPolicy của quillo, bạn viết
  - path: tests/test_network_policy.py
    note: Không sửa (cũng là nơi định nghĩa pod thử)
run:
  - nice -n 15 uv run python -m fdekit prepare lawfirm-prod
  - uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/basic/03-network-policy -q
  - uv run python -m fdekit leftovers
---

## Mục tiêu

Namespace của khách chặn sẵn mọi kết nối. Bảo IT "mở hết cho namespace quillo" là cách nhanh nhất để mất lòng tin của
đội bảo mật. Bạn viết đúng những NetworkPolicy mà sản phẩm cần, theo một bảng luồng có thể đưa cho IT duyệt, rồi chứng
minh bằng kết nối thật: luồng trong bảng thông, mọi luồng khác vẫn tắc.

## Đề bài

Namespace `quillo` trên `lawfirm-prod` có hai NetworkPolicy của IT, bạn **không** được sửa hay xoá:

- `default-deny`: chọn mọi pod, chặn mọi ingress và egress trừ DNS tới CoreDNS ở `kube-system`.
- `reporting-egress`: pod `app.kubernetes.io/name=reporting` (công cụ báo cáo của IT) được egress tới mọi pod trong
  namespace.

Pod của quillo mang nhãn `app.kubernetes.io/name=quillo`, `app.kubernetes.io/instance=quillo`,
`app.kubernetes.io/component=<api|worker|db|llm|embed>`. Reverse proxy của công ty luật chạy trong cùng namespace với
nhãn `app.kubernetes.io/name=lawfirm-gateway`, IT chưa viết policy nào cho nó và cho phép bạn viết.

Bảng luồng **được mở** (mọi luồng khác phải bị chặn):

| Từ | Tới | Cổng TCP |
| --- | --- | --- |
| api | db | 5432 |
| api | llm, embed | 8080 |
| worker | db | 5432 |
| worker | embed | 8080 |
| lawfirm-gateway | api | 8080 |

Viết `starter/networkpolicy.yaml`: một hay nhiều object `NetworkPolicy` (ngăn bằng `---`), namespace `quillo` hoặc bỏ
trống, tên khác `default-deny` và `reporting-egress`.

Test boot `lawfirm-prod`, tạo `reporting-egress` và bảy pod thử BusyBox (năm thành phần quillo, `lawfirm-gateway`,
`reporting`), mỗi pod nghe cổng 8080 và 5432; áp tệp của bạn bằng `kubectl apply -n quillo -f`, rồi từ từng pod thử
`nc -z -w 2 <IP pod đích> <cổng>` theo một danh sách luồng: mọi luồng trong bảng, và các luồng ngoài bảng như worker →
llm, api → db cổng 8080, gateway → db, reporting → api/db/embed, db/llm/embed → nơi khác, api → gateway, pod quillo →
`10.0.2.101:5000` (ngoài namespace). Đo trên máy của repo: ~50 s.

## Tiêu chí đạt

`test_network_policy_matches_flow_table`:

- Tệp chỉ chứa NetworkPolicy hợp lệ, đúng namespace và tên như trên; `kubectl apply` chấp nhận.
- Mọi luồng trong bảng kết nối được (thử lại vài vòng trong ~15 s để policy kịp áp).
- Mọi luồng ngoài bảng mà test thử đều không kết nối được ở **mọi** vòng.
- Sau cùng, `default-deny` và `reporting-egress` giữ nguyên `spec`.

## Gợi ý

### Gợi ý 1

Một kết nối đi qua hai policy: egress của pod nguồn và ingress của pod đích. Với `default-deny`, cả hai chiều đều đang
đóng.

### Gợi ý 2

NetworkPolicy chỉ cộng thêm quyền, không trừ. Policy của người khác mở egress cho pod của họ thì chỉ ingress của pod
bạn quyết định họ vào được tới đâu.

### Gợi ý 3

Trong cùng một phần tử `from`/`to`, `podSelector` và `namespaceSelector` là "và"; hai phần tử riêng là "hoặc". Viết sai
một dấu `-` là mở rộng gấp nhiều lần.
