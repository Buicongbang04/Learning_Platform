# Lời giải: NetworkPolicy tối thiểu cho quillo

Lời giải ở `networkpolicy.yaml` cạnh tệp này:

```bash
SOLUTION=1 nice -n 15 uv run pytest tracks/fde/modules/06-k8s-at-customer/exercises/basic/03-network-policy -q
```

Đo 2026-11-11 trên máy của repo: ~50 s (boot ~15 s, bảy pod thử ~10 s, mỗi vòng thử ~8 s).

## Cách nghĩ

Với `default-deny`, mỗi kết nối cần **hai** cửa mở: egress ở pod nguồn và ingress ở pod đích. NetworkPolicy chỉ cộng
quyền: một pod được chọn bởi nhiều policy thì được phép hợp của tất cả. Nên lời giải là một policy cho mỗi thành phần,
mỗi policy mô tả đúng hàng của nó trong bảng luồng:

| Policy | Chọn pod | Ingress | Egress |
| --- | --- | --- | --- |
| `quillo-api` | component api | từ `lawfirm-gateway`, cổng 8080 | db:5432; llm, embed:8080 |
| `quillo-worker` | component worker | (không có: chặn) | db:5432; embed:8080 |
| `quillo-db` | component db | từ api, worker, cổng 5432 | (không khai Egress: `default-deny` vẫn chặn) |
| `quillo-llm` | component llm | từ api, cổng 8080 | như trên |
| `quillo-embed` | component embed | từ api, worker, cổng 8080 | như trên |
| `lawfirm-gateway-to-quillo` | `lawfirm-gateway` | (không đổi) | api:8080 |

DNS: `default-deny` đã cho egress tới CoreDNS, nên không cần lặp lại (vẫn đúng khi viết thêm: luật cộng dồn).

## Ba chỗ dễ sai

1. **Quên egress của gateway.** IT nói gateway "chưa có policy nào", tức là nó đang nằm dưới `default-deny`: mở ingress
   cho api thôi thì gateway vẫn không gửi gói ra được. Test bắt bằng luồng `gateway → api:8080` phải thông.
2. **Ingress của api mở cho mọi nguồn** (`ingress: [{ports: [{port: 8080}]}]`, như `networkPolicy.apiFrom` rỗng của
   chart). Dưới `default-deny` trông như vẫn an toàn vì pod khác không có egress, nhưng `reporting-egress` của IT mở egress
   cho pod reporting: lúc đó chỉ ingress của api chặn được nó. Test bắt bằng `reporting → api:8080` phải tắc. Quy tắc:
   ingress của bạn phải tự đứng được, không dựa vào việc policy của người khác đang chặt.
3. **`from` viết thành hai phần tử** (`- podSelector: …` và `- namespaceSelector: …` riêng) thay vì một phần tử có cả hai:
   đó là "hoặc", mở cho mọi pod của mọi namespace khớp selector thứ hai.

`matchExpressions` với `In` gộp nhiều thành phần trong một phần tử `from`/`to`; viết hai phần tử `podSelector` riêng
cũng đạt.

## Kiểm bằng kết nối thật, không bằng đọc YAML

`kubectl describe networkpolicy` cho biết policy *nói* gì, không cho biết CNI có áp hay không (flannel thuần không áp
NetworkPolicy; k3s áp bằng kube-router tích hợp). Cách chắc chắn là pod thử ở đúng nhãn rồi `nc -z`, như test làm, và
thử cả các luồng phải tắc. Khi bàn giao, gửi IT bảng luồng cùng kết quả thử, không chỉ tệp YAML.
